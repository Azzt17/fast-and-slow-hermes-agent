# ADR-0015: Gate answerability untuk seluruh kandidat scored

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Baseline Fase 8 mencapai recall `100%`, tetapi abstention hanya `50%`. Query
tanpa jawaban tentang konstelasi masih menerima neighbor kopi Toraja dengan
score `0.598476`, sementara fakta valid terlemah berada pada rentang
`0.567921–0.595779`. Satu threshold global tidak dapat menolak false neighbor
tersebut tanpa membuang fakta valid.

Audit reuse menemukan reranking Mem0 resmi hanya tersedia pada mode Platform.
Provider ini memakai Mem0 OSS agar storage tetap lokal dan ekstraksi otomatis
tetap dapat dimatikan. Reranker Jaccard plugin Holographic milik Hermes hanya
mengukur overlap token, bukan apakah kandidat memberi bukti langsung untuk
menjawab query.

Pre-gate run pada 30 hard-negative mengoreksi asumsi awal bahwa score tinggi
dapat diterima langsung: 29 query menghasilkan context, dengan false neighbor
hingga `0.846105`. Karena score adalah kedekatan embedding dan bukan ukuran
answerability, tidak ada zona high-confidence yang aman pada corpus ini.

## Keputusan

Retrieval memakai dua tahap setelah shadow policy:

1. kandidat scored `<0.55` ditolak langsung;
2. seluruh kandidat scored `>=0.55` diverifikasi oleh satu panggilan model
   bounded per query.

Verifier menilai setiap kandidat secara independen dalam satu batch. Kandidat
hanya diterima jika teksnya memberi bukti langsung untuk menjawab seluruh atau
sebagian komponen query; kesamaan orang, proyek, atau topik saja tidak cukup.
Output wajib JSON boolean per candidate ID. Format invalid boleh dicoba ulang
tepat satu kali di dalam total timeout yang sama; missing decision setelah retry,
exception, verifier tidak tersedia, atau timeout bersifat fail-closed. Kandidat
tanpa score tetap mengikuti compatibility path legacy dan tidak dipaksa melalui
verifier.

Shadow policy dijalankan sebelum verifier. Candidate, quarantined, orphan
bertanda shadow, current-state-invalid, dan invalid episodic tidak pernah
dikirim ke verifier. Mode historis ADR-0014 tetap boleh memberikan superseded
semantic trusted sebagai kandidat.

Low threshold dan timeout dapat dioverride melalui environment untuk operasi
dan eksperimen. Nilai default hanya boleh diubah setelah benchmark
real-stack menunjukkan recall/security tidak turun. Benchmark juga harus
mencatat jumlah call, latency, dan token verifier secara terpisah dari token
context yang diinjeksi.

## Alternatif yang Dipertimbangkan

- Menaikkan threshold global ke `0.60`: ditolak karena membuang expected facts
  dengan score di bawah `0.60`.
- Memakai rerank Mem0 Platform: ditolak karena tidak tersedia pada Mem0 OSS dan
  mengubah deployment/storage contract proyek.
- Reuse Jaccard Holographic: ditolak karena lexical overlap bukan direct
  answerability dan akan lemah pada paraphrase.
- Menerima kandidat score tinggi tanpa verifier: ditolak setelah pre-gate run
  menemukan hard-negative score `0.846105`; embedding similarity bukan bukti
  bahwa kandidat menjawab atribut yang ditanyakan.
- Satu keputusan untuk seluruh result set: ditolak karena query agregasi dapat
  memiliki beberapa kandidat relevan dan irrelevant secara bersamaan.

## Konsekuensi

False semantic neighbor dapat ditolak tanpa menaikkan threshold global. Biaya
model muncul pada query yang memiliki minimal satu kandidat scored di atas
threshold; seluruh kandidat query tersebut dinilai dalam satu batch.
Trade-off: kegagalan verifier dapat mengurangi recall kandidat ambigu; pilihan
ini disengaja karena tidak menyuntikkan memory opsional lebih aman daripada
memberi konteks yang tidak terverifikasi. Corpus abstention wajib diperbesar
menjadi minimal 30 query hard-negative sebelum baseline dipromosikan.
