"""Validate core UI icons from original SARC; compare XML, decoded PNG and pixel evidence."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, re, struct, tempfile, zlib
from pathlib import Path, PureWindowsPath
import xml.etree.ElementTree as ET
from PIL import Image
from lgpe_research.archive_reader import read_sarc
from lgpe_research.assets_decode import write_png_rgba, validate_output, safe_name
from audit_image_resources import PROJECT, SOURCE, brti_rows, rgba, linearize

LANGS = ("jpn","eng","fre","ger","ita","kor","sch","spa","tch")
CASES = [("pokemon","bin/app/icon_pokemon/dummy.arc","dummy.flyt",221),
         ("item","bin/app/icon_item/itemdummy.arc","itemdummy.flyt",180)]
CASES += [(lang,"bin/app/icon_type/icon_type"+("" if lang=="jpn" else "_"+lang)+".arc","dummy.flyt",36) for lang in LANGS]
def sha(data): return hashlib.sha256(data).hexdigest()
def crc(data): return f"{zlib.crc32(data)&0xffffffff:08x}"
def key(name): return name[:-2] if name.endswith(("^j","^u")) else name
def xml_names(data):
    root=ET.fromstring(data)
    return [PureWindowsPath(e.attrib["imagePath"]).stem for e in root.iter()
            if e.tag.split("}")[-1]=="textureFile"]

def pillow_bc7(raw,w,h):
    # DDS DX10 header for a single BC7_UNORM 2D surface.
    header=bytearray(148)
    header[:4]=b"DDS "
    for p,v in ((4,124),(8,0x81007),(12,h),(16,w),(20,len(raw)),
                (28,1),(76,32),(80,4),(108,0x1000),(128,98),(132,3),(140,1)):
        struct.pack_into("<I",header,p,v)
    header[84:88]=b"DX10"
    with Image.open(io.BytesIO(header+raw)) as im:
        return im.convert("RGBA").tobytes()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root",type=Path,default=SOURCE)
    ap.add_argument("--report",type=Path,default=PROJECT/"work/core-icon-validation.json")
    ap.add_argument("--png-dir",type=Path,help="optional local PNG export; not committed")
    args=ap.parse_args()
    root=args.source_root.resolve(strict=True)
    report_path=args.report.resolve()
    if report_path.is_relative_to(root): raise ValueError("report inside source")
    if args.png_dir and (args.png_dir.resolve().is_relative_to(root) or root.is_relative_to(args.png_dir.resolve())):
        raise ValueError("PNG root must be disjoint from source")
    evidence_path=PROJECT/"docs/image-resources/evidence/item-rgb5a1-20261126.csv"
    with evidence_path.open(encoding="utf8") as f:
        expected={r["name"]:r for r in csv.DictReader(f)}
    report={"cases":[]}
    for group,relative,layout,expected_count in CASES:
        rec={"group":group,"source":relative,"textures":[]}
        report["cases"].append(rec)
        try:
            path=root/relative
            path.resolve(strict=True).relative_to(root)
            data=path.read_bytes()
            rec["source_sha256"]=sha(data)
            members={meta["internal_path"]:payload for meta,payload in read_sarc(data)}
            bntx=members["timg/__Combined.bntx"]
            rec["bntx_sha256"]=sha(bntx)
            names=xml_names(members[layout])
            entries=list(brti_rows(bntx))
            actual=[key(row["name"]) for row,_ in entries]
            rec.update(xml_count=len(names),brti_count=len(actual),name_match=(set(names)==set(actual) and len(actual)==len(set(actual))==len(names)==expected_count))
            if not rec["name_match"]: raise ValueError("XML/BRTI name or count mismatch")
            for row,payload in entries:
                tr={**row}
                rec["textures"].append(tr)
                try:
                    pixels=rgba(row,payload)
                    w,h=row["width"],row["height"]
                    tr.update(rgba_sha256=sha(pixels),rgba_crc32=crc(pixels),
                              opaque_pixels=sum(v==255 for v in pixels[3::4]),
                              transparent_pixels=sum(v==0 for v in pixels[3::4]))
                    if group=="item":
                        ev=expected[row["name"]]
                        tr["connector_crc_match"]=(ev["rgba_crc32"]==crc(pixels))
                        if not tr["connector_crc_match"]: raise ValueError("remote RGBA CRC mismatch")
                    if row["format_code"] in (0x2001,0x2006):
                        raw=linearize(payload,(w+3)//4,(h+3)//4,16,row["block_height_log2"])
                        tr["linear_bc7_sha256"]=sha(raw)
                        ref=pillow_bc7(raw,w,h)
                        errors=[abs(a-b) for a,b in zip(pixels,ref,strict=True)]
                        tr.update(bc7_pillow_exact=(pixels==ref),bc7_max_delta=max(errors,default=0),
                                  bc7_differing_channels=sum(v!=0 for v in errors))
                    with tempfile.TemporaryDirectory() as tmp:
                        png=Path(tmp)/"texture.png"
                        write_png_rgba(png,w,h,pixels,srgb=row["format_code"]==0x2006)
                        validate_output(png)
                        with Image.open(png) as im:
                            if im.convert("RGBA").tobytes()!=pixels: raise ValueError("PNG round-trip mismatch")
                        tr["png_sha256"]=sha(png.read_bytes())
                        if args.png_dir:
                            out=args.png_dir.resolve()/group/(safe_name(row["name"])+".png")
                            out.parent.mkdir(parents=True,exist_ok=True)
                            if not out.resolve().is_relative_to(args.png_dir.resolve()): raise ValueError("unsafe PNG path")
                            if out.exists():
                                if out.read_bytes()!=png.read_bytes(): raise ValueError("PNG conflict")
                            else:
                                with out.open("xb") as f: f.write(png.read_bytes())
                    tr["status"]="PNG_ROUNDTRIP_OK"
                except Exception as e:
                    tr.update(status="FAILED",error=f"{type(e).__name__}: {e}")
            rec["status"]="PASS" if all(t["status"]=="PNG_ROUNDTRIP_OK" for t in rec["textures"]) else "FAILED"
        except Exception as e: rec.update(status="FAILED",error=f"{type(e).__name__}: {e}")
    textures=[t for case in report["cases"] for t in case["textures"]]
    good=[t for t in textures if t.get("status")=="PNG_ROUNDTRIP_OK"]
    bc7=[t for t in good if "bc7_pillow_exact" in t]
    report["summary"]={"cases_pass":sum(c["status"]=="PASS" for c in report["cases"]),
        "textures":len(textures),"png_roundtrip_ok":len(good),
        "unique_rgba":len({(t["width"],t["height"],t["format_code"]==0x2006,t["rgba_sha256"]) for t in good}),
        "bc7_compared":len(bc7),"bc7_exact":sum(t["bc7_pillow_exact"] for t in bc7),
        "bc7_max_delta":max((t["bc7_max_delta"] for t in bc7),default=None)}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(report["summary"],indent=2))
    return int(any(c["status"]!="PASS" for c in report["cases"]))
if __name__=="__main__": raise SystemExit(main())
