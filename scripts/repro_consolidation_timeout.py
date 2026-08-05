"""Repro harness: reproduce consolidation timeout + measure actual latency.

Uses the exact production path: _load_llm_callable (9router config) + consolidation
prompt built from the pending rows of the stuck research session.
Read-only: does NOT write to hot_sessions, memory_index, or mem0.
"""
import os
import sys
import time
import json

HERMES_PROFILE = os.path.expanduser("~/.hermes/profiles/research")
os.environ["HERMES_HOME"] = HERMES_PROFILE

PLUGIN_DIR = os.path.expanduser(
    "~/hermes-dual-memory/plugins/memory/hermes-dual-memory"
)
sys.path.insert(0, PLUGIN_DIR)

from storage import HotSessionStore  # noqa: E402
from consolidation import build_prompt, chunk_rows  # noqa: E402

# Load the plugin's __init__ to reuse _load_llm_callable and _default_mem0_config
import importlib.util  # noqa: E402
_init_path = os.path.join(PLUGIN_DIR, "__init__.py")
spec = importlib.util.spec_from_file_location("hdm_init", _init_path)
hdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hdm)

STORE_DIR = os.path.join(HERMES_PROFILE, "hermes-dual-memory")
DB = os.path.join(STORE_DIR, "hot_sessions.sqlite3")

# Sessions that are stuck (consolidated=0) in research
STUCK_SESSIONS = [
    "20260730_184221_077ec125",  # the one that crashed in logs (23 rows)
    "20260731_151911_a1bc21d1",  # 30 rows
    "20260804_210420_ecd900e7",  # most recent, 10 rows
]


def main():
    store = HotSessionStore(STORE_DIR)
    cfg = hdm.MemoryProvider._default_mem0_config(__import__("pathlib").Path(HERMES_PROFILE))
    llm_call = hdm.MemoryProvider._load_llm_callable(cfg)

    if llm_call is None:
        print("FATAL: llm_call is None — 9router config not resolvable from plugin loader")
        return 1

    print(f"llm_call resolved: {getattr(llm_call, '__name__', 'configured_call')}")
    print(f"mem0_config llm: {cfg and (cfg.get('llm') or {}).get('config')}")
    print("=" * 70)

    for sid in STUCK_SESSIONS:
        rows = store.fetch_turns(sid, consolidated=False)
        if not rows:
            print(f"[{sid}] no pending rows — SKIP")
            continue
        chunks = chunk_rows(rows)
        total_rows = len(rows)
        print(f"\n[{sid}] {total_rows} pending rows -> {len(chunks)} chunk(s)")

        for ci, chunk in enumerate(chunks, 1):
            chars = sum(len(str(r.get("content", ""))) for r in chunk)
            messages = build_prompt(sid, chunk)
            print(f"  chunk {ci}: {len(chunk)} rows, ~{chars} chars, prompt ~{sum(len(m['content']) for m in messages)} chars")

            # call with the production default timeout (30s) — reproduce
            t0 = time.monotonic()
            try:
                resp = llm_call(
                    task="memory_consolidation",
                    messages=messages,
                    temperature=0,
                    max_tokens=3000,
                )
                dt = time.monotonic() - t0
                content = getattr(resp, "choices", [{}])[0] if hasattr(resp, "choices") else resp
                text = ""
                try:
                    text = resp.choices[0].message.content
                except Exception:
                    text = str(resp)[:200]
                print(f"    -> SUCCESS in {dt:.1f}s (len={len(text) or 0})")
            except Exception as e:
                dt = time.monotonic() - t0
                print(f"    -> FAILED in {dt:.1f}s: {type(e).__name__}: {e}")
            # flush per chunk
            sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())