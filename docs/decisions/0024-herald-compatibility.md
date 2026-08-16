# ADR-0024: Kompatibilitas Hermes Herald (agent_context, backup_paths, on_memory_write audit)

**Status**: Diterima
**Tanggal**: 2026-08-16

## Konteks

Hermes di-update ke `v0.20.1` (Herald, 2026-08-13). Kontrak `MemoryProvider`
di versi ini memperluas hook yang tersedia dan mengubah beberapa perilaku:

1. `initialize()` kini menyediakan `agent_context` (`primary`, `subagent`,
   `cron`, `flush`) dan `agent_identity`. Provider disarankan menolak write
   untuk konteks non-primary karena system prompt subagent/cron akan
   mengotori representasi user.
2. `backup_paths()` baru: provider dapat mendeklarasikan path penyimpanan di
   luar `HERMES_HOME` agar ikut `hermes backup`/`hermes import`. Tanpa ini,
   state plugin (SQLite hot_sessions + Chroma) hilang dari arsip.
3. `on_memory_write(action, target, content, metadata)` baru: dipanggil saat
   memory tool bawaan Hermes menulis entri Core Memory. Ini membuka peluang
   sinkronisasi — tetapi **bertentangan dengan prinsip ADR-0005** (Sistem 2
   kita yang mengekstrak fakta; matikan ekstraksi otomatis Mem0) dan prinsip
   quarantine pipeline. Menulis langsung `on_memory_write` ke `trusted` akan
   mem-bypass System-2, admission, dan shadow lifecycle.
4. `sync_turn()` kini menerima `messages` kwarg (sudah kompatibel).
5. `on_session_switch()` kini menerima `parent_session_id`, `reset`, `rewound`
   (sudah kompatibel; `reset=True` berarti benar-benar sesi baru — relevan
   untuk provenance).
6. Boundary `/new` di gateway herald kini memakai `_cleanup_agent_resources`
   → `flush_pending()` + `shutdown_memory_provider(messages)` → `on_session_end`
   — fix manual kita (BETA) sudah diadopsi upstream, sehingga patch gateway
   lokal tidak lagi diperlukan.

## Keputusan

1. **Filter konteks di `initialize`**: simpan `self._agent_context =
   kwargs.get("agent_context", "primary")`. Pada `sync_turn`, jika
   `agent_context != "primary"`, lewati penulisan ke hot_sessions (kecuali
   `flush` yang tetap menulis untuk sesi primary yang sedang di-flush).
   Konsolidasi tetap boleh jalan pada konteks `primary`/`flush`; subagent dan
   cron tidak menulis.

2. **Implementasi `backup_paths()`**: kembalikan
   `[str(self._hermes_home / "hermes-dual-memory")]` — direktori SQLite +
   Chroma provider. Method harus dapat dipanggil tanpa `initialize()` (ABC
   menuntut callable tanpa network); return path absolut dari config/env,
   bukan dari state instance.

3. **Implementasi `on_memory_write()` sebagai audit trail saja**: catat tulis
   Core Memory ke tabel SQLite baru `core_memory_audit` (append-only) dengan
   `{ts, action, target, content_hash, metadata_json, session_id}`. **Tidak**
   menulis ke Mem0/shadow, tidak menandai `trusted`. Ini menjaga prinsip
   ADR-0005 + quarantine: tulis Core Memory bawaan hanyalah jejak yang bisa
   direview, bukan fakta yang otomatis naik ke retrieval. Integrasi lanjutan
   (misal review candidate dari audit) membutuhkan ADR terpisah.

4. **Gunakan `reset` di `on_session_switch` untuk provenance**: simpan
   `parent_session_id` ke `hot_sessions` (kolom baru `parent_session_id`)
   agar lineage /branch /resume tercatat, tanpa mengubah perilaku konsolidasi.

5. **Schema migration**: tambahkan kolom `parent_session_id` di
   `hot_sessions` dan tabel `core_memory_audit` via `ALTER TABLE`/`CREATE
   TABLE IF NOT EXISTS` idempotent di `_ensure_schema` (tanpa migration
   framework; pattern `IF NOT EXISTS`/`PRAGMA table_info` sudah dipakai).

## Alternatif yang Dipertimbangkan

- **Tidak filter `agent_context`**: ditolak. Subagent/cron menulis hot rows
  yang mengotori konsolidasi user (bukti: banyak sesi pending berasal dari
  context non-primary).
- **`on_memory_write` → langsung `trusted` di shadow**: ditolak keras. Ini
  mem-bypass System-2 extraction, admission check, dan quarantine — melanggar
  ADR-0005, ADR-0011, dan prinsip "quarantine sebelum trust".
- **`on_memory_write` → candidate + tunggu review**: ditunda. Pipeline review
  kandidat manual belum ada; audit trail dulu adalah langkah aman.
- **Tidak implement `backup_paths`**: ditolak. Data plugin tidak ikut
  `hermes backup` → risiko kehilangan saat migrasi/rollback.

## Konsekuensi

Positif:

- Subagent/cron tidak lagi mengotori hot_sessions; konsolidasi lebih bersih.
- `hermes backup`/`import` kini menyertakan state dual-memory → rollback &
  migrasi aman.
- Audit trail Core Memory tersedia untuk review tanpa mem-bypass pipeline.
- Lineage sesi (/branch, /resume, compression) tercatat.

Trade-off:

- `sync_turn` di konteks subagent/cron tidak menulis apa pun — memory untuk
  pekerjaan subagent tidak akan muncul di hot_sessions. Ini sengaja: hanya
  hasil yang dibawa kembali ke sesi primary yang layak dikonsolidasi.
- Tabel `core_memory_audit` menyimpan hash konten + metadata; isi mentah
  TIDAK disalin (prinsip "jangan salin memory mentah ke repo").

## Verifikasi

- Unit test: `initialize` dengan `agent_context=subagent` → `sync_turn` tidak
  menulis; `agent_context=primary` → menulis.
- Unit test: `backup_paths()` mengembalikan path dual-memory tanpa
  `initialize`.
- Unit test: `on_memory_write` mencatat audit row; tidak ada baris shadow/Mem0
  baru.
- Unit test: `hot_sessions.parent_session_id` terisi saat
  `on_session_switch(parent_session_id=...)`.
- Full suite + baseline subset sebelum deploy.
