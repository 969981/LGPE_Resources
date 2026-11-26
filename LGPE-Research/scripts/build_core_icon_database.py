"""Join verified core image report to exact message labels and personal-table evidence."""
from __future__ import annotations
import argparse, json, hashlib, struct
from pathlib import Path
from dataclasses import asdict
from lgpe_research.image_resource_core import LGPEImageResourceCore, POKE, ITEM, TYPE, LANGS
from audit_image_resources import PROJECT, SOURCE

def message_index(path, prefix):
    rows=json.loads(path.read_text(encoding="utf8"))["lines"]
    out={}
    for r in rows:
        label=r["id"]
        if label and label.startswith(prefix+"_") and label.split("_")[-1].isdigit():
            n=int(label.split("_")[-1])
            if n in out: raise ValueError("duplicate message label")
            out[n]=r
    return out

def personal_info(data,species,form):
    if len(data)%84: raise ValueError("personal stride")
    def row(index):
        if not 0<=index<len(data)//84: raise ValueError("personal index")
        b=data[index*84:(index+1)*84]
        return dict(index=index,gender_ratio=b[18],form_stats_index=struct.unpack_from("<H",b,28)[0],form_count=b[32],type_indices=list(b[6:8]))
    if species==0: return None
    base=row(species)
    if not 0<=form<base["form_count"]: raise ValueError("form count")
    if form and not base["form_stats_index"]: raise ValueError("missing form stats index")
    return row(base["form_stats_index"]+form-1 if form else species)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report",type=Path,default=PROJECT/"work/core-icon-validation.json")
    ap.add_argument("--output",type=Path,default=PROJECT/"work/core-icon-database.json")
    args=ap.parse_args()
    core=LGPEImageResourceCore.from_path(args.report)
    msg=PROJECT/"decoded/1.0.2/romfs/bin/message/Simp_Chinese/common"
    mons=message_index(msg/"monsname.json","MONSNAME")
    items=message_index(msg/"itemname.json","ITEMNAME")
    info=message_index(msg/"iteminfo.json","ITEMINFO")
    types=message_index(msg/"typename.json","TYPENAME")
    personal_path=SOURCE/"bin/pokelib/personal/personal_total.bin"
    data=personal_path.read_bytes()
    if len(data)!=82320: raise ValueError("personal size")
    records=[]
    for r in core.resources:
        entry=asdict(r)
        entry["native_selector_status"]="UNVERIFIED"
        if r.group=="pokemon":
            s,f,g,p=POKE.fullmatch(r.key).groups()
            s,f=int(s),int(f)
            entry.update(species_candidate=s,form_candidate=f,gender_symbol=g,palette_symbol=p,
                         name_zh=mons[s]["text"],name_message_id=mons[s]["id"],personal=personal_info(data,s,f),
                         mapping_evidence="RESOURCE_NAME_PLUS_PERSONAL_FORM_BOUNDS" if s else "PLACEHOLDER")
        elif r.group=="item":
            m=ITEM.fullmatch(r.key)
            if m:
                n=int(m[1])
                entry.update(item_id_candidate=n,name_zh=items[n]["text"],name_message_id=items[n]["id"],
                             description_zh=info[n]["text"],description_message_id=info[n]["id"],mapping_evidence="RESOURCE_NAME_PLUS_MESSAGE_LABEL")
            else: entry["mapping_evidence"]="PLACEHOLDER"
        else:
            m=TYPE.fullmatch(r.key)
            n=int(m[2])
            # The decoded message table is contiguous by index but its labels skip 009.
            label=n if n<9 else n+1
            if types[label]["index"]!=n: raise ValueError("type label/index mismatch")
            entry.update(icon_index=n,type_message_label_number=label,name_message_id=types[label]["id"],
                         name_zh=types[label]["text"],text_variant=bool(m[1]),mapping_evidence="RESOURCE_INDEX_PLUS_MESSAGE_ORDER")
        records.append(entry)
    result={"schema":"lgpe-image-resource-core-v1","personal_sha256":hashlib.sha256(data).hexdigest(),
            "message_sha256":{n:hashlib.sha256((msg/(n+".json")).read_bytes()).hexdigest() for n in ("monsname","itemname","iteminfo","typename")},
            "records":records}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({"records":len(records),"pokemon":sum(r["group"]=="pokemon" for r in records),
        "pokemon_personal_valid":sum(r.get("personal") is not None for r in records),
        "items_named":sum("item_id_candidate" in r for r in records),"types_named":sum("icon_index" in r for r in records)},indent=2))
    assert len(records)==725
    assert core.pokemon.resolve(25,0,"m") and core.pokemon.resolve(25,0,"f")
    assert core.pokemon.resolve(25,8,"f") and core.pokemon.resolve(25,9,"m") is None
    assert core.pokemon.resolve(25,0,"m","s") is None
    assert core.item.resolve(4) and core.item.resolve(9999) is None
    assert core.type.resolve(9,"sch",True) and core.type.resolve(18,"sch") is None
if __name__=="__main__": main()
