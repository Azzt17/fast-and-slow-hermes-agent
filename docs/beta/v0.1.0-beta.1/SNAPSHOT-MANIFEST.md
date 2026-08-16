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

## BETA-011 Asa Pre-Deploy Snapshot

**Created at**: `2026-07-30T14:38:32+08:00`
**Profile scope**: `default` (Asa) only
**Purpose**: paired code+data rollback sebelum deployment ADR-0021

| Artifact | SHA-256 | Size | Storage class |
|---|---|---:|---|
| Full Hermes backup | `f5596f131b0a5166da644358e1e564b82e2083f340bf15d58ba74ac15297b0b2` | 106.6 MB | private, outside Git |
| Asa dual-memory runtime + plugin | `cad24476d367d8f626ce425687c24611da40cad8e7d530ee54f18cce6943ecbd` | included above | private, outside Git |

Archive checksum PASS. Previous deployed Asa plugin remains retained as
`.hermes-dual-memory.beta-011-predeploy` beside the active plugin.

## BETA-013 Dual-Profile Pre-Deploy Snapshot

**Created at**: `2026-07-30T15:03:21+08:00`
**Profile scope**: `default` (Asa) and `research` (Nellie)
**Purpose**: paired code+data rollback before ADR-0022 rollout

| Artifact | SHA-256 | Storage class |
|---|---|---|
| Default dual-memory runtime + plugin | `2fb8dbe08c77012efa1b05b21d6a2b41800b457904c8729e9f07719f1db0166e` | private, outside Git |
| Research profile archive | `5dcf52add1546201332e0206808b8b7c697173b398014534dc0f4e8962a941ec` | private, outside Git |

Archive checksums PASS. Each profile retains its BETA-013 predeploy plugin.

## Gateway Boundary Fix Pre-Deploy Snapshot

**Created at**: `2026-07-30T15:34:37+08:00`
**Scope**: local Hermes gateway source plus default/research runtime
**Purpose**: rollback before local upstream `/new` lifecycle integration fix

| Artifact | SHA-256 | Storage class |
|---|---|---|
| Hermes gateway source patch set | `c2c736ee2f43a8debd6c9be1f2f036cb1078646716a1adc3db0bbc6369828fa2` | private, outside Git |
| Default runtime | `50585bc042738de9d5f53feb77aad2e8865d947b555ec294ca8765b5732fcebe` | private, outside Git |
| Research runtime | `5573c28f469462ee01162ea168af1b027d30c5488504b66497a0943ec01ff354` | private, outside Git |

All archive checksums PASS.

## BETA-012 Research Pre-Deploy Snapshot

**Created at**: `2026-07-30T14:50:50+08:00`
**Profile scope**: `research` (Nellie) only
**Purpose**: paired code+data rollback sebelum rollout ADR-0021

| Artifact | SHA-256 | Size | Storage class |
|---|---|---:|---|
| Research profile archive | `f1b8fd054657f2570398a5dc82700bd380587dd6a230188114b1db7b1c8aea0e` | private | private, outside Git |

Archive checksum PASS. Previous deployed research plugin remains retained as
`.hermes-dual-memory.beta-011-predeploy` beside the active plugin.
