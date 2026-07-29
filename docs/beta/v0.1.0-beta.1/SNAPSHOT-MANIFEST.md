# Snapshot Manifest

**Status**: Belum dibuat
**Code tag**: `v0.1.0-beta.1`
**Code commit**: `18c770bfdd0099cacc647de1f88259b8be8f9128`
**Created at**: Belum dibuat
**Gateway stopped**: Belum diverifikasi
**Hermes profile**: `default`
**Memory provider**: `hermes-dual-memory`

## Snapshot Artifacts

| Artifact | SHA-256 | Size | Storage class |
|---|---|---:|---|
| Full Hermes backup | pending | pending | private, outside Git |
| Dedicated plugin+memory archive | pending | pending | private, outside Git |

## Data Included

- `$HERMES_HOME/hermes-dual-memory/hot_sessions.sqlite3`
- `$HERMES_HOME/hermes-dual-memory/history.db`
- `$HERMES_HOME/hermes-dual-memory/chroma/`
- `$HERMES_HOME/hermes-dual-memory/skill-drafts/`
- `$HERMES_HOME/plugins/hermes-dual-memory/`

## Integrity

- Hot/shadow SQLite: preflight `ok`; snapshot result pending
- Mem0 history SQLite: preflight `ok`; snapshot result pending
- Chroma archive extraction smoke: pending
- Plugin hash vs checkpoint: pending

Jangan menaruh path snapshot privat, credential, atau isi memory mentah di file
ini. Path operasional dapat dicatat lokal di `CURRENT.md` hanya bila aman.
