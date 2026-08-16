"""Verifikasi retrieval memory yang baru di-recover di profil research.

Membuka mem0 client yang sama dengan produksi, search beberapa query yang
berhubungan dengan konten sesi-sesi yang di-recover, lalu join ke shadow index
untuk memastikan hanya status=trusted yang visible.
"""
import os
import sys
import importlib.util
from pathlib import Path

HERMES_PROFILE = Path(os.path.expanduser("~/.hermes/profiles/research"))
os.environ["HERMES_HOME"] = str(HERMES_PROFILE)

PLUGIN_DIR = Path(os.path.expanduser("~/hermes-dual-memory/plugins/memory/hermes-dual-memory"))
sys.path.insert(0, str(PLUGIN_DIR))

from storage import HotSessionStore  # noqa: E402

spec = importlib.util.spec_from_file_location("hdm", str(PLUGIN_DIR / "__init__.py"))
hdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hdm)

STORE_DIR = HERMES_PROFILE / "hermes-dual-memory"
store = HotSessionStore(str(STORE_DIR))

cfg = hdm.MemoryProvider._default_mem0_config(HERMES_PROFILE)
mem0 = hdm.MemoryProvider._create_mem0_client(cfg, HERMES_PROFILE)

# Query yang relevan dengan sesi-sesi yang di-recover (topik riset/teknis)
QUERIES = [
    "analisis sistem dual memory hermes konsolidasi",
    "decay retrievability shadow index",
    "9router model routing fallback",
    "preferensi prompting panjang dan detail",
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
            # join ke shadow via retrieval_states (status/t_invalid)
            states = store.retrieval_states([mid]) if mid != "?" else {}
            st = states.get(mid, {})
            status = st.get("status", "NO_SHADOW")
            print(f"  [{status}] score={score:.3f} id={mid[:12]} :: {mem}")
    except Exception as e:
        print(f"\n### query {q!r} FAILED: {type(e).__name__}: {e}")

print("\n=== DONE ===")