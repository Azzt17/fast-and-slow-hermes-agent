# Beta Preflight & Rollback Runbook

Runbook ini pertama kali dieksekusi pada `2026-07-29`; hasil aktual ada di
`CURRENT.md`, `SNAPSHOT-MANIFEST.md`, dan `journal.md`. Perintah di bawah tetap
menjadi referensi untuk profile default `$HERMES_HOME=~/.hermes`. Eksekusi awal
juga memasukkan profile `research` sebagai profile terisolasi kedua.

## 1. Pre-check

```bash
git switch master
git pull --ff-only origin master
git rev-parse HEAD
git rev-list -n1 v0.1.0-beta.1
hermes config get memory.provider
hermes gateway status
sqlite3 ~/.hermes/hermes-dual-memory/hot_sessions.sqlite3 'PRAGMA integrity_check;'
sqlite3 ~/.hermes/hermes-dual-memory/history.db 'PRAGMA integrity_check;'
```

Expected code checkpoint: `18c770bfdd0099cacc647de1f88259b8be8f9128`.

## 2. Maintenance Window

Beritahu channel aktif bahwa gateway akan restart. Pastikan tidak ada task yang
sedang diproses. Profile `research` berjalan terpisah dan kini masuk scope beta;
stop, snapshot, deploy, dan restart profile itu secara terkontrol bersama default.

```bash
systemctl --user stop hermes-gateway.service hermes-gateway-nellie.service
systemctl --user is-active hermes-gateway.service
systemctl --user is-active hermes-gateway-nellie.service
```

Lanjut hanya bila seluruh gateway profile yang masuk scope benar-benar berhenti.

## 3. Snapshot Pre-Beta

Gunakan lokasi privat di luar repo:

```bash
stamp=$(date +%Y%m%dT%H%M%S%z)
snapshot_root="$HOME/hermes-beta-snapshots/v0.1.0-beta.1-$stamp"
mkdir -p "$snapshot_root"

hermes backup -o "$snapshot_root/hermes-full.zip"
tar --create --gzip \
  --file "$snapshot_root/hermes-dual-memory.tar.gz" \
  --directory "$HOME/.hermes" \
  hermes-dual-memory plugins/hermes-dual-memory
tar --create --gzip \
  --file "$snapshot_root/research-profile.tar.gz" \
  --directory "$HOME/.hermes/profiles" \
  research

sha256sum \
  "$snapshot_root/hermes-full.zip" \
  "$snapshot_root/hermes-dual-memory.tar.gz" \
  "$snapshot_root/research-profile.tar.gz" \
  > "$snapshot_root/SHA256SUMS"
du -sh "$snapshot_root" > "$snapshot_root/SIZE.txt"
```

Jangan commit snapshot atau path privat. Salin nilai tersanitasi ke
`SNAPSHOT-MANIFEST.md` dan lokasi aktual ke `CURRENT.md` bila aman.

## 4. Deploy Exact Beta Plugin

Deployment memakai staging + rename agar tidak meninggalkan direktori parsial.
Ulangi blok ini dengan `HERMES_HOME="$HOME/.hermes/profiles/research"` untuk
profile research:

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
src="$PWD/plugins/memory/hermes-dual-memory"
dst="$HERMES_HOME/plugins/hermes-dual-memory"
stage="$HERMES_HOME/plugins/.hermes-dual-memory.beta-stage"
previous="$HERMES_HOME/plugins/.hermes-dual-memory.pre-beta"

mkdir -p "$stage"
cp -a "$src/." "$stage/"

"$HOME/.hermes/hermes-agent/venv/bin/python" -m compileall -q "$stage"
test -f "$stage/answerability.py"

mv "$dst" "$previous"
mv "$stage" "$dst"
```

Jangan hapus `$previous` sampai beta selesai. Jika salah satu `mv` gagal,
kembalikan direktori sebelumnya sebelum gateway start.

## 5. Verify Deployed Code

```bash
for file in \
  __init__.py admission.py answerability.py cli.py consolidation.py decay.py \
  procedural.py storage.py plugin.yaml
do
  cmp \
    "plugins/memory/hermes-dual-memory/$file" \
    "$HERMES_HOME/plugins/hermes-dual-memory/$file"
done
```

Semua `cmp` wajib exit `0`.

## 6. Restart & Smoke

```bash
systemctl --user start hermes-gateway.service hermes-gateway-nellie.service
systemctl --user is-active hermes-gateway.service
systemctl --user is-active hermes-gateway-nellie.service
HERMES_HOME="$HOME/.hermes" hermes config get memory.provider
HERMES_HOME="$HOME/.hermes/profiles/research" hermes config get memory.provider
```

Lakukan lima smoke task tersanitasi lewat Hermes:

1. recall fakta valid lintas sesi;
2. current-state query tidak menampilkan superseded fact;
3. before-state query menampilkan historical fact;
4. no-answer query tidak menyuntik neighbor;
5. known quarantined fixture tidak visible.

Catat latency dan hasil di jurnal. Jalankan baseline subset bila diperlukan:

```bash
PYTHONPATH="$HOME/.hermes/hermes-agent:$PWD" \
  "$HOME/.hermes/hermes-agent/venv/bin/python" \
  evaluation/phase8_regression.py \
  --output /tmp/beta-smoke.json \
  --compare-to docs/testing/baselines/phase-8-baseline.json \
  --categories single_session_recall,temporal_reasoning,abstention,security_exclusion \
  --skip-token-measurement
```

`--skip-token-measurement` tetap memakai provider untuk answerability verifier.

## 7. Start Beta Clock

Jika seluruh smoke PASS:

- ubah status `CURRENT.md` menjadi `Berjalan`;
- isi tanggal mulai dan target selesai `+21 hari`;
- centang preflight di `README.md`;
- isi `SNAPSHOT-MANIFEST.md`;
- append entri `beta dimulai` di jurnal.

## Rollback Darurat

Stop seluruh gateway profile yang masuk scope lebih dulu:

```bash
systemctl --user stop hermes-gateway.service hermes-gateway-nellie.service
```

### Rollback Deployment Saja

Jika data belum berubah/migrasi dan hanya deployment yang gagal:

```bash
mv "$HOME/.hermes/plugins/hermes-dual-memory" \
   "$HOME/.hermes/plugins/.hermes-dual-memory.failed"
mv "$HOME/.hermes/plugins/.hermes-dual-memory.pre-beta" \
   "$HOME/.hermes/plugins/hermes-dual-memory"
```

### Rollback Code + Data

Untuk S0/S1 atau perubahan schema/vector/shadow:

1. simpan snapshot incident baru bila aman;
2. pindahkan direktori aktif ke lokasi karantina;
3. extract archive profile-scoped dari snapshot beta yang dipilih ke setiap
   `HERMES_HOME` yang berpasangan;
4. deploy code dari tag `v0.1.0-beta.1` atau pre-beta plugin sesuai pasangan
   snapshot yang dipilih;
5. jalankan SQLite integrity check;
6. start gateway dan ulang smoke test.

Jangan memakai `git reset --hard`, force-push, atau menghapus data aktif sebagai
bagian rollback operasional.
