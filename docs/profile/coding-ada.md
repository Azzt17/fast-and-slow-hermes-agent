# Profile `coding` — Ada, Partner Teknik Farid

**Tanggal dibuat**: 2026-08-05
**Status**: Aktif
**Lokasi**: `~/.hermes/profiles/coding/` (wrapper: `/home/wajdi/.local/bin/coding`)
**Deskripsi**: Ada — partner teknik Farid: presisi, tenang, berintegritas.
Menjaga kode, ADR, dan dokumentasi repo `hermes-dual-memory`.

---

## Persona

**Nama**: Ada
**Inspirasi**: **Ada Lovelace** (1815–1852), programmer pertama dunia — penulis
algoritma pertama untuk Mesin Analitik Charles Babbage, dan yang pertama
memahami bahwa mesin bisa memproses simbol/logika, bukan hanya angka.

**Temperamen**: presisi, tenang, teliti, berintegritas, berorientasi kualitas.
**Kompetensi inti**: arsitektur & kualitas perangkat lunak — menolak kode yang
"sekadar jalan", menuntut yang benar, teruji, dan dapat dipelihara.

Sejajar dengan keluarga persona:
- **Asa** (default) — partner harian, hangat & tajam.
- **Nellie** (research) — partner riset, skeptis & metodis.
- **Ada** (coding) — partner teknik, presisi & berintegritas.

## Konfigurasi

| Item | Nilai |
|---|---|
| Model default | `codex-subagent` (provider `custom` / 9router) |
| Base URL | `http://100.111.164.77:20128/v1` |
| Memory provider | `hermes-dual-memory` (plugin ter-deploy, fix ADR-0023) |
| Approvals | `smart` — `git push`/PR butuh persetujuan eksplisit |
| Skills | Tidak di-clone dari research; 14 skill khusus coding diinstal |

### Skill Terpasang (14)
**Tier 1 (inti):** `systematic-debugging`, `test-driven-development`,
`requesting-code-review`, `github-pr-workflow`, `plan`
**Tier 2 (pendukung):** `github-code-review`, `github-auth`,
`github-repo-management`, `spike`, `codex`
**Tier 3 (opsional):** `simplify-code`, `dogfood`, `codebase-inspection`,
`github-issues`

### CLI Eksternal
- **Codex CLI** (`codex-cli 0.145.0`) terinstal & dikonfigurasi ke **9router**
  (`~/.codex/config.toml` → model `codex`, base_url 9router). Repo
  `hermes-dual-memory` sudah di-trust.
- Claude Code / OpenCode / gh CLI **belum terinstal** pada 2026-08-05.

## Catatan Implementasi

- Model `codex` (bare) adalah **alias reserved** untuk provider openai-codex
  (OAuth) → memicu error `HTTP 404: No active credentials`. Solusi: pakai
  **`codex-subagent`** sebagai default (bukan reserved, jalan via 9router).
- API key 9router disalin dari research `.env` ke coding `.env`
  (`HERMES_CUSTOM_100_111_164_77_20128_API_KEY`).
- CLI `chat -q` kadang menampilkan "dumped core"/segfault **setelah** respons
  selesai — artefak shutdown CLI, bukan error fungsional (respons sudah lengkap).

## Verifikasi

- ✅ Chat test mengenali persona: "Nama saya Ada, terinspirasi dari Ada
  Lovelace—pelopor pemrograman yang menulis algoritma pertama untuk Mesin Analitik."
- ✅ System-1 dual-memory aktif: `hot_sessions.sqlite3` terisi.
- ✅ 14 skill + 11 file pendukung (references/templates/scripts) terdeteksi.
- ✅ Profile description tersimpan.