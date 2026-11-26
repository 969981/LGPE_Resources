# T08 GFBCol schema follow-up — 2026-10-29

## Five real sample/output cross-checks

I read five extracted LGPE 1.0.2 RomFS sources and their already generated path-mirrored JSON views. For each sample, the source bytes hash equals both `manifests/collisions.jsonl` and the JSON's embedded source hash; the output bytes hash equals the manifest receipt; the output path preserves the source-relative path with only `.gfbcol` changed to `.json`. Every row and JSON still records `status`, `schema_status`, and `slot_semantics` as `UNKNOWN`.

| RomFS-relative source | Bytes | Source SHA-256 | Mirrored JSON SHA-256 |
|---|---:|---|---|
| `bin/field/model/com_chika/underground01_00_floor.gfbcol` | 612 | `6c37be45daf9f582684d43022ad0ecf8c406cd9c7722fee710151cacc84e7ba0` | `b464af7257244ea545ef8cfc402899fcb25a5e96c62eb9bfed1c5bc9e0166893` |
| `bin/field/model/com_chika/underground01_00_wall.gfbcol` | 840 | `4db22c0af8008e8247fcd2e0a6345a6e911b01d35a2bb0f395e64db96abdc345` | `2c1ae5500c311659dbc5d88cdcfadb4902a3b49c876b48f69de780ade2dbc8ec` |
| `bin/field/model/area01/road023_00_zone.gfbcol` | 360 | `7e150214648ed58b9d973466b62f4de25c57c6b2a52bbef49e96241629470473` | `f79972c8b4954130ab73a168eda72437ff6aaa9c750c296e5dca0eeed117ac9b` |
| `bin/field/model/area01/road023_enc01.gfbcol` | 516 | `6153240b2ef073928dc7486f1ebe92aad24a281fc2bf0eef530ccdb14ff0a2b7` | `adf63662b6a706e42b6a42aab4240b33b03349151e4c1478f49531321aa56b70` |
| `bin/field/model/area02/skyenc_col.gfbcol` | 26,472 | `e0fe0fcfc9aedb2e16912bd33bc1a4f0d774bf5a2907b7d6b568004ebff679c1` | `34ac77c064955cab398cd12473a93179156a8bf75e4ff01910ffabeb729fc927` |

All five share a root-table envelope: the root uoffset points to `0x10`; the vtable at `0x04` is 12 bytes; the root object is 20 bytes; and its four recorded slot offsets are `[4, 8, 12, 16]`. The raw prefixes of slots 0 and 1 vary across samples; slots 2 and 3 begin with `38 00 00 00` and `0c 00 00 00` in these five. These are byte observations only and do not name fields or establish vector types.

The cross-check can be rerun from the project root with Python 3.12. It reads the original RomFS files and existing outputs without writing either:

```bash
python3 - <<'PY'
import hashlib, json
from pathlib import Path, PurePosixPath
romfs = Path('../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1')
manifest = {r['source']: r for r in map(json.loads, Path('manifests/collisions.jsonl').read_text().splitlines())}
samples = (
    'bin/field/model/com_chika/underground01_00_floor.gfbcol',
    'bin/field/model/com_chika/underground01_00_wall.gfbcol',
    'bin/field/model/area01/road023_00_zone.gfbcol',
    'bin/field/model/area01/road023_enc01.gfbcol',
    'bin/field/model/area02/skyenc_col.gfbcol',
)
for rel in samples:
    row = manifest[rel]
    source = (romfs / rel).read_bytes()
    output_path = Path(row['output'])
    output = output_path.read_bytes()
    doc = json.loads(output)
    assert row['source_sha256'] == doc['source']['sha256'] == hashlib.sha256(source).hexdigest()
    assert row['output_sha256'] == hashlib.sha256(output).hexdigest()
    assert PurePosixPath(row['output']) == PurePosixPath('decoded/1.0.2/romfs') / PurePosixPath(rel).with_suffix('.json')
    assert row['status'] == doc['schema_status'] == doc['slot_semantics'] == 'UNKNOWN'
    assert doc['root_table']['object_bytes'] == 20
    assert [s['field_offset'] for s in doc['root_table']['slots']] == [4, 8, 12, 16]
    print(rel, len(source), row['source_sha256'], row['output_sha256'], 'verified')
PY
```

## Source-backed schema search

The local Switch-Toolbox checkout is pinned at `3fcb87f1fea25ad56db139b0d9577db591f54118`. A read-only `git ls-remote https://github.com/KillzXGaming/Switch-Toolbox.git HEAD refs/heads/master` returned the same commit, so the pinned source is also the upstream master head checked on this date. A literal source search returned no matches (exit status 1):

```bash
rg -n -i --hidden --glob '!**/.git/**' --glob '!**/.gradle/**' --glob '!**/build/**' --glob '!**/bin/**' 'gfbcol' tools/src
```

The source does contain a generated `CollisionGroup` table, but it is explicitly part of GFBMDL: `Switch_Toolbox_Library/Resources/FlatBuffers/gfbmdl.fbs` declares `Model.CollisionGroups:[CollisionGroup]` and the table fields `BoneIndex`, `Unknown1`, `BoneChildren`, and `Bounding`. The generated GFBMDL `BoundingBox` is six float32 values (24 bytes). Blender's `GFLib/Model/Model.py:187–203` reads these groups only from the GFBMDL model table; neither checkout has a standalone GFBCol reader.

This GFBMDL table is not a safe schema substitute for the standalone root table observed in the `.gfbcol` samples. Although both expose four vtable slots, GFBCol's recorded root object is 20 bytes, while the GFBMDL `CollisionGroup`'s fourth slot is a 24-byte inline `BoundingBox` at object offset 16. That struct cannot fit in a 20-byte object. This rejects reuse of this particular table definition; it does not reveal what the standalone GFBCol slots mean.

No LGPE-specific standalone GFBCol schema or loader was found in the pinned local tool sources or in the latest Switch-Toolbox head checked here. The existing decoder therefore remains a generic root/vtable indexer: it does not traverse children or emit collision names, geometry, or typed fields. All **698** source files keep semantic `UNKNOWN`, while their existing JSON views and receipts remain useful for structural inspection. No code or tests were changed in this follow-up, and no original input was modified.
