# Canonical Hermes Profile Assets

Direktori ini adalah source-of-truth file statis profile beta. Deploy target:

- `profiles/default/` → `$HOME/.hermes/`
- `profiles/research/` → `$HOME/.hermes/profiles/research/`

Yang boleh berada di sini: persona, seeded Core Memory, dan aturan workspace
tersanitasi. Jangan menaruh `.env`, token, session, channel ID, SQLite, Chroma,
isi memory dinamis, conversation mentah, atau skill custom yang dipreseed.

Layering mengikuti ADR-0017:

- `SOUL.md` → identity/character;
- `memories/USER.md` → stable user facts;
- `memories/MEMORY.md` → operational invariants;
- `workspace/.hermes.md` → project-specific instructions.

Tidak ada custom/personal skill yang dipreseed. Skill baru hanya masuk melalui
pipeline procedural memory: draft, validasi/security/Curator native, lalu approval
manusia. Deployer juga menghapus hanya daftar skill legacy yang pernah dikelola
repo; skill native lain tidak disentuh.
