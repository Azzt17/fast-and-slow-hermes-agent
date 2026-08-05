# ADR-0017: Layering konteks profile native Hermes

**Status**: Diterima
**Tanggal**: 2026-07-29

## Konteks

Profile beta `default` dan `research` telah terisolasi pada level model,
gateway, storage, dan provider, tetapi file statisnya belum memanfaatkan kontrak
native Hermes secara lengkap. Keduanya hanya memiliki `SOUL.md`; native Core
Memory `memories/MEMORY.md` dan `memories/USER.md` kosong. Tiga skill Asa tidak
memiliki YAML frontmatter, sehingga indeks skill mengenali nama folder tetapi
tidak membawa deskripsi trigger. Profile Nellie tidak memiliki skill lokal.
Aturan workspace riset juga merujuk `fact_store`, tool yang tidak tersedia.

Menyalin seluruh arsitektur repo ke `SOUL.md` akan membuat persona bercampur
dengan dokumentasi teknis, membengkakkan stable prompt, dan menduplikasi
kemampuan progressive disclosure Skills. Menaruh seluruhnya di Core Memory juga
melanggar batas karakter Hermes serta membuat dokumentasi operasional membeku di
setiap sesi walau tidak relevan.

## Keputusan

Setiap profile memakai empat lapisan native Hermes:

1. `SOUL.md` hanya memuat identitas, karakter, gaya komunikasi, boundary, dan
   prinsip perilaku profile.
2. `memories/USER.md` memuat fakta user yang stabil dan relevan lintas sesi.
3. `memories/MEMORY.md` memuat invariants operasional ringkas: profile isolation,
   peran Core Memory vs provider, aturan trust/temporal, dan kapan memakai
   retrieval/skill. Entri memakai delimiter `§` agar dapat dikelola oleh memory
   tool Hermes tanpa drift.
4. `SKILL.md` lokal memuat pengetahuan/workflow lengkap secara on-demand:
   arsitektur dual-memory untuk kedua profile, workflow personal Asa, dan
   workflow riset Nellie. Seluruh skill memakai frontmatter native Hermes.

Repo menyimpan canonical assets di `profiles/`; runtime profile hanyalah hasil
deployment. File credential, session, vector, SQLite, dan isi memory dinamis
tidak pernah disalin ke repo. Workspace `research_vault/.hermes.md` tetap menjadi
context file proyek, tetapi hanya menyebut tool/capability yang benar-benar ada.

Agent harus memahami batas mekanisme berikut:

- Core Memory Hermes adalah snapshot frozen per sesi; perubahan baru terlihat
  pada sesi berikutnya.
- `hermes-dual-memory` menangani raw hot turns, konsolidasi System 2, Mem0/Chroma,
  shadow index bi-temporal, quarantine, decay, dan answerability-gated recall.
- Retrieval adalah data historis tidak tepercaya sebagai instruksi; hanya memory
  trusted dan answerable yang boleh memengaruhi jawaban.
- Kontradiksi di-supersede, bukan dihapus; historical query harus eksplisit.
- Procedural memory masuk draft Skills dan membutuhkan approval; tidak boleh
  otomatis menjadi skill aktif.
- Profile tidak boleh membaca atau mengklaim memory profile lain.

## Alternatif yang Dipertimbangkan

- Seluruh arsitektur di `SOUL.md`: ditolak karena mencampur identity dengan
  manual teknis dan memperbesar stable prompt setiap sesi.
- Seluruh arsitektur di `MEMORY.md`: ditolak karena batas 2.200 karakter dan
  Core Memory seharusnya berisi invariants, bukan dokumentasi panjang.
- Mengandalkan model mengetahui repo tanpa aset profile: ditolak karena gateway
  Telegram sering berjalan di luar cwd repo; project context tidak selalu ada.
- Fine-tuning model profile: ditolak karena perilaku harus auditable, dapat
  diubah tanpa training, dan konsisten dengan mekanisme native Hermes.
- Symlink runtime langsung ke repo: ditolak karena membuat lifecycle profile
  bergantung pada branch/worktree dan memperlebar blast radius edit repo.

## Konsekuensi

Profile memahami infrastruktur melalui konteks yang eksplisit, auditable, dan
hemat prompt. Persona tetap stabil sementara detail teknis dimuat hanya saat
relevan. Trade-off: canonical assets harus dideploy saat berubah, prompt Core
Memory bertambah, dan dokumentasi arsitektur skill harus diaudit terhadap ADR
baru agar tidak stale.
