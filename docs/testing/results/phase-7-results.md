# Hasil Uji Fase 7

**Tanggal**: 2026-07-28
**Status**: PASS

## Audit Kondisi Awal

Sejak Fase 2, `new_skills` divalidasi sebagai list `{title, detail}`, tetapi
hanya diserialisasi sebagai JSON di metadata Mem0. Tidak ada routing ke Skills,
draft store, approval, atau conversion. Audit runtime sebelum implementasi hanya
menemukan laporan historis dengan `new_skills=[]`.

Source Hermes `v0.19.0` terpasang diverifikasi langsung:

- skill aktif ditemukan rekursif di `${HERMES_HOME}/skills/**/SKILL.md` dan
  `skills.external_dirs`;
- frontmatter wajib `name` dan `description`, body wajib non-empty;
- nama maksimal 64 karakter;
- create-path membatasi description menjadi 60 karakter;
- `tools.skill_manager_tool.skill_manage(action="create")` menyediakan validasi,
  atomic write, security scan, dan cache invalidation;
- `tools.skill_usage.mark_agent_created()` memasukkan skill ke lifecycle Curator.

## Suite Otomatis

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 42 tests
OK (skipped=2)

Hermes runtime integration:
Ran 2 tests
OK
```

Coverage Fase 7 memverifikasi `new_skills` non-empty dari report complex,
draft tidak membuat active skills tree, raw procedure tidak disimpan sebagai
metadata Mem0, output lolos validator/frontmatter native Hermes, redundancy
blocking, explicit approval, Curator marker, quarantine gate, dan compact retry
prompt setelah output konsolidasi malformed. Batas jumlah/panjang skill serta
tampered draft path juga ditolak sebelum writer native dipanggil.
Failure injection shadow finalization meninggalkan draft internal berstatus
`candidate`; candidate tersebut tidak dapat di-approve.

## Skenario Hermes Nyata

Sesi Hermes asli:

```text
Session: 20260728_211350_950e7b
Messages: 20 (1 user, 18 tool calls)
```

Tugas melakukan audit read-only Fase 7 melalui pengecekan Git, arsitektur,
consolidation routing, procedural workflow, CLI, dan test procedural. Hermes
menyelesaikan **18 tool call**, melebihi kriteria minimal lima. Jawaban akhirnya
mengandung prosedur reusable berjudul `Audit procedural memory release
readiness`.

Catatan apa adanya: meski diminta read-only, Hermes menjalankan `pip install
pytest --quiet` setelah command pytest pertamanya salah. Install tersebut masuk
ke `.venv` proyek; tidak mengubah tracked files.

## Konsolidasi Real Stack

One-shot Hermes **memanggil** `on_session_end()` secara natural saat cleanup.
Log sesi menunjukkan `CLI cleanup calling memory shutdown` pada 21:16:04 dan
attempt konsolidasi mulai sesudahnya. Namun hook provider memang asynchronous:
`shutdown()` hanya menunggu worker konsolidasi selama 10 detik, sedangkan dua
attempt LLM dengan timeout awal 8 detik dapat melewati window tersebut. Pada
sesi ini attempt pertama timeout pada 21:16:12 dan proses one-shot keluar ketika
retry masih berjalan, sehingga hot rows tetap pending. Hook resmi
`on_pre_compress()` kemudian dipicu sinkron lewat loader memory provider Hermes
pada session yang sama.

Ini adalah keterbatasan metodologi one-shot/cleanup completion window, bukan
hook yang tidak terpanggil dan bukan regresi dari routing skill Fase 7. Method
`on_session_end()` tidak diubah oleh Fase 7; `route_new_skills()` baru berjalan
di dalam pipeline setelah `_consolidate()` sudah dipicu dan report lolos
admission.

Percobaan real-stack:

1. Default timeout awal 8 detik: dua attempt timeout; hot rows tetap pending.
2. Timeout 60 detik sebelum hardening: dua response JSON malformed/terpotong;
   hot rows tetap pending.
3. Setelah prompt membatasi maksimum tiga skill/detail 1200 karakter dan retry
   meminta JSON ringkas: consolidation + admission + Mem0 write sukses.

Hasil akhir:

```text
hot rows: 2/2 consolidated
shadow status: trusted
memory_type: episodic
new_skills: 1
skill draft id: 17120d019a9ae75d
status sebelum approval: pending
active SKILL.md sebelum approval: tidak ada
```

Draft berasal dari model konsolidasi nyata, bukan report mock. Raw `new_skills`
tidak lagi disimpan sebagai prosa metadata Mem0; metadata hanya mencatat jumlah
serta draft IDs.

## Approval dan Hermes Skills

Approval eksplisit:

```text
hermes hermes-dual-memory skills approve 17120d019a9ae75d
Approved 17120d019a9ae75d ->
/home/wajdi/.hermes/skills/procedural-memory/
audit-procedural-memory-release-readiness/SKILL.md
```

Verifikasi native:

```text
skills_list match: 1
skill_view success: true
category: procedural-memory
created_by: agent
is_curation_eligible: true
is_agent_created: true
```

Percobaan tambahan `hermes security scan <path>` gagal karena versi CLI ini
hanya memiliki `hermes security audit`. Ini bukan kegagalan create: native
`skill_manage(create)` sudah menjalankan security scanner internal dan hanya
mengembalikan sukses setelah file lolos.

## Curator

```text
hermes curator run --dry-run --sync
preview candidates: 69
errors: 0

hermes curator run --sync
auto: checked=69 stale=0 archived=0 reactivated=0
errors: 0
```

`hermes curator status` menampilkan
`audit-procedural-memory-release-readiness` sebagai agent-created active skill.
LLM consolidation Curator tidak dijalankan karena konfigurasi
`curator.consolidate` memang off; deterministic lifecycle pass mengenali skill
baru tanpa error, memenuhi kriteria fase tanpa mengubah kebijakan user.

Sesudah skill aktif, report identik diroute sekali lagi untuk verifikasi
redundansi runtime. Draft baru berstatus `redundant`, match skill aktif mendapat
score `1.0`, dan approval ditolak dengan `redundant draft cannot be approved`.

## Kesimpulan

Seluruh kriteria keluar Fase 7 PASS. Draft tetap non-active sampai approval,
redundancy diblokir, final file dibuat melalui API native Hermes, dan Curator
mengambil alih lifecycle. Timeout/malformed output real-stack tetap fail-safe;
hardening retry diperlukan agar sesi panjang berhasil dikonsolidasi.
Default timeout configured consolidation dinaikkan menjadi 30 detik; tetap
bounded dan dapat dioverride melalui `HERMES_DUAL_MEMORY_LLM_TIMEOUT`.
