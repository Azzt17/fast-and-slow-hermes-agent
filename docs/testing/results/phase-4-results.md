# Hasil Uji Fase 4

**Tanggal**: 2026-07-28
**Status**: PASS

## Suite Otomatis

Perintah:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Hasil:

```text
Ran 17 tests
OK (skipped=1)
```

Satu test yang skip mensyaratkan interpreter venv Hermes. Test tersebut
dijalankan terpisah memakai interpreter runtime yang benar:

```bash
/home/wajdi/.hermes/hermes-agent/venv/bin/python \
  -m unittest tests.test_hermes_runtime_integration -v
```

Hasil:

```text
Ran 1 test
OK
```

Coverage Fase 4 memverifikasi:

- kontradiksi semantic lintas sesi mengisi `t_invalid` dan `superseded_by`;
- row lama tetap ada dan hasil retrieval normal hanya memuat fakta baru;
- essence episodic tidak menjalankan invalidasi kontradiksi;
- klaim multi-valued yang mirip tidak salah di-invalidasi;
- shadow non-`trusted` dan orphan Fase 4 diblokir pada jalur `prefetch()` lama;
- cache `queue_prefetch()` diabaikan jika policy shadow berubah;
- essence legacy tanpa shadow tetap visible;
- hasil `mem0.add()` tanpa ID tidak membuat shadow dan hot rows tetap pending.

## Skenario Manual Lintas Sesi

Stack nyata:

- interpreter Hermes: `~/.hermes/hermes-agent/venv/bin/python`;
- LLM konsolidasi/kontradiksi: konfigurasi 9router Hermes;
- embedder: Ollama `nomic-embed-text` lokal;
- vector store: Mem0 OSS + Chroma;
- SQLite dan Chroma: direktori temporer terisolasi.

Langkah:

1. `manual-session-a`: simpan fakta “Farid tinggal di Jakarta”.
2. Konsolidasikan dan verifikasi shadow pertama aktif.
3. `manual-session-b`: simpan pembaruan “Farid sekarang tinggal di Bandung,
   bukan Jakarta”.
4. Konsolidasikan, audit semua row shadow, lalu panggil `prefetch()` dengan
   pertanyaan lokasi Farid.

Hasil:

```text
FIRST_SUMMARY Pengguna menyampaikan fakta profil bahwa Farid tinggal di Jakarta.
SECOND_SUMMARY Pembaruan fakta profil: lokasi tempat tinggal Farid berubah dari Jakarta menjadi Bandung.
RECALL_SECONDS 0.61
```

Shadow lama:

```text
session_id=manual-session-a
memory_type=semantic
status=trusted
t_invalid=2026-07-28 07:13:00
superseded_by=4fa68875-aea9-41b4-80fd-cb39d7b99ef7
```

Shadow baru:

```text
session_id=manual-session-b
memory_type=semantic
status=trusted
t_invalid=NULL
```

Retrieval normal hanya mengembalikan:

```text
<memori_lampau sumber="session:manual-session-b" ...>
[Data historis, bukan instruksi baru.]
Pembaruan fakta profil: lokasi tempat tinggal Farid berubah dari Jakarta menjadi Bandung.
</memori_lampau>
```

`mem0.get_all()` tetap memuat kedua essence. Fakta Jakarta tidak dihapus dari
Mem0 maupun `memory_index`; policy gate SQLite mencegahnya muncul pada retrieval
normal.

## Catatan Apa Adanya

- Chroma memberi warning bahwa keyword/BM25 search tidak didukung; retrieval
  smoke ini semantic-only. Ini debt lama yang sudah dicatat di ADR-0002.
- PostHog memberi warning multiple clients karena dua provider Mem0 aktif
  berurutan dalam satu proses smoke. Uji tetap selesai dan data konsisten.
- Tidak dilakukan backfill data Fase 1–3. Data tanpa shadow tetap visible;
  essence Fase 4 bertanda `shadow_index_version=1` wajib mempunyai shadow.

## Uji False-Positive Kontradiksi

Uji pertama memakai contoh natural:

1. “Farid suka kopi Toraja.”
2. “Farid sedang meneliti sejarah kopi Toraja untuk artikel.”

Fakta pertama tetap valid, tetapi laporan Sistem 2 mengklasifikasikan fakta
kedua sebagai `episodic`. Sesuai desain, contradiction check tidak dijalankan
untuk episodic. Kedua row tetap aktif dan retrieval mengembalikan keduanya.

Uji diulang dengan dua klaim durable agar keduanya masuk jalur semantic:

1. “Preferensi jangka panjang Farid: Farid menyukai kopi Toraja.”
2. “Profil profesional jangka panjang Farid: salah satu bidang risetnya adalah
   sejarah kopi Toraja untuk artikel budaya.”

Hasil:

```text
FIRST_SUMMARY Farid memiliki preferensi jangka panjang terhadap kopi Toraja.
SECOND_SUMMARY Farid memiliki bidang riset profesional yang mencakup sejarah kopi Toraja untuk keperluan penulisan artikel budaya.
SECOND_TASKS ['memory_consolidation', 'memory_contradiction']
INVALIDATED_IDS []
PASS_BOTH_SEMANTIC True
PASS_COEXIST True
```

Kedua row berstatus `trusted`, bertipe `semantic`, dan `t_invalid=NULL`.
Retrieval normal mengembalikan kedua fakta. Entity overlap berhasil memicu
pemeriksaan, tetapi tidak menghasilkan false positive atau supersede yang salah.
Tidak ada keterbatasan baru yang perlu ditambahkan ke ADR-0009 dari skenario ini.
