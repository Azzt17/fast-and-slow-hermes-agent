# Hasil Uji Fase 1

## Unit Test Storage

Perintah:

```bash
python3 -m unittest tests.test_storage
```

Hasil:

```text
.
----------------------------------------------------------------------
Ran 1 test in 0.032s

OK
```

Makna: insert ke `hot_sessions` berhasil, baris bisa di-query balik, dan jumlah pending row sesuai ekspektasi.

## Tes Integrasi Manual (Hermes CLI)

Status aktivasi Hermes CLI:

```text
Memory status
────────────────────────────────────────
  Built-in (MEMORY.md / USER.md):
    Memory injection:   enabled ✓
    User profile:       enabled ✓
    Memory tool:        enabled ✓
  Provider:  hermes-dual-memory

  Plugin:    installed ✓
  Status:    available ✓

  Installed plugins:
    • hermes-dual-memory  (no setup needed) ← active
```

Discovery plugin user-space:

```text
86:not enabled  user     0.0.0    hermes-dual-memory
```

Catatan: `hermes memory status` adalah indikator aktivasi runtime yang relevan; entri di `plugins list` menunjukkan paket user-space terpasang.

Bukti row hot tier yang terisi:

```text
rows_after_write=[('user', 'user turn for phase-1 docs'), ('assistant', 'assistant turn for phase-1 docs')]
```

## Tes Persistensi (Restart)

Simulasi restart provider pada `hermes_home` yang sama:

```text
pending_before_restart=2
rows_after_restart=2
persisted_db=/tmp/hermes-phase1-o1nog3w_/hermes_home/hermes-dual-memory/hot_sessions.sqlite3
restarted_rows=[('user', 'user turn for phase-1 docs'), ('assistant', 'assistant turn for phase-1 docs')]
```

Makna: data tetap ada setelah provider diinisialisasi ulang terhadap home directory yang sama.

## Tes Non-Blocking

Pengukuran `sync_turn()` tanpa delay buatan:

```text
sync_turn_return_seconds=0.007859
```

Makna: panggilan balik hampir instan, sementara penulisan baris terjadi di background thread dan selesai setelahnya. Ini memenuhi kontrak non-blocking untuk jalur write.
