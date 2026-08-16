# Demo Alur Kerja — hermes-dual-memory

Demo teks ini menunjukkan alur kerja end-to-end mekanisme memori dua-proses
(System 1 capture → System 2 konsolidasi → retrieval). Jalankan pada profile
Hermes yang memakai provider `hermes-dual-memory`.

**Durasi**: ±5 menit (termasuk menunggu konsolidasi).
**Prasyarat**: plugin terpasang, provider aktif, `HERMES_DUAL_MEMORY_LLM_MODEL`
ter-set ke model valid.

---

## Langkah 1 — Pemicu capture (System 1)

Mulai percakapan dengan Hermes (CLI atau gateway) dan lakukan percakapan
ringkas dengan fakta yang mudah diverifikasi:

```
Anda: Nama panggilan saya adalah "Echo". Saya sedang membangun aplikasi kasir.
      Buku favorit saya: "Sapiens". Proyek kode saya pakai Python.
```

Hermes merespons (isi bebas). Saat turn selesai, `sync_turn()` menulis turn
tersebut ke `hot_sessions` secara **asinkron** — tidak ada lag yang terasa.

**Verifikasi** — setelah beberapa turn, cek DB capture:

```bash
python3 - <<'EOF'
import sqlite3
conn = sqlite3.connect("$HERMES_HOME/hermes-dual-memory/hot_sessions.sqlite3")
n = conn.execute("SELECT COUNT(*) FROM hot_sessions WHERE consolidated=0").fetchone()[0]
print(f"Pending (belum konsolidasi): {n} rows")
EOF
```

---

## Langkah 2 — Konsolidasi (System 2)

Akhiri sesi dengan `/new` (atau biarkan kompresi terjadi). Ini memicu boundary
`on_session_end` → pending rows dikonsolidasi melalui laporan JSON terstruktur.

**Verifikasi** — tunggu ±1 menit, lalu cek:

```bash
python3 - <<'EOF'
import sqlite3
conn = sqlite3.connect("$HERMES_HOME/hermes-dual-memory/hot_sessions.sqlite3")
rows = conn.execute("""
    SELECT memory_type, status, substr(t_valid,1,19)
    FROM memory_index ORDER BY id DESC LIMIT 5
""").fetchall()
for r in rows:
    print(f"  [{r[1]:<12}] {r[0]:<10} valid sejak {r[2]}")
EOF
```

Diharapkan muncul baris baru bertipe `semantic` (fakta: nama panggilan, proyek,
buku) dengan status `trusted` — atau `quarantined` jika lolos guard keamanan
tetapi gagal semantic review (periksa `flagged_reason`).

---

## Langkah 3 — Retrieval answerability-gated

Mulai sesi **baru** dan tanyakan fakta yang tadi diberikan:

```
Anda: Siapa nama panggilan saya? Buku favorit saya apa?
```

Plugin `prefetch()` menelusuri shadow index + Mem0, melewati threshold
relevansi, lalu **answerability check** — hanya hasil dengan bukti eksplisit
yang disuntikkan ke context. Hermes seharusnya menjawab:

```
Nama panggilan Anda adalah "Echo". Buku favorit Anda: "Sapiens".
```

**Uji abstention** (jawaban jujur saat data tidak ada):

```
Anda: Apa warna favorit saya?
```

Hermes seharusnya **tidak mengarang** — jawaban jujur "tidak tahu" / tidak ada
data, karena tidak ada bukti eksplisit di memori.

---

## Langkah 4 — Supersession (bi-temporal)

Koreksi fakta di sesi baru:

```
Anda: Sebenarnya nama panggilan saya sekarang "Echo-X". Lupakan yang lama.
```

Saat konsolidasi berikutnya, baris lama `Echo` di-set `t_invalid` dan baris baru
`Echo-X` aktif (supersede, bukan hapus). Query "siapa nama panggilan saya"
kembali jawab `Echo-X`.

**Verifikasi**:

```bash
python3 - <<'EOF'
import sqlite3
conn = sqlite3.connect("$HERMES_HOME/hermes-dual-memory/hot_sessions.sqlite3")
rows = conn.execute("""
    SELECT substr(t_valid,1,19), substr(t_invalid,1,19), status
    FROM memory_index WHERE memory_type='semantic'
    ORDER BY id DESC LIMIT 3
""").fetchall()
for r in rows:
    print(f"  valid {r[0]} → invalid {r[1] or '-'}  [{r[2]}]")
EOF
```

---

## Hasil yang Diharapkan

| Langkah | Output |
|---|---|
| 1. Capture | `Pending > 0` setelah percakapan |
| 2. Konsolidasi | Baris baru `trusted` di `memory_index` |
| 3. Retrieval | Jawab benar + abstention jujur |
| 4. Supersession | Baris lama `t_invalid` terisi, query jawab nilai baru |

---

## Catatan Troubleshooting

- **Pending tetap 0 setelah percakapan**: cek `HERMES_DUAL_MEMORY_LLM_MODEL`
  di `.env` — konsolidasi butuh model valid (lihat ADR-0023).
- **Konsolidasi tidak pernah selesai**: cek
  `maintenance_state.last_consolidation_error` di SQLite.
- **Retrieval kosong padahal data ada**: cek apakah chroma ikut ter-backup
  (rollback tanpa chroma = recall hilang, ADR-0024).
- **Semua di-quarantine**: periksa `flagged_reason` — `semantic_unsafe` berarti
  guard keamanan bekerja (bukan bug).
