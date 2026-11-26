# LGPE multilingual text: `.dat` + `.tbl`

Candidate `bin/message/<Language>/{common,script}/*.{dat,tbl}` pairs are visible in the uploaded tree. `pokedat` explicitly supports LGPE with `.dat/.tbl`; `CMahk/read_swsh` supports Let's Go text and warns that some control codes/variables may not decode cleanly. `pkNX` editor supplies a known TextFile implementation.

First test sample: `bin/message/English/common/bag.dat` and `bag.tbl` (the file tree confirms both). To run after fetching the public `pokedat` source and confirming its current CLI:

```powershell
cd tools/src/pokedat
python main.py read 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\1\bin\message\English\common\bag.dat' 'D:\scratch\lgpe_text' --version=LGPE --format=json
```

Inspect the exact emitted JSON name/structure rather than assuming it, then ingest it with:

```powershell
cd 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
uv run lgpe ingest --partition romfs --source 'bin/message/English/common/bag.dat' --export 'D:\scratch\lgpe_text\bag.json' --suffix '.json' --method 'pokedat LGPE' --tool-version '<commit>'
```

Compare with pkNX: count of index records, label/hash relationships, control codes (avoid silently stripping them), text decoding of French/Chinese/Japanese, and the effect of unknown controls. For `.tbl` output consider a separate `foo.csv` metadata file with **source `.tbl`** in receipt, avoiding a duplicate same-stem `.dat` destination. Do not merge unrelated sort-table `.dat` with message `.dat` assumptions.
