# ADR-0022: Combo-Safe System-2 Request Budget

**Status**: Diterima
**Tanggal**: 2026-07-30

## Konteks

ADR-0021 membatasi transcript System-2 menjadi 24.000 karakter, tetapi run
legacy default dan research tetap timeout pada chunk pertama, bahkan setelah
satu retry. Model 9router adalah combo dengan fallback, sehingga 24.000
karakter masih melebihi latency budget praktisnya.

## Keputusan

Turunkan batas transcript deterministik menjadi 6.000 karakter per request.
Turn tetap atomic: satu turn lebih besar dari batas dikirim sendirian, tidak
dipotong. Marking tetap per chunk sukses; kegagalan menghentikan run dan semua
row belum sukses tetap pending.

## Alternatif yang Dipertimbangkan

- Menaikkan timeout: ditolak; dua request 24.000 karakter sudah menghabiskan
  deadline dan tidak membuktikan backend dapat menyelesaikan payload besar.
- Memotong isi turn: ditolak; menghilangkan bukti/konteks dan menyulitkan audit.
- Memilih model langsung khusus: ditunda; itu perubahan routing/config lebih
  luas daripada hardening provider ini.

## Konsekuensi

Sesi panjang menghasilkan lebih banyak candidate dan request serial, dengan
latensi total yang mungkin lebih panjang. Namun setiap request combo jauh lebih
kecil, retry tidak mengulang payload besar, dan invariants fail-closed tetap
berlaku.
