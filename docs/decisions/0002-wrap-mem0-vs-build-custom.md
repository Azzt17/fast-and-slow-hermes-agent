# ADR-0002: Membungkus Mem0 OSS in-process, bukan membangun retrieval dari nol

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Plugin membutuhkan penyimpanan essence dan retrieval lintas sesi, sementara proyek juga memerlukan kontrol sendiri atas bi-temporal facts, tiering, decay, dan quarantine.

## Keputusan

Memakai `mem0ai` dalam mode OSS in-process sebagai storage dan mesin retrieval, dengan backend vektor lokal yang diverifikasi pada Fase 0. SQLite `memory_index` menjadi shadow index untuk metadata dan kebijakan yang tidak disediakan Mem0.

## Alternatif yang Dipertimbangkan

- Membangun vector, BM25, dan entity retrieval sendiri: tidak dipilih karena memerlukan pembangunan ulang kemampuan retrieval yang sudah teruji.
- Menyimpan seluruh state hanya di Mem0: tidak dipilih karena Mem0 tidak menyediakan bi-temporal tracking, retrievability decay, dan quarantine sesuai rancangan.

## Konsekuensi

Kita memperoleh fusion retrieval Mem0 tanpa mengorbankan kontrol kebijakan di SQLite. Trade-off-nya adalah dua sistem penyimpanan yang harus dijaga konsistensinya melalui `mem0_id`.

## Tindak Lanjut

Backend Chroma yang digunakan pada Fase 0–2 tidak mendukung pencarian keyword
BM25, sehingga retrieval hybrid saat ini memakai semantic similarity saja.
Evaluasi Qdrant dijadikan tindak lanjut sebelum memilih backend pengganti;
perubahan backend harus mempertahankan Mem0 sebagai mesin retrieval dan SQLite
sebagai shadow index.

Catatan ini menyerap hasil eksperimen Fase 2 yang sebelumnya tersimpan pada
`0001-architectural-decisions.md`; file eksperimen tersebut bukan ADR terpisah.
