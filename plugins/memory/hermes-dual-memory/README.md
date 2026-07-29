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

Explicit historical queries (`before`, `previous`, `riwayat`, `sebelum`, and
related deterministic markers) may retrieve trusted superseded semantic rows.
Current-state queries still hide every superseded row; historical blocks carry
their validity boundary so the model can distinguish old and current state.
Quarantined and superseded episodic rows remain hidden (ADR-0014).

Scored results that survive the relevance threshold and shadow policy pass one
bounded batch answerability check before context injection. Only candidates
with explicit evidence for the query remain visible. Missing/invalid decisions,
timeout, and verifier unavailability reject scored candidates; unscored legacy
results retain the ADR-0009 compatibility path (ADR-0015).

Operational overrides: `HERMES_DUAL_MEMORY_MIN_SCORE` controls the low score
gate (default `0.55`), while `HERMES_DUAL_MEMORY_ANSWERABILITY_TIMEOUT` bounds
the full answerability operation including one format-only retry (default `5`
seconds).

Phase 5 adds opportunistic episodic decay through the existing `initialize()`
and `on_session_end()` lifecycle hooks. Retrieval updates stability and access
history; low-retrievability episodic entries move cold, repeated access can
promote them, and similar cold clusters are compacted by System 2 with source
lineage preserved. Semantic entries are excluded from decay (ADR-0010).

Phase 6 adds two-layer admission before a persisted candidate becomes trusted:
Hermes `tools.threat_patterns` strict scanning (with a standalone fallback),
then a bounded semantic hidden-instruction review. Pattern/semantic failures and
semantic unavailability are fail-closed to `quarantined`; the existing shadow
status gate blocks them from retrieval and compression context (ADR-0011).

Phase 7 routes trusted `new_skills` into JSON drafts under
`~/.hermes/hermes-dual-memory/skill-drafts/`, outside the active Skills tree.
Near-duplicates are marked `redundant`. Pending drafts require explicit
`hermes hermes-dual-memory skills approve <draft-id>` promotion; the plugin then
reuses Hermes' native skill validator/security writer and marks the result
agent-created so the built-in Curator owns subsequent lifecycle (ADR-0012).
