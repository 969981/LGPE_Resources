# Specific LGPE 1.0.2 research targets from attached tree

All paths below are **relative to `1/bin/`**. They are verified as filenames from the supplied tree, not decoded content:

1. `archive/pokemon/pm0001_00.gfpak`: test GFPAK extraction, model/texture skeleton relationships.
2. `archive/field/area01.gfpak`: field/scene resources; map asset identity.
3. `archive/script_amx.gfpak`: cross-check script archiving against `battle/ai_script/*.amx`.
4. `pokelib/personal/personal_total.bin`: Pokémon personal data struct layout, regional forms, starter differences; compare pkNX.
5. `field/param/encount/encount_data_p.bin` and `encount_data_e.bin`: GameManagerGG EncounterArchive parsing and spawn-table schema. Do not equate wild encounter config with runtime RNG.
6. `battle/ai_script/btl_ai_basic.amx`: candidate script VM and game code references.
7. `message/English/common/bag.dat` and `bag.tbl`: first paired-text decoding sample.
8. `app/battle/bin/battle_command_00.arc`: first ARC recognition sample.
9. `archive/buddy_mood_pikachu.gfpak`: Pikachu buddy behavior/config clues.
10. `app/palma/rgbled/poke_c_0025_008_N.bin`: controller LED resource data candidate; treat as unknown binary until headers examined.

After data work, inspect ExeFS `0/main` for loader/readers and annotate e.g. `fn name / main+offset / actual instruction / xrefs / field inference / evidence`; never state unverified RNG formulae. PokeLDN LGPE session research provides **one external address cross-check only**: https://decryptu.github.io/pokeldn/lgpe_session.html .
