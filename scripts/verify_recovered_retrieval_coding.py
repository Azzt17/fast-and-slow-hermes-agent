"""Verifikasi retrieval memory yang baru di-recover di profil coding.

Membuka mem0 client yang sama dengan produksi, search beberapa query yang
berhubungan dengan konten sesi coding yang di-recover, lalu join ke shadow
index untuk memastikan hanya status=trusted yang visible.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERMES_PROFILE = Path("/home/wajdi/.hermes/profiles/coding")
os.environ["HERMES_HOME"] = str(HERMES_PROFILE)

env_path = HERMES_PROFILE / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

os.environ["HERMES_DUAL_MEMORY_LLM_MODEL"] = "ada-low"

PLUGIN_DIR = Path("/home/wajdi/hermes-dual-memory/plugins/memory/hermes-dual-memory")
sys.path.insert(0, str(PLUGIN_DIR))

from storage import HotSessionStore  # noqa: E402

spec = importlib.util.spec_from_file_location("hdm", str(PLUGIN_DIR / "__init__.py"))
hdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hdm)

STORE_DIR = HERMES_PROFILE / "hermes-dual-memory"
store = HotSessionStore(str(STORE_DIR))

cfg = hdm.MemoryProvider._default_mem0_config(HERMES_PROFILE)
mem0 = hdm.MemoryProvider._create_mem0_client(cfg, HERMES_PROFILE)

QUERIES = [
    "analisis proses konsolidasi memory profile coding",
    "dual memory hermes arsitektur provider hot tier",
    "recovery pending konsolidasi system 2",
    "profil coding partner teknik",
]

for q in QUERIES:
    try:
        results = mem0.search(q, filters={"user_id": "default"}, limit=5)
        hits = results.get("results", results) if isinstance(results, dict) else results
        print(f"\n### query: {q!r}")
        for r in hits:
            mid = r.get("id") or r.get("memory_id") or "?"
            score = r.get("score")
            mem = (r.get("memory") or "")[:80]
            states = store.retrieval_states([mid]) if mid != "?" else {}
            st = states.get(mid, {})
            status = st.get("status", "NO_SHADOW")
            print(f"  [{status}] score={score:.3f} id={mid[:12]} :: {mem}")
    except Exception as e:  # noqa: BLE001
        print(f"\n### query {q!r} FAILED: {type(e).__name__}: {e}")

print("\n=== DONE ===")