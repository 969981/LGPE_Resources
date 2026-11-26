# ExeFS LGPE 1.0.2 static RE

The extracted `0/` directory contains `main`, `main.npdm`, `rtld`, `sdk`, `subsdk0`, `subsdk1`. Verify actual headers before NSO decoding/import, inspect segments/relocation/bases (the supplied tree only proves file names).

- Use a version-matched Ghidra and Switch Loader; inspect its Ghidra and Java support before building.
- Keep actual sample SHA256, NSO sections/offset ranges, function names and `main+offset` offsets in `docs/research/`, *not hardcoded into game-generic scripts*.
- Start with references to the exact binary data being decoded: `personal_total.bin`, `encount_data_p.bin`, `btl_ai_basic.amx`, `GO Park` message and resources. Cross-reference loaders/decompressors and data consumers.
- Research RNG only after tracing caller/callee, state storage and selection behavior. Static encounter tables and `main` calls aren't enough to prove a PID/EC or shiny algorithm.
- External reference: PokeLDN LGPE 1.0.2 session analysis, https://decryptu.github.io/pokeldn/lgpe_session.html. It documents PIA/LDN trade code but all binary offsets must be independently checked against the local user's `main`.
- Prioritize study, documentation and read-only probes; avoid real-world online misuse or altering third-party network traffic.
