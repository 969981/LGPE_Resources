"""Read-only raw LGPE archive -> BNTX/BRTI inventory and bounded PNG exports."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from collections import Counter
from lgpe_research.archive_reader import read_sarc, read_gfpak
from lgpe_research.assets_decode import write_png_rgba, validate_output

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
def digest(b): return hashlib.sha256(b).hexdigest()

def brti_rows(data):
    def take(p, n):
        if p < 0 or n < 0 or p+n > len(data): raise ValueError("BNTX bounds")
        return data[p:p+n]
    def u(p, fmt): return struct.unpack("<"+fmt, take(p, struct.calcsize("<"+fmt)))[0]
    if take(0,8) != b"BNTX\0\0\0\0" or take(12,2) != b"\xff\xfe" or take(32,4) != b"NX  " or u(28,"I") != len(data):
        raise ValueError("unsupported BNTX header")
    n, table = u(36,"I"), u(40,"Q")
    if not 0 < n <= 100000: raise ValueError("invalid texture count")
    take(table, n*8)
    seen = set()
    for i in range(n):
        p = u(table+i*8,"Q")
        if p in seen or take(p,4) != b"BRTI": raise ValueError("bad BRTI pointer")
        seen.add(p)
        take(p,u(p+4,"I"))
        np = u(p+0x60,"Q")
        size = u(np,"H")
        name = take(np+2,size).decode("utf-8")
        if take(np+2+size,1) != b"\0": raise ValueError("invalid texture name")
        mip_count = u(p+0x16,"H")
        if not 0 < mip_count <= 32: raise ValueError("invalid mip count")
        mp = u(p+0x70,"Q")
        offsets = [u(mp+8*j,"Q") for j in range(mip_count)]
        start, length = offsets[0], u(p+0x50,"I")
        if not length or offsets != sorted(set(offsets)) or any(x >= start+length for x in offsets):
            raise ValueError("invalid mip offsets")
        payload = take(start,length)
        yield dict(index=i,name=name,brti_offset=p,format_code=u(p+0x1c,"I"),
                   width=u(p+0x24,"I"),height=u(p+0x28,"I"),depth=u(p+0x2c,"I"),
                   array_count=u(p+0x30,"I"),tile_mode=u(p+0x10,"B"),
                   mip_count=mip_count,block_height_log2=u(p+0x34,"I")&7,
                   component_selectors=list(take(p+0x58,4)),data_offset=start,
                   data_bytes=length,payload_sha256=digest(payload)),payload

def linearize(payload,w,h,bpp,log):
    if not 0 <= log <= 5 or not 0 < w*h <= 16777216: raise ValueError("surface limits")
    bh=1<<log
    pitch=(w*bpp+63)//64
    out=bytearray(w*h*bpp)
    for y in range(h):
        for x in range(w):
            xb=x*bpp
            pos=(y//(8*bh))*512*bh*pitch+(xb//64)*512*bh+((y%(8*bh))//8)*512
            pos+=((xb%64)//32)*256+((y%8)//2)*64+((xb%32)//16)*32+(y%2)*16+xb%16
            if pos+bpp>len(payload): raise ValueError("GOB bounds")
            dest=(y*w+x)*bpp
            out[dest:dest+bpp]=payload[pos:pos+bpp]
    return bytes(out)

def rgba(row,payload):
    if (row["depth"],row["array_count"],row["tile_mode"],row["mip_count"],row["component_selectors"]) != (1,1,1,1,[2,3,4,5]):
        raise NotImplementedError("only observed single-mip 2D identity-channel block-linear textures")
    w,h=row["width"],row["height"]
    if not 0 < w*h <= 16777216: raise ValueError("pixel limits")
    f=row["format_code"]
    if f==0x0501:
        raw=linearize(payload,w,h,2,row["block_height_log2"])
        out=bytearray()
        for (v,) in struct.iter_unpack("<H",raw):
            out.extend((((v&31)*255+15)//31,(((v>>5)&31)*255+15)//31,(((v>>10)&31)*255+15)//31,255*(v>>15)))
        return bytes(out)
    if f in (0x2001,0x2006):
        import texture2ddecoder
        raw=linearize(payload,(w+3)//4,(h+3)//4,16,row["block_height_log2"])
        bgra=texture2ddecoder.decode_bc7(raw,w,h)
        if len(bgra)!=w*h*4: raise ValueError("BC7 pixel length")
        out=bytearray(bgra)
        out[0::4],out[2::4]=bgra[2::4],bgra[0::4]
        return bytes(out)
    raise NotImplementedError("format not supported by this bounded PNG adapter")

def sources(root):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".arc",".gfpak",".bntx",".bffnt"}:
            p.resolve(strict=True).relative_to(root)
            yield p

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root",type=Path,default=SOURCE)
    ap.add_argument("--prefix",default="",help="only source relative paths beginning with this prefix")
    ap.add_argument("--png",action="store_true",help="export supported raw RGBA textures, never final UI renders")
    args=ap.parse_args()
    root=args.source_root.resolve(strict=True)
    out=(PROJECT/"work/image-resources").resolve()
    if out.is_relative_to(root) or root.is_relative_to(out): raise ValueError("output must be disjoint")
    out.mkdir(parents=True,exist_ok=True)
    counts=Counter()
    with (out/"texture-index.jsonl").open("w",encoding="utf8") as log:
        def emit(row):
            log.write(json.dumps(row,ensure_ascii=False)+"\n")
            counts[row["status"]]+=1
        def inspect(data,source,source_hash,member=None):
            cid=digest(data)
            try:
                rows=list(brti_rows(data))
                for row,payload in rows:
                    record={**row,"source":source,"source_sha256":source_hash,"member":member,"bntx_sha256":cid,"status":"INDEXED"}
                    if args.png:
                        try:
                            pixels=rgba(row,payload)
                            ph=digest(struct.pack("<II?",row["width"],row["height"],row["format_code"]==0x2006)+pixels)
                            dest=out/"png"/(ph+".png")
                            dest.parent.mkdir(exist_ok=True)
                            if dest.resolve().parent != (out/"png").resolve() or (out/"png").is_symlink():
                                raise ValueError("unsafe PNG output")
                            if not dest.exists(): write_png_rgba(dest,row["width"],row["height"],pixels,srgb=row["format_code"]==0x2006)
                            # Verify exact bytes using a deterministic staged regeneration.
                            import tempfile
                            with tempfile.TemporaryDirectory(dir=out) as tmp:
                                check=Path(tmp)/"check.png"
                                write_png_rgba(check,row["width"],row["height"],pixels,srgb=row["format_code"]==0x2006)
                                if check.read_bytes()!=dest.read_bytes(): raise ValueError("conflicting PNG")
                            record.update(status="RAW_RGBA",pixel_sha256=ph,png_sha256=digest(dest.read_bytes()),png=str(dest.relative_to(out)),validation=validate_output(dest))
                        except NotImplementedError as e: record.update(status="INDEXED_UNSUPPORTED_PNG",error=str(e))
                        except Exception as e: record.update(status="PNG_FAILED",error=str(e))
                    emit(record)
            except Exception as e: emit(dict(source=source,source_sha256=source_hash,member=member,bntx_sha256=cid,status="BNTX_FAILED",error=str(e)))
        for p in sources(root):
            rel=p.relative_to(root).as_posix()
            if not rel.startswith(args.prefix): continue
            data=p.read_bytes(); sh=digest(data)
            if data.startswith(b"BNTX"): inspect(data,rel,sh)
            elif data.startswith((b"SARC",b"GFLXPACK")):
                try:
                    members=read_sarc(data) if data.startswith(b"SARC") else read_gfpak(data)
                    counts["archives_attempted"]+=1
                    for meta,payload in members:
                        if payload.startswith(b"BNTX"): inspect(payload,rel,sh,meta)
                    counts["archives_completed"]+=1
                except Exception as e: emit(dict(source=rel,source_sha256=sh,status="ARCHIVE_FAILED",error=str(e)))
            elif p.suffix.lower()==".bffnt":
                try:
                    from lgpe_research.bffnt_decode import parse_bffnt
                    _, sheets=parse_bffnt(data)
                    for i,sheet in enumerate(sheets):
                        if sheet.startswith(b"BNTX"): inspect(sheet,rel,sh,{"font_sheet_index":i})
                except Exception as e: emit(dict(source=rel,status="FONT_FAILED",error=str(e)))
            else: emit(dict(source=rel,status="UNKNOWN_MAGIC"))
    (out/"summary.json").write_text(json.dumps(counts,indent=2),encoding="utf8")
    print(json.dumps(counts,indent=2))
    return int(any(v for k,v in counts.items() if k.endswith("FAILED") or k=="UNKNOWN_MAGIC"))
if __name__=="__main__": raise SystemExit(main())
