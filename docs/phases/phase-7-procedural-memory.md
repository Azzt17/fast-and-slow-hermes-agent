# Fase 7: Procedural Memory via Skills System

**Status**: Selesai
**Tanggal Mulai**: 2026-07-28
**Tanggal Selesai**: 2026-07-28

## Goal

Meroute `new_skills` tervalidasi menjadi draft yang memerlukan approval manusia,
lalu mempromosikannya sebagai `SKILL.md` valid yang dikelola Curator Hermes.

## Yang Dibangun

- [x] Audit historis `new_skills` dan format Skills Hermes
- [x] Draft store di luar pohon skill aktif
- [x] Deteksi kemiripan terhadap skill existing
- [x] CLI list/show/approve untuk approval eksplisit
- [x] Promosi melalui validator/security writer native Hermes
- [x] Provenance agent-created untuk lifecycle Curator
- [x] Test unit, integrasi runtime, dan skenario nyata ≥5 tool call

## Failure Mode yang Diwaspadai

- Draft terbaca sebagai skill aktif sebelum approval
- Skill granular atau redundant lolos menjadi aktif
- Konten final tidak memenuhi parser/validator Hermes
- Skill aktif tidak ditandai agent-created sehingga diabaikan Curator
- Kegagalan promosi meninggalkan direktori skill parsial

## Kriteria Keluar (Exit Criteria)

- [x] Skenario tugas kompleks nyata menghasilkan `new_skills` non-empty
- [x] Draft tidak muncul di loader Skills sebelum approval
- [x] Approval menghasilkan `SKILL.md` valid di `~/.hermes/skills/`
- [x] Redundansi terdeteksi dan diblokir dari promosi
- [x] Curator mendeteksi skill baru tanpa error

## Hasil Uji

PASS. Suite regression menjalankan 42 test (`2 skipped`); runtime Hermes
menjalankan 2 test native. Sesi `20260728_211350_950e7b` menyelesaikan 18 tool
call, menghasilkan draft nyata `17120d019a9ae75d`, lalu approval native membuat
skill aktif. Curator deterministic pass memeriksa 69 skill tanpa error. Bukti
lengkap: `docs/testing/results/phase-7-results.md`.

## Catatan/Pembelajaran

Audit awal menemukan runtime historis hanya menghasilkan `new_skills=[]`.
Sebelum Fase 7, field tersebut divalidasi lalu diserialisasi ke metadata Mem0;
tidak ada routing procedural atau draft.

Sesi real-stack mengungkap timeout default dan JSON panjang malformed; kedua
kegagalan membiarkan hot rows pending. Prompt/output budget serta compact retry
ditambahkan sebelum skenario akhirnya PASS.

Catatan metodologi: one-shot CLI Hermes tetap memanggil `on_session_end()` pada
cleanup. Konsolidasi awal tidak selesai karena hook provider daemonized dan
`shutdown()` hanya memberi join window 10 detik, sementara retry LLM dapat
berjalan lebih lama. Jadi ini bukan gangguan trigger oleh fitur skill; validasi
E2E dilanjutkan dengan hook sinkron `on_pre_compress()` pada session yang sama.
