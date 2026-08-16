# hermes-dual-memory

Provider memori untuk **Hermes Agent** yang menerapkan arsitektur memori dua-proses (System 1 / System 2) ala *Thinking, Fast and Slow* (Kahneman) — dengan policy bi-temporal, quarantine, decay, dan retrieval yang di-gate oleh answerability.

Plugin ini **bukan** provider `mem0` resmi Hermes. Ia membungkus library `mem0ai` sebagai backend penyimpanan/penelusuran internal, sementara seluruh kebijakan memori (trust, lifecycle, retrieval filtering) dipegang oleh plugin ini sendiri.

> **Status**: Beta `v0.1.0-beta.1` **Selesai** (2026-08-16). Fase 9 — Hardening & Rilis Portofolio sedang berjalan.

---

## Daftar Isi

- [Cara Kerja](#cara-kerja)
- [Fitur](#fitur)
- [Prasyarat](#prasyarat)
- [Instalasi](#instalasi)
- [Konfigurasi](#konfigurasi)
- [Penggunaan](#penggunaan)
- [Testing](#testing)
- [Pemecahan Masalah](#pemecahan-masalah)
- [Arsitektur & Keputusan](#arsitektur--keputusan)
- [Status & Roadmap](#status--roadmap)
- [Lisensi](#lisensi)

---

## Cara Kerja

```
┌──────────────────────────────────────────────────────────────┐
│  System 1 — Hot Capture (cepat, selalu jalan)                 │
│  sync_turn() menulis turn mentah ke SQLite hot_sessions       │
│  (async daemon thread, non-blocking)                          │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  System 2 — Konsolidasi (lambat, deterministik)               │
│  on_session_end / on_pre_compress:                            │
│  pending rows → chunk → laporan §4.3 (JSON) → admission →      │
│  Mem0 add (infer=False) + shadow index (memory_index)          │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Retrieval — answerability-gated                              │
│  prefetch() → shadow policy → relevance threshold →            │
│  answerability check → context injection                      │
└──────────────────────────────────────────────────────────────┘
```

**Prinsip inti**: yang mengekstrak fakta adalah **System 2 plugin** (lewat laporan konsolidasi terstruktur), **bukan** mesin auto-extraction Mem0 — karena itu semua write memakai `infer=False`. Mem0 hanyalah backend, bukan otoritas trust/lifecycle.

---

## Fitur

- **Hot-tier capture asinkron** — turn mentah ditulis ke SQLite `hot_sessions` tanpa memblokir percakapan.
- **Konsolidasi deterministik** — laporan JSON terstruktur (§4.3) dengan validasi ketat; retry + sanitize otomatis untuk output model yang melanggar batas.
- **Quarantine fail-closed** — admission dua lapis (pattern + semantic); entri yang mencurigakan **tidak pernah** masuk retrieval sampai ditinjau.
- **Shadow index bi-temporal** — setiap essence Mem0 punya baris di `memory_index` dengan `t_valid`/`t_invalid`; kontradiksi **men-supersede**, bukan menghapus.
- **Answerability gate** — hanya hasil yang punya bukti eksplisit untuk query yang masuk context; abstention jujur kalau data tidak ada.
- **Decay oportunistik** — entri episodik yang jarang diakses berpindah tier; semantic-permanent tidak ikut terdemosi.
- **Procedural memory via Skills** — draft skill tervalidasi dirutekan ke sistem Skills Hermes (bukan disimpan sebagai prosa).
- **Isolasi profile** — semua path storage memakai `hermes_home` dari `initialize()`; tiap profile Hermes punya DB sendiri.
- **Kompatibilitas herald** — filter `agent_context` (subagent/cron skip), `backup_paths()`, audit trail `on_memory_write`, lineage `parent_session_id` (ADR-0024).

---

## Prasyarat

- **Python** 3.11+ (diuji pada 3.11.15)
- **Hermes Agent** herald v0.20.1+ (2026.8.13) — kontrak MemoryProvider terbaru
- **mem0ai** (library OSS in-process)
- **Chroma** (vector store lokal, backend mem0)
- Linux/macOS (diuji pada Linux; Windows belum didukung)

---

## Instalasi

### 1. Siapkan venv Hermes

```bash
python3 -m venv /path/to/hermes-agent/.venv
source /path/to/hermes-agent/.venv/bin/activate
pip install -U pip
```

### 2. Install dependensi

```bash
pip install mem0ai chromadb
```

> Pastikan versi mem0ai kompatibel dengan Chroma lokal. Lihat `requirements` project untuk versi yang diuji.

### 3. Salin plugin

```bash
# Dari repo ini:
mkdir -p ~/.hermes/plugins/
cp -r plugins/memory/hermes-dual-memory ~/.hermes/plugins/
```

Untuk profile khusus (mis. `coding`):

```bash
mkdir -p ~/.hermes/profiles/coding/plugins/
cp -r plugins/memory/hermes-dual-memory ~/.hermes/profiles/coding/plugins/
```

### 4. Aktifkan sebagai memory provider

Edit `config.yaml` profile (default: `~/.hermes/config.yaml`):

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: hermes-dual-memory
```

> ⚠️ **Jangan** aktifkan provider resmi `mem0` bersamaan — aturan "satu provider aktif" Hermes akan menolaknya.

### 5. Restart gateway

```bash
hermes gateway restart
```

> Dari sesi agent, restart diblokir (guard anti-loop). Jalankan dari shell terpisah, atau `env -u _HERMES_GATEWAY hermes -p <profile> gateway restart` di background.

---

## Konfigurasi

### Environment (`.env` profile)

| Variabel | Default | Keterangan |
|---|---|---|
| `HERMES_DUAL_MEMORY_LLM_MODEL` | (fallback config.yaml) | Model untuk konsolidasi System-2. **Wajib** model yang callable lewat endpoint provider — jangan alias routing/subagent. |
| `HERMES_DUAL_MEMORY_LLM_TIMEOUT` | 90 (min guard 60) | Timeout konsolidasi per chunk (detik). |
| `HERMES_DUAL_MEMORY_MIN_SCORE` | 0.55 | Ambang skor relevansi retrieval. |
| `HERMES_DUAL_MEMORY_ANSWERABILITY_TIMEOUT` | 5 | Timeout penuh operasi answerability (detik). |

### Storage

Semua data tersimpan di `$HERMES_HOME/hermes-dual-memory/`:

```
hot_sessions.sqlite3   # System-1 capture + memory_index + maintenance_state
history.db             # riwayat Mem0
chroma/                # vector store (embeddings + HNSW)
```

`backup_paths()` (ADR-0024) mendeklarasikan direktori ini ke `hermes backup`, sehingga data dual-memory otomatis masuk arsip.

---

## Penggunaan

Setelah aktif, plugin bekerja otomatis:

1. **Capture** — setiap turn ditulis ke `hot_sessions` (async).
2. **Konsolidasi** — saat sesi berakhir (`/new`, `/reset`) atau kompresi (`on_pre_compress`), pending rows dikonsolidasi ke Mem0 + shadow index.
3. **Retrieval** — `prefetch()` menyuntikkan konteks relevan (trusted, answerability-passed) ke prompt.

### Perintah CLI plugin

```bash
python -m plugins.memory.hermes-dual-memory.cli --help
```

### Verifikasi cepat

```python
# Catatan: nama kelas provider adalah MemoryProvider (bukan HermesDualMemoryProvider)
from plugins.memory.hermes_dual_memory import MemoryProvider  # atau load via importlib (lihat tests/)

from storage import HotSessionStore

store = HotSessionStore("$HERMES_HOME/hermes-dual-memory")
print(store.pending_count("session-id"))        # pending belum konsolidasi
print(store.stats())                            # ringkasan memory_index
```

> ⚠️ **Guard gateway**: mengimpor `__init__.py` dari dalam sesi gateway diblokir
> (string "gateway" di komentar memicu guard anti-restart). Untuk smoke test,
> jalankan dari shell terpisah atau via `systemd-run --user --collect`.

---

## Testing

```bash
# Dari root repo, dengan venv Hermes:
HERMES_SOURCE_ROOT=/path/to/hermes-agent \
  /path/to/hermes-agent/.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Hasil saat ini: **87/87 PASS** (termasuk test kompatibilitas herald ADR-0024).

> `HERMES_SOURCE_ROOT` wajib diset — tanpa itu, 3 test integrasi runtime gagal (pre-existing env, bukan regresi plugin).

---

## Pemecahan Masalah

| Gejala | Penyebab | Solusi |
|---|---|---|
| Konsolidasi tidak jalan, log `404 No active credentials for provider: openai` | Model konsolidasi resolve salah (alias routing) | Set `HERMES_DUAL_MEMORY_LLM_MODEL=<model valid>` di `.env` profile |
| `ValueError: new_skills detail cannot exceed 1200 characters` | Draft skill dari LLM terlalu panjang | Sudah di-fix (ADR-0024/Fase 9): `sanitize_new_skills=True` drop item buruk, lanjut fakta |
| Test `sqlite3.OperationalError: disk I/O error` | Test panggil `initialize()` tanpa `shutdown()` | Selalu `shutdown()` di akhir test (daemon thread menulis DB) |
| `~` tidak expand ke profile dir | Hermes remap `HOME` sesi | Pakai `$HERMES_HOME` atau path absolut |
| Pending rows menumpuk tanpa error | Cek trigger boundary benar-benar fire | `maintenance_state.last_consolidation_error`; recovery idempotent |
| Retrieval kosong setelah restore | Rollback tanpa chroma = recall hilang | Selalu restore paired code+data; `hermes backup` (ADR-0024) menyertakan chroma |

---

## Arsitektur & Keputusan

Dokumentasi lengkap:

- `docs/architecture/final-architecture.md` — arsitektur final (fase 0–9)
- `docs/decisions/` — ADR 0001–0025 (semua keputusan desain)
- `docs/beta/v0.1.0-beta.1/` — jurnal beta, CURRENT.md, CLOSURE-SUMMARY
- `docs/testing/baselines/` — baseline Fase 8 (kontrak regresi)
- `docs/demo/alur-kerja.md` — demo alur kerja end-to-end (teks)

**ADR kunci**: 0005 (System 2 yang ekstrak, bukan Mem0), 0009 (legacy compatibility), 0010 (decay semantic-permanent), 0014 (superseded episodic hidden), 0015 (answerability gate), 0023 (timeout 90s), 0024 (kompatibilitas herald), 0025 (evaluasi micro-compaction/context engine).

---

## Status & Roadmap

- **Fase 0–8**: Selesai (arsitektur, hot tier, konsolidasi, shadow, security, procedural, evaluasi).
- **Beta v0.1.0-beta.1**: Selesai 2026-08-16 — 14/14 hari aktif, 49/30 sesi, baseline PASS, rollback drill PASS, test 87/87.
- **Fase 9 (aktif)**: Hardening & Rilis Portofolio — README, demo, uji instalasi bersih, cleanup.

---

## Lisensi

[MIT](LICENSE) — lihat file `LICENSE`.

---

*Dibangun di atas Hermes Agent (Nous Research). Bukan produk resmi Nous Research.*
