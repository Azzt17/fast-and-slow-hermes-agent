# Obsidian → Asa Pilot 1 Review Protocol

Pilot 1 membaca hanya allowlist yang disetujui Farid dan menghasilkan candidate
ledger privat. Ia tidak boleh melakukan `mem0.add`, membuka SQLite provider,
menulis Core Memory, atau mengubah vault.

## Candidate Ledger Minimum

Setiap kandidat menyimpan `candidate_id`, `fact`, `type`, `temporal`, `confidence`,
`sensitivity`, `source_path`, `source_sha256`, serta `review_status=pending`.

## Review Farid

- `approve_stable`: boleh dipertimbangkan untuk semantic long-term memory.
- `approve_current`: hanya candidate temporal; wajib expiry/review date pada Pilot 2.
- `historical_only`: tidak boleh menjawab current-state.
- `exclude`: tidak boleh masuk importer.
- `edit`: Farid menyediakan redaksi yang benar.

Tidak ada action di atas yang menulis runtime memory pada Pilot 1.
