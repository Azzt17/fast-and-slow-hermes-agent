# ADR-0005: Sistem 2 mengekstrak fakta, bukan ekstraksi otomatis Mem0

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Rancangan memerlukan laporan konsolidasi dengan format terstruktur untuk summary, skill, entity, relation, tipe memori, dan importance score. Mesin ekstraksi otomatis Mem0 dapat mengolah input dengan perilaku default yang tidak mengikuti format ini.

## Keputusan

Sistem 2 milik plugin menghasilkan dan memvalidasi laporan konsolidasi JSON. Yang dikirim ke `mem0.add()` adalah essence hasil proses tersebut; ekstraksi LLM otomatis Mem0 dinonaktifkan atau tidak diandalkan.

## Alternatif yang Dipertimbangkan

- Mengirim raw conversation ke ekstraksi otomatis Mem0: tidak dipilih karena hasilnya tidak terikat pada skema konsolidasi proyek.
- Menjalankan kedua mekanisme paralel: tidak dipilih karena menimbulkan duplikasi dan konflik dalam fakta yang tersimpan.

## Konsekuensi

Format data dan proses admission dapat dikendalikan sepenuhnya oleh plugin. Trade-off-nya, pipeline Sistem 2 harus menangani prompt, parsing JSON, validasi, dan fallback sendiri.
