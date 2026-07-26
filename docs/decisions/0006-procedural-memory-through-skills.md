# ADR-0006: Procedural memory melalui Skills system Hermes

**Status**: Diterima
**Tanggal**: 2026-07-26

## Konteks

Essence procedural yang tervalidasi perlu memiliki lifecycle, deteksi staleness, konsolidasi, dan arsip. Hermes sudah menyediakan Skills system dan Curator untuk kebutuhan tersebut.

## Keputusan

Mengonversi atau mengusulkan procedural memory sebagai file `SKILL.md` yang kompatibel dengan `agentskills.io`, bukan menyimpannya sebagai prosa bebas di Mem0.

## Alternatif yang Dipertimbangkan

- Menyimpan procedural memory sebagai teks di Mem0: tidak dipilih karena tidak memperoleh lifecycle skill Hermes.
- Membangun lifecycle procedural memory baru: tidak dipilih karena menduplikasi kemampuan Curator.

## Konsekuensi

Procedural memory memakai siklus hidup Skills/Curator yang sudah ada. Trade-off-nya, kualitas dan granularitas skill perlu divalidasi dengan hati-hati, termasuk kemungkinan dry-run atau review sebelum aktivasi.
