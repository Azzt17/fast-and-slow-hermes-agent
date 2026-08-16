"""Recovery konsolidasi untuk hot rows pending (consolidated=0) di profil coding.

Meniru persis alur produksi _consolidate_locked:
- fetch pending rows per session
- chunk_rows (whole-turn, 6000 char)
- consolidate_once per chunk (llm_call 90s, admission, mem0.add, shadow record)
- mark_consolidated hanya untuk chunk yang sukses

Dibedakan dari versi research:
- HERMES_HOME menunjuk profil coding
- memakai model `ada-low` via env override (root cause 404 `codex-subagent`)
- PENDING_SESSIONS diisi otomatis dari DB (semua sesi yang masih punya pending)

AMAN: memakai jalur storage + consolidation yang sama dengan gateway. Tidak
memodifikasi skema; hanya menjalankan pipeline konsolidasi yang idempotent
terhadap row yang masih pending. Snapshot dibuat sebelum dijalankan.
"""
import importlib.util
import os
import sys
import time
from pathlib import Path

HERMES_PROFILE = Path("/home/wajdi/.hermes/profiles/coding")
os.environ["HERMES_HOME"] = str(HERMES_PROFILE)

# Load .env secara langsung (tanpa shell parsing) supaya API key & model override aktif
env_path = HERMES_PROFILE / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

# Jamin model konsolidasi = ada-low (root cause fix). Env override menang di
# _default_mem0_config, tapi set eksplisit supaya konsisten walau .env berubah.
os.environ["HERMES_DUAL_MEMORY_LLM_MODEL"] = "ada-low"

PLUGIN_DIR = Path("/home/wajdi/hermes-dual-memory/plugins/memory/hermes-dual-memory")
sys.path.insert(0, str(PLUGIN_DIR))

from storage import HotSessionStore  # noqa: E402
from consolidation import consolidate_once, chunk_rows  # noqa: E402

spec = importlib.util.spec_from_file_location("hdm", str(PLUGIN_DIR / "__init__.py"))
hdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hdm)

STORE_DIR = HERMES_PROFILE / "hermes-dual-memory"
DB = STORE_DIR / "hot_sessions.sqlite3"


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
        report=report, session_id="recovery-coding", hermes_home=str(HERMES_PROFILE)
    )
    skill_finalizer = lambda drafts: _procedural.finalize_skill_drafts(  # noqa: E731
        drafts=drafts, hermes_home=str(HERMES_PROFILE)
    )
    mem0_client = hdm.MemoryProvider._create_mem0_client(cfg, HERMES_PROFILE)

    # Semua sesi dengan pending rows (bukan eksklusif list)
    import sqlite3
    conn = sqlite3.connect(str(DB))
    sids = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT session_id FROM hot_sessions WHERE consolidated = 0 ORDER BY session_id"
        ).fetchall()
    ]
    conn.close()
    print(f"Pending total: {len(sids)} sessions waiting")
    print("Model konsolidasi:", (cfg or {}).get("llm", {}).get("config", {}).get("model"))

    total_ok = 0
    total_fail = 0
    for sid in sids:
        sid_rows = store.fetch_turns(sid, consolidated=False)
        if not sid_rows:
            print(f"[{sid}] no pending — skip")
            continue
        chunks = chunk_rows(sid_rows)
        print(f"\n[{sid}] {len(sid_rows)} pending -> {len(chunks)} chunk")
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
            except Exception as e:  # noqa: BLE001
                dt = time.monotonic() - t0
                print(f"  chunk {ci}: FAIL in {dt:.1f}s: {type(e).__name__}: {str(e)[:120]}")
                total_fail += len(chunk)
            sys.stdout.flush()

    print(f"\n=== DONE: {total_ok} rows consolidated, {total_fail} failed/pending ===")
    return 0


import admission as _admission  # noqa: E402
import procedural as _procedural  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())