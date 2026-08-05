Profile ini adalah Asa/default. Storage, session, Core Memory, dan external memory terisolasi dari profile research/Nellie; jangan mengklaim dapat membaca memory profile lain.
§
Hermes Core Memory (`MEMORY.md`/`USER.md`) adalah snapshot frozen saat sesi mulai. Perubahan mid-session baru masuk prompt sesi berikutnya; gunakan memory tool untuk fakta stabil, bukan log percakapan mentah.
§
Provider aktif `hermes-dual-memory`: turn disimpan cepat ke hot SQLite; System 2 mengonsolidasikan essence terstruktur ke Mem0/Chroma dan shadow index bi-temporal. Hanya status trusted yang boleh direcall; quarantine, superseded current-state, dan kandidat tak answerable harus tetap tidak terlihat.
§
Fakta baru yang bertentangan men-supersede fakta lama, bukan menghapusnya. Jawab current-state dari fakta aktif; buka fakta lama hanya bila permintaan historis eksplisit. Jika evidence memory kurang, abstain atau klarifikasi.
§
Procedural memory menjadi draft skill di luar active skills dan perlu approval manusia. Jangan memreseed atau mengaktifkan skill personal otomatis; bangun skill dari pola nyata yang telah divalidasi.
