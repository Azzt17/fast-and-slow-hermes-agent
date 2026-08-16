"""Recovery konsolidasi untuk hot rows pending (consolidated=0) di profil research.

Meniru persis alur produksi _consolidate_locked:
- fetch pending rows per session
- chunk_rows (whole-turn, 6000 char)
- consolidate_once per chunk (llm_call 90s, admission, mem0.add, shadow record)
- mark_consolidated hanya untuk chunk yang sukses

AMAN: memakai jalur storage + consolidation yang sama dengan gateway. Tidak
memodifikasi skema; hanya menjalankan pipeline konsolidasi yang idempotent
terhadap row yang masih pending. Snapshot dibuat sebelum dijalankan.
"""
import os
import sys
import time
import importlib.util
from pathlib import Path

HERMES_PROFILE = Path(os.path.expanduser("~/.hermes/profiles/research"))
os.environ["HERMES_HOME"] = str(HERMES_PROFILE)

PLUGIN_DIR = Path(os.path.expanduser("~/hermes-dual-memory/plugins/memory/hermes-dual-memory"))
sys.path.insert(0, str(PLUGIN_DIR))

from storage import HotSessionStore  # noqa: E402
from consolidation import consolidate_once, chunk_rows  # noqa: E402

# load __init__ for _load_llm_callable / _default_mem0_config / admission / procedural
spec = importlib.util.spec_from_file_location("hdm", str(PLUGIN_DIR / "__init__.py"))
hdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hdm)

STORE_DIR = HERMES_PROFILE / "hermes-dual-memory"
DB = STORE_DIR / "hot_sessions.sqlite3"

# Sesi lama yang pending (dari verifikasi sebelumnya; eksklusif sesi aktif 20260805_*)
PENDING_SESSIONS = [
    "20260730_184221_077ec125",
    "20260731_151911_a1bc21d1",
    "20260803_101159_b44b58b7",
    "20260804_190759_9b61cee4",
    "20260804_210420_ecd900e7",
]


def main():
    store = HotSessionStore(str(STORE_DIR))
    cfg = hdm.MemoryProvider._default_mem0_config(HERMES_PROFILE)
    llm_call = hdm.MemoryProvider._load_llm_callable(cfg)
    if llm_call is None:
        print("FATAL: llm_call None")
        return 1

    admission_check = lambda content: _admission.evaluate_admission(  # noqa: E731
        content, llm_call=llm_call, timeout_seconds=5.0
    )
    skill_router = lambda report: _procedural.route_new_skills(  # noqa: E731
        report=report, session_id="recovery", hermes_home=str(HERMES_PROFILE)
    )
    skill_finalizer = lambda drafts: _procedural.finalize_skill_drafts(  # noqa: E731
        drafts=drafts, hermes_home=str(HERMES_PROFILE)
    )
    mem0_client = hdm.MemoryProvider._create_mem0_client(cfg, HERMES_PROFILE)

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
                store.mark_consolidated(sid, [int(r["id"]) for r in chunk])
                dt = time.monotonic() - t0
                status = report.get("admission_status", "?")
                print(f"  chunk {ci}: OK in {dt:.1f}s status={status} rows={len(chunk)}")
                total_ok += len(chunk)
            except Exception as e:
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