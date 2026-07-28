# ADR-0012: Draft terpisah dan promosi skill melalui API native Hermes

**Status**: Diterima
**Tanggal**: 2026-07-28

## Konteks

Laporan konsolidasi sejak Fase 2 memvalidasi `new_skills`, tetapi nilainya hanya
diserialisasi ke metadata Mem0. Menulis setiap usulan langsung ke
`~/.hermes/skills/` akan membuat prosedur yang belum ditinjau langsung aktif dan
terlihat oleh agent. Fase 7 juga harus menghindari duplikasi skill serta
menyerahkan staleness, konsolidasi, dan arsip kepada Curator bawaan Hermes.

Hermes menyediakan `tools.skill_manager_tool.skill_manage(action="create")`.
Jalur ini memvalidasi nama/frontmatter/body, membatasi deskripsi skill baru pada
budget prompt 60 karakter, menulis `SKILL.md` secara atomik, menjalankan security
scan, dan menginvalidasi cache skill. Curator hanya mengelola skill dengan usage
record `created_by="agent"`, yang dapat ditetapkan melalui
`tools.skill_usage.mark_agent_created()`.

## Keputusan

Hanya laporan konsolidasi berstatus `trusted` yang boleh meroute `new_skills`.
Setiap item dinormalisasi menjadi nama lowercase-hyphen, deskripsi singkat, dan
body instruksi. Plugin menyimpan usulan sebagai JSON atomik di
`~/.hermes/hermes-dual-memory/skill-drafts/`, di luar pohon `skills/`, sehingga
draft tidak dapat ditemukan loader Hermes.

Draft mula-mula berstatus internal `candidate`. Hanya setelah shadow memory
berhasil difinalisasi sebagai `trusted`, draft berubah menjadi `pending` atau
`redundant`. Kegagalan finalisasi memory meninggalkan candidate yang tidak dapat
di-approve.

Sebelum draft ditulis, plugin membandingkan gabungan nama, deskripsi, dan body
terhadap skill aktif Hermes, termasuk `skills.external_dirs`. Similarity memakai
token Jaccard dan `SequenceMatcher`; exact/near match di atas ambang konservatif
dicatat sebagai draft berstatus `redundant` dengan daftar match, bukan sebagai
draft yang dapat dipromosikan.

Approval dilakukan eksplisit melalui CLI:

```text
hermes hermes-dual-memory skills list
hermes hermes-dual-memory skills approve <draft-id>
```

Promosi memanggil `skill_manage(action="create")`, bukan menulis langsung. Jika
berhasil, plugin memanggil `mark_agent_created()`, memverifikasi file final, lalu
mengubah draft menjadi `approved` dengan path final. Draft tidak dihapus agar
audit trail tetap tersedia. Approval bersifat idempotent; draft redundant tidak
dapat dipromosikan.

Plugin tidak membuat scheduler, staleness state, consolidation, atau archive
skill sendiri. Semua lifecycle setelah promosi dimiliki Curator Hermes.

## Alternatif yang Dipertimbangkan

- Menulis `SKILL.md` aktif saat konsolidasi: ditolak karena tidak ada human gate.
- Menaruh draft di bawah `~/.hermes/skills/`: ditolak karena recursive loader
  dapat menganggapnya aktif.
- Menulis final file sendiri: ditolak karena membypass validator, security scan,
  atomic write, dan cache invalidation Hermes.
- Menyimpan lifecycle draft di SQLite: ditolak karena file JSON atomik lebih
  mudah diaudit dan tidak mengubah skema data fase sebelumnya.
- Membangun Curator sendiri: ditolak karena menduplikasi Hermes.

## Konsekuensi

Procedural memory tidak aktif tanpa tindakan manusia. Usulan redundan tetap
terlihat untuk audit tetapi tidak mencemari daftar skill aktif. Promosi bergantung
pada source/runtime Hermes yang menyediakan API Skills; jika API tidak tersedia
atau menolak konten, draft tetap pending dan tidak ada file aktif parsial.
