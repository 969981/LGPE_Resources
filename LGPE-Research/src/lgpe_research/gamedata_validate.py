"""Compare decoded samples to independent upstream pkNX exports (no source writes)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

def compare(project):
    p=Path(project); w=p/"work/gamedata-crosscheck"; d=p/"decoded/1.0.2/romfs/bin"
    source=p.parent/"1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin"
    sys.path.insert(0,str(p/"tools/src/pokedat"))
    from text_config import GAME_VARIABLES
    names={v:f"{k:04X}" for k,v in GAME_VARIABLES["LGPE"].items()}
    def normalize(text,names):
        text=text.replace(chr(0x20bd),chr(0xe300))
        return re.sub(r"\[VAR ([^()\]]+)",lambda m:"[VAR "+names.get(m[1],m[1]),text)
    results=[]
    for language in ["English","Simp_Chinese"]:
        for name in ["common/bag","script/master_trainer"]:
            actual=json.loads((d/"message"/language/(name+".json")).read_text(encoding="utf-8"))
            upstream=json.loads((w/(language+"_"+Path(name).name+".json")).read_text(encoding="utf-8"))
            upnames={v:k for entry in upstream["variables"] for k,v in [entry.split("=",1)]}
            diffs=[i for i,(a,b) in enumerate(zip(actual["lines"],upstream["lines"])) if normalize(a["text"],names)!=normalize(b,upnames)]
            data=(source/"message"/language/(name+".dat")).read_bytes(); section=struct.unpack_from("<I",data,12)[0]
            byte_diffs=[]
            for i,raw in enumerate(upstream["bytes"]):
                off,n,flags=struct.unpack_from("<IHH",data,section+4+i*8)
                key=(0x7c89+i*0x2983)&65535; plain=[]
                for j in range(n):
                    plain.append(struct.unpack_from("<H",data,section+off+j*2)[0]^key)
                    key=((key<<3)|(key>>13))&65535
                if struct.pack("<"+"H"*n,*plain).hex().upper()!=raw: byte_diffs.append(i)
                assert actual["lines"][i]["flags"]==upstream["flags"][i]
            assert len(actual["lines"])==len(upstream["lines"])
            results.append(dict(sample=f"{language}/{name}",count=len(actual["lines"]),normalized_text_mismatches=diffs,decrypted_payload_mismatches=byte_diffs))
    actual=json.loads((d/"pokelib/personal/personal_total.json").read_text(encoding="utf-8"))["entries"]
    up=json.loads((w/"personal.json").read_text(encoding="utf-8")); diffs=[]; checks=0
    assert len(actual)==len(up)
    for i,(a,b) in enumerate(zip(actual,up)):
        for key,value in a.items():
            if key in b:
                checks+=1
                if value!=b[key]: diffs.append([i,key])
        for j,key in enumerate(["EV_HP","EV_ATK","EV_DEF","EV_SPE","EV_SPA","EV_SPD"]):
            checks+=1
            if a["EVYield"][j]!=b[key]: diffs.append([i,key])
    results.append(dict(sample="personal_total",count=len(actual),field_checks=checks,mismatches=diffs))
    for version in ["p","e"]:
        actual=json.loads((d/f"field/param/encount/encount_data_{version}.json").read_text(encoding="utf-8"))["tables"]
        up=json.loads((w/f"encount_{version}.json").read_text(encoding="utf-8"))["Table"]
        results.append(dict(sample=f"encount_data_{version}",count=len(actual),all_fields_equal=actual==up))
    report={"upstream":"pkNX d191cd0e5c05f2af81d9a41c1f1d82e6621b351a","results":results}
    (w/"comparison.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return int(any(r.get("mismatches") or r.get("normalized_text_mismatches") or r.get("decrypted_payload_mismatches") or r.get("all_fields_equal")==False for r in results))

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--project",required=True)
    raise SystemExit(compare(parser.parse_args().project))
