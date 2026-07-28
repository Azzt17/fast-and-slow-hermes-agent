# ADR-0011: Admission semantik fail-closed dan reuse pola Hermes

**Status**: Diterima
**Tanggal**: 2026-07-28

## Konteks

Fase 4 membuat row `candidate`, tetapi langsung mengubahnya menjadi `trusted`
dalam transaksi yang sama. Tidak ada keputusan keamanan sungguhan. Fase 6
membutuhkan dua lapis admission sebelum memory boleh muncul pada retrieval.
Source Hermes terpasang menyediakan `tools/threat_patterns.py` dengan
`scan_for_threats(content, scope="strict")`, termasuk pola injection,
exfiltration, persistence, dan invisible Unicode.

Lapisan semantik bergantung pada model eksternal dan dapat timeout/gagal. Sistem
harus memilih apakah hasil yang belum diperiksa boleh trusted.

## Keputusan

Admission memakai dua lapis berurutan:

1. Pattern scan cepat memakai `tools.threat_patterns.scan_for_threats()` scope
   `strict` jika modul Hermes tersedia. Untuk test/development standalone,
   plugin menyediakan fallback subset yang konservatif dengan pattern ID
   kompatibel untuk kategori inti.
2. Jika pattern scan bersih, model terpisah menilai apakah essence mencoba
   memberi instruksi kepada agent, mengubah perilaku/identitas, meminta rahasia,
   atau menyamarkan instruksi sebagai fakta. Output wajib JSON boolean
   `safe` beserta `reason`.

Kegagalan/timeout/format invalid pada lapis semantik bersifat **fail-closed**:
entry menjadi `quarantined` dengan `flagged_reason=semantic_unavailable:*`.
Pattern hit juga menjadi `quarantined`. Hanya keputusan semantik eksplisit
`safe=true` yang memindahkan `candidate → trusted`.

Essence tetap ditulis ke Mem0 sebelum shadow dibuat karena `mem0_id` diperlukan
sebagai foreign key policy. Metadata Mem0 memakai status admission final dan
`shadow_index_version=1`; retrieval Fase 4 tetap satu-satunya policy gate dan
memblokir shadow non-trusted. Orphan bertanda Fase 4/6 tanpa shadow tetap
fail-closed seperti ADR-0009.

## Alternatif yang Dipertimbangkan

- Semantic failure tetap trusted dengan flag: ditolak karena unchecked memory
  dapat masuk system context dan melanggar quarantine-before-trust.
- Pattern-only: ditolak karena framing halus seperti “kamu berkewajiban untuk”
  sengaja berada di luar pola Hermes guna menghindari false positive umum.
- Menyalin seluruh `threat_patterns.py`: ditolak karena membuat fork pola Hermes
  yang cepat basi; fallback hanya untuk environment tanpa source Hermes.
- Membuat filter retrieval baru: ditolak karena Fase 4 sudah memusatkan policy
  pada status shadow.

## Konsekuensi

Kegagalan provider semantik mengurangi availability memory baru, tetapi tidak
mengorbankan keselamatan context. False positive dapat diaudit melalui
`flagged_reason` dan benchmark korpus. Mem0 mungkin menyimpan essence
quarantined, namun retrieval normal tetap memblokirnya melalui SQLite.
