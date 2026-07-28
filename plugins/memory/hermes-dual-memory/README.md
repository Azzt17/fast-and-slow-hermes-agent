# hermes-dual-memory

Hermes memory provider implementing the hot SQLite tier, deterministic System-2
consolidation, bounded Mem0 retrieval, and the Phase 4 shadow index. Raw turns
are written asynchronously to `hot_sessions`; `on_session_end` and
`on_pre_compress` distill pending rows through the §4.3 JSON prompt and write
essence to Mem0 with `infer=False`.

Each new Mem0 essence is linked to `memory_index` in the same SQLite file.
Semantic contradictions supersede old shadows through `t_invalid` rather than
deletion. The existing `prefetch()`/`queue_prefetch()` path consults those
shadows before returning Mem0 results. Legacy Mem0 entries without shadow rows
remain visible for backward compatibility (ADR-0009).
