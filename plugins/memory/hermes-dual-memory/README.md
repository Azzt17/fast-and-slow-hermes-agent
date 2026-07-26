# hermes-dual-memory

Hermes memory provider implementing the Phase 1 hot SQLite tier and the minimal
Phase 2 System-2 consolidation pipeline. Raw turns are written asynchronously
to `hot_sessions`; `on_session_end` and `on_pre_compress` distill pending rows
through the §4.3 JSON prompt and write the resulting essence to Mem0 with
`infer=False`.
