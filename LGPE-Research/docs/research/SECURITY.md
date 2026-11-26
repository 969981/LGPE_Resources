# Sample path and binary extraction safety

Untrusted archive entry names can contain `../`, absolute paths, odd Unicode, NTFS alternate streams, Windows device names, or symlinks. The current `ingest-container` command copies files **already extracted by a third party** while guarding resolved destination paths; this is not a substitute for validating the archive parser. Extend the parser with per-entry and total-size limits, deduplication, invalid filename reporting, symlink/reparse-point rejection, and output quota before running a mass extract. Never run game code or arbitrary scripts merely to inspect assets.

Code and docs do not distribute game files or decryption keys. Git ignores binary dumps and generated data by default; still check staged files. You are responsible for your legally obtained game content and licenses of any outside tools.
