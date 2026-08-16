# ADR-0021: Bounded System-2 Consolidation for Router Combos

**Status**: Diterima
**Tanggal**: 2026-07-30

## Konteks

Model `asa-complex` di 9router adalah combo dengan fallback. Satu request
System-2 mengirim seluruh hot transcript; sesi nyata 104 turn (110.832 karakter)
timeout dua kali dan tetap fail-closed. Timeout lebih besar saja tidak membatasi
latensi maupun ukuran request.

## Keputusan

Pecah hot turns berurutan menjadi batch whole-turn deterministik maksimal 24.000
karakter transcript. Konsolidasikan tiap batch secara independen. Tandai hanya
row batch yang berhasil setelah admission dan write lengkap; saat satu batch
gagal, hentikan run dan biarkan batch itu serta sisanya pending untuk trigger
berikutnya.

## Alternatif yang Dipertimbangkan

- Menaikkan timeout global: ditolak; fallback tetap dapat melebihi deadline.
- Mengirim ulang payload penuh: ditolak; retry identik memperbesar beban.
- Memotong di tengah turn: ditolak; mengubah bukti dan konteks secara ambigu.

## Konsekuensi

Request combo lebih bounded dan retry tidak mengulang sesi panjang penuh.
Satu sesi panjang dapat menghasilkan beberapa memory candidate/trusted yang
masing-masing berasal dari batch kronologis. Kegagalan tetap fail-closed dan
tidak menandai row yang belum sukses.
