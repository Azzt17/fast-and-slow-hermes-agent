# Snapshot Manifest

**Status**: Selesai dan terverifikasi
**Code tag**: `v0.1.0-beta.1`
**Code commit**: `18c770bfdd0099cacc647de1f88259b8be8f9128`
**Created at**: `2026-07-29T12:28:52+08:00`
**Gateway stopped**: Ya, `default` dan `research`
**Hermes profile**: `default` dan `research`
**Memory provider**: `hermes-dual-memory`

## Snapshot Artifacts

| Artifact | SHA-256 | Size | Storage class |
|---|---|---:|---|
| Full Hermes clean-start backup | `269b250033964979242a4252364f2cd002965f33b321d2114d13a7aacf5e0d29` | 107,605,295 B | private, outside Git |
| Default profile runtime | `91128cf7a915aee09f83b96bcc19e6f64e9c7ca8b1af0ea9ef0dfe226cb2394b` | 204,227 B | private, outside Git |
| Research profile | `2fbdf921aabcfae60bec90bf3c70f59c514df86ff88f78cf884fc7a5a7625a46` | 11,093,464 B | private, outside Git |

## Data Included

- `$HERMES_HOME/hermes-dual-memory/hot_sessions.sqlite3`
- `$HERMES_HOME/hermes-dual-memory/history.db`
- `$HERMES_HOME/hermes-dual-memory/chroma/`
- `$HERMES_HOME/hermes-dual-memory/skill-drafts/`
- `$HERMES_HOME/plugins/hermes-dual-memory/`
- Persona Asa (`SOUL.md` dan tiga skill khusus)
- Profile research/Nellie lengkap, termasuk config dan storage terisolasi

## Integrity

- Hot/shadow SQLite kedua profile: `ok`
- Mem0 history SQLite kedua profile: `ok`
- ZIP integrity dan listing kedua tar archive: PASS
- Plugin hash vs checkpoint pada kedua profile: PASS
- Fresh-state counts: `0` hot turn, shadow memory, session, dan message
- Pre-mutation snapshot data uji juga dipertahankan privat sebagai rollback/audit
  source terpisah; clean-start artifacts di atas adalah rollback point beta resmi.

Jangan menaruh path snapshot privat, credential, atau isi memory mentah di file
ini. Path operasional dapat dicatat lokal di `CURRENT.md` hanya bila aman.
