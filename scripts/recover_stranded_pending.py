"""Recovery konsolidasi pending rows untuk sesi stranded (A3, 2026-08-16).

Meniru persis alur produksi _consolidate_locked:
- fetch pending rows per session
- chunk_rows (whole-turn, 6000 char)
- consolidate_once per chunk (llm_call 90s, admission, mem0.add, shadow record)
- mark_consolidated hanya untuk chunk yang sukses

AMAN: memakai jalur storage + consolidation yang sama dengan gateway. Tidak
memodifikasi skema; hanya menjalankan pipeline konsolidasi idempotent terhadap
row yang masih pending. Snapshot dibuat sebelum dijalankan.

PENYEBARAN: jalankan PER PROFILE dengan env HERMES_HOME + TARGET_SESSIONS.
"""
import json
import os
import sys
import time
import importlib.util
from pathlib import Path

PROFILE = Path(os.environ.get("HERMES_HOME", "/home/wajdi/.hermes/profiles/research"))
os.environ["HERMES_HOME"] = str(PROFILE)

PLUGIN_DIR = Path(os.environ.get(
    "PLUGIN_DIR", "/home/wajdi/hermes-dual-memory/plugins/memory/hermes-dual-memory"))
sys.path.insert(0, str(PLUGIN_DIR))

from storage import HotSessionStore  # noqa: E402
from consolidation import consolidate_once, chunk_rows  # noqa: E402

spec = importlib.util.spec_from_file_location("hdm", str(PLUGIN_DIR / "__init__.py"))
hdm = importlib.util.module_from_spec(spec)
if spec.loader is not None:
    spec.loader.exec_module(hdm)

STORE_DIR = PROFILE / "hermes-dual-memory"
DB = STORE_DIR / "hot_sessions.sqlite3"

# Sesi stranded: last activity >= 08-15, bukan sesi aktif hari ini.
# Di-set via env TARGET_SESSIONS (json list) atau default kosong (skip semua).
_target = os.environ.get("TARGET_SESSIONS", "[]")
PENDING_SESSIONS = json.loads(_target)


def main():
    # muat .env profile in-process (pola referensi consolidation-model-and-recovery)
    env_path = PROFILE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    store = HotSessionStore(str(STORE_DIR))
    cfg = hdm.MemoryProvider._default_mem0_config(PROFILE)
    llm_call = hdm.MemoryProvider._load_llm_callable(cfg)
    if llm_call is None:
        print("FATAL: llm_call None")
        return 1

    admission_check = lambda content: hdm._admission.evaluate_admission(  # noqa: E731
        content, llm_call=llm_call, timeout_seconds=5.0
    )
    skill_router = lambda report: hdm._procedural.route_new_skills(  # noqa: E731
        report=report, session_id="recovery", hermes_home=str(PROFILE)
    )
    skill_finalizer = lambda drafts: hdm._procedural.finalize_skill_drafts(  # noqa: E731
        drafts=drafts, hermes_home=str(PROFILE)
    )
    mem0_client = hdm.MemoryProvider._create_mem0_client(cfg, PROFILE)

    total_ok = 0
    total_fail = 0
    for sid in PENDING_SESSIONS:
        rows = store.fetch_turns(sid, consolidated=False)
        if not rows:
            print(f"[{sid}] no pending — skip")
            continue
        chunks = chunk_rows(rows)
        print(f"\n[{sid}] {len(rows)} pending -> {len(chunks)} chunk")
        for ci, chunk in enumerate(chunks, 1):
            t0 = time.monotonic()
            try:
                report = consolidate_once(
                    session_id=sid,
                    rows=chunk,
                    llm_call=llm_call,
                    mem0_client=mem0_client,
                    shadow_store=store,
                    admission_check=admission_check,
                    skill_router=skill_router,
                    skill_finalizer=skill_finalizer,
                    user_id="default",
                )
                # mark consolidated hanya chunk sukses
                store.mark_consolidated(sid, [int(r["id"]) for r in chunk])
                dt = time.monotonic() - t0
                status = report.get("admission_status", "?")
                print(f"  chunk {ci}: OK in {dt:.1f}s status={status} rows={len(chunk)}")
                total_ok += len(chunk)
            except Exception as e:  # noqa: BLE001
                dt = time.monotonic() - t0
                print(f"  chunk {ci}: FAIL in {dt:.1f}s: {type(e).__name__}: {str(e)[:120]}")
                total_fail += len(chunk)
            sys.stdout.flush()
    print(f"\n=== DONE: {total_ok} rows consolidated, {total_fail} failed/pending ===")
    return 0


# import admission & procedural lazily (mereka import dari __init__ path)
import admission as _admission  # noqa: E402
import procedural as _procedural  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
