# Obsidian → Asa Pilot 0

Pilot 0 membuat manifest metadata-only untuk review file-level. Ia **bukan**
semantic analysis, candidate ledger, vector import, atau write ke runtime memory.

## Kontrak

- Source vault read-only; output manifest harus berada di luar vault.
- Tidak ada isi note, excerpt, credential, embedding, Mem0, SQLite, atau model
  call pada tahap ini.
- Setiap record memuat path relatif, SHA-256, ukuran, mtime, frontmatter/tag/link
  metadata, revision family, klasifikasi, dan alasan.
- Artifact manifest bersifat privat (`0600`); jangan commit ke Git karena path dan
  metadata pribadi masih sensitif.

## Klasifikasi Default

- `excluded`: non-Markdown, `.obsidian`, `00-inbox`, `04-archive`, koleksi
  `DailyJournal`, `DreamJournal`, dan `news-digest`.
- `needs_review`: seluruh Markdown lain, termasuk nama file dengan marker sensitif.
  Tidak ada file otomatis `candidate` atau `trusted`.

## Jalankan

```bash
python3 scripts/obsidian_import_dry_run.py \
  --vault /path/to/vault \
  --output /path/private/vault-import-manifest.jsonl
```

Review file-level dilakukan dari manifest. Hanya allowlist eksplisit yang boleh
melanjutkan ke Pilot 1 semantic candidate ledger. Pilot 1 membutuhkan approval
Farid, snapshot runtime, baseline comparison, dan tidak boleh ditulis sebelum
ADR/tes yang relevan PASS.
