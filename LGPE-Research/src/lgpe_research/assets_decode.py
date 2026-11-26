"""Headless representative asset conversions; never writes into input trees.

Run from the repo: python -m lgpe_research.assets_decode --root . --execute
Adapters run pinned sources/executables supplied in tools/. Output records are
separate from the shared manifest until accepted by the pipeline orchestrator.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import wave
import zlib

SAMPLES = {
    'texture': 'bin/app/report/bin/fxmt_3_white202_a.bntx',
    'model': 'bin/app/report/bin/cmn_shadow.gfbmdl',
    'animation': 'bin/battle/waza/model/anm/ee006_kinomi.gfbanm',
    'particle': 'bin/app/gogopark/particle/ep_Appears/ep_Appears01_pm0050.ptcl',
    'audio': 'bin/sound/NX64/wwise/bank/1001133599.wem',
}
NULL = 0xffffffff


def sha256(path: Path) -> str:
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def safe_name(name: str) -> str:
    if not name or name in {'.', '..'} or any(ord(c)<32 for c in name) or any(c in name for c in '/\\:<>"|?*\0'):
        raise ValueError('Unsafe texture name')
    if name[-1] in '. ':
        raise ValueError('Unsafe trailing character')
    if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        raise ValueError('Reserved texture name')
    return name


def validate_output(path: Path) -> dict:
    data = path.read_bytes()
    if path.suffix == '.png':
        if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
            raise ValueError('Not PNG')
        width, height = struct.unpack_from('>II',data,16)
        if not width or not height:
            raise ValueError('Empty PNG')
        pos=8;compressed=bytearray();seen_iend=False
        while pos<len(data):
            if pos+12>len(data):raise ValueError('Truncated PNG chunk')
            length=struct.unpack_from('>I',data,pos)[0];tag=data[pos+4:pos+8]
            end=pos+12+length
            if end>len(data):raise ValueError('PNG chunk exceeds file size')
            payload=data[pos+8:pos+8+length]
            crc=struct.unpack_from('>I',data,pos+8+length)[0]
            if zlib.crc32(tag+payload)&0xffffffff!=crc:raise ValueError('PNG chunk CRC mismatch')
            if tag==b'IHDR':
                if pos!=8 or length!=13:raise ValueError('Invalid PNG IHDR')
                bit_depth,color_type,compression,filter_method,interlace=payload[8:13]
                channels={0:1,2:3,3:1,4:2,6:4}.get(color_type)
                valid_depths={0:{1,2,4,8,16},2:{8,16},3:{1,2,4,8},4:{8,16},6:{8,16}}
                if channels is None or bit_depth not in valid_depths[color_type] or compression!=0 or filter_method!=0 or interlace!=0:
                    raise ValueError('Unsupported PNG pixel layout')
            elif tag==b'IDAT':compressed.extend(payload)
            elif tag==b'IEND':
                if length!=0 or end!=len(data):raise ValueError('Invalid PNG IEND')
                seen_iend=True
                break
            pos=end
        if not seen_iend:raise ValueError('PNG lacks IEND')
        raw=zlib.decompress(compressed)
        row_bytes=(width*channels*bit_depth+7)//8
        if len(raw)!=height*(1+row_bytes):raise ValueError('PNG decompressed size mismatch')
        if any(raw[row*(1+row_bytes)]>4 for row in range(height)):
            raise ValueError('Invalid PNG row filter')
        return {'width':width,'height':height,'color_type':color_type,'bit_depth':bit_depth,'validated_bytes':len(raw)}
    if path.suffix == '.wav':
        with wave.open(str(path),'rb') as w:
            if w.getnframes() < 1 or w.getsampwidth()!=2:
                raise ValueError('Not nonempty PCM16 WAV')
            pcm=w.readframes(w.getnframes())
            if len(pcm)!=w.getnframes()*w.getnchannels()*w.getsampwidth():raise ValueError('Truncated WAV')
            return {'channels':w.getnchannels(),'sample_rate':w.getframerate(),'frames':w.getnframes(),'pcm_bytes':len(pcm)}
    if path.suffix == '.glb':
        if len(data)<20 or struct.unpack_from('<4sII',data)!=(b'glTF',2,len(data)):
            raise ValueError('Invalid GLB header')
        size,tag=struct.unpack_from('<I4s',data,12)
        if tag!=b'JSON' or size>len(data)-20:
            raise ValueError('Invalid GLB JSON chunk')
        obj=json.loads(data[20:20+size]);prims=[q for m in obj.get('meshes',[]) for q in m['primitives']]
        counts=[obj['accessors'][q['attributes']['POSITION']]['count'] for q in prims]
        if not counts or not all(n>0 for n in counts):raise ValueError('GLB lacks geometry')
        return {'meshes':len(obj['meshes']),'primitives':len(prims),'position_counts':counts,'nodes':len(obj.get('nodes',[]))}
    if path.suffix=='.json':
        return {'keys':list(json.loads(data))}
    raise ValueError('Unsupported output validation')


def ptcl_sections(data: bytes) -> dict:
    """Bounded VFXB section traversal; emitter simulation remains unsupported.

    Header/relative section links verified against Switch-Toolbox PCTL.cs.
    SectionSize is payload size, not a reliable enclosing section boundary.
    """
    if len(data)<32 or data[:4]!=b'VFXB' or data[12:14]!=b'\xff\xfe':
        raise ValueError('Unsupported VFXB header')
    declared=struct.unpack_from('<I',data,28)[0]
    if declared!=len(data):raise ValueError('VFXB size mismatch')
    start=struct.unpack_from('<H',data,22)[0];visited=set();sections=[]
    def parse(pos: int, depth: int) -> int:
        if depth>32 or len(visited)>=10000 or pos in visited:
            raise ValueError('VFXB cyclic/excessive section links')
        if pos<32 or pos+32>len(data):raise ValueError('VFXB section out of bounds')
        visited.add(pos)
        tag,size,child,nxt,unk,binary,unk3,count=struct.unpack_from('<4s7I',data,pos)
        name=tag.decode('ascii')
        if not all(32<=c<127 for c in tag):raise ValueError('Invalid section signature')
        entry={'offset':pos,'signature':name,'payload_bytes':size,'child_offset':child,'next_offset':nxt,'binary_offset':binary,'child_count':count,'depth':depth}
        if binary!=NULL and (binary<32 or pos+binary+size>len(data)):
            raise ValueError('VFXB payload out of bounds')
        sections.append(entry)
        if child!=NULL:
            if child<32:raise ValueError('VFXB child overlaps header')
            cpos=pos+child
            for _ in range(count or 1):
                following=parse(cpos,depth+1)
                if following==NULL:break
                cpos=following
        if nxt==NULL:return NULL
        if nxt<32 or pos+nxt>=len(data):raise ValueError('Invalid VFXB next link')
        return pos+nxt
    while start!=NULL:
        start=parse(start,0)
    return {'format':'VFXB','file_bytes':len(data),'sections':sections,'render_status':'UNSUPPORTED: no particle simulation/export adapter'}


def _jsonable(obj):
    if obj is None or isinstance(obj,(str,int,float,bool)):return obj
    if isinstance(obj,bytes):return obj.decode('utf8')
    if isinstance(obj,(list,tuple)):return [_jsonable(x) for x in obj]
    if hasattr(obj,'tolist'):return obj.tolist()
    if hasattr(obj,'__dict__'):return {k:_jsonable(v) for k,v in vars(obj).items()}
    raise TypeError(type(obj).__name__)


def animation_json(source: Path, tool: Path) -> dict:
    # Import generated bindings only, avoiding add-on registration/install side effects.
    sys.path.insert(0,str(tool))
    try:
        module=importlib.import_module('GFLib.Anim.Animation')
        parsed=module.AnimationT.InitFromPackedBuf(bytearray(source.read_bytes()),0)
        result=_jsonable(parsed)
        if not parsed.info or parsed.info.keyFrames<1 or parsed.info.frameRate<1:
            raise ValueError('Invalid animation info')
        result['skeleton_import_status']='SUPPORTED' if parsed.skeleton else 'UNSUPPORTED: this clip has no skeleton; io_scene_gfbanm importer rejects it'
        return result
    finally:sys.path.pop(0)


def run_command(args: list[str], log: list, cwd: Path|None=None, timeout: int=180) -> None:
    try:
        r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        def text_value(value):
            return value.decode('utf-8','replace') if isinstance(value,bytes) else (value or '')
        log.append({'command':args,'cwd':str(cwd) if cwd else None,'returncode':None,'timeout_seconds':timeout,'timed_out':True,'stdout':text_value(exc.stdout),'stderr':text_value(exc.stderr)})
        raise
    log.append({'command':args,'cwd':str(cwd) if cwd else None,'returncode':r.returncode,'timeout_seconds':timeout,'stdout':r.stdout,'stderr':r.stderr})
    if r.returncode:raise RuntimeError(f'Tool exit {r.returncode}: {r.stderr[-500:]}')


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload)&0xffffffff)


def write_png_rgba(output: Path, width: int, height: int, rgba: bytes, srgb: bool=False) -> None:
    if width<1 or height<1 or len(rgba)!=width*height*4:
        raise ValueError('RGBA image dimensions or payload length mismatch')
    rows=b''.join(b'\0'+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    data=b'\x89PNG\r\n\x1a\n'+_png_chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))
    if srgb:data+=_png_chunk(b'sRGB',b'\0')
    data+=_png_chunk(b'IDAT',zlib.compress(rows))+_png_chunk(b'IEND',b'')
    output.write_bytes(data)


def decode_bntx_dds(data: bytes, format_name: str):
    if len(data)<128 or data[:4]!=b'DDS ':
        raise ValueError('BNTX extractor did not produce a DDS image')
    height,width=struct.unpack_from('<II',data,12)
    if not width or not height:raise ValueError('DDS has empty dimensions')
    pixel_format=data[84:88]
    if format_name in {'BC7_UNORM','BC7_SRGB'}:
        if pixel_format!=b'DX10' or len(data)<148:raise ValueError('BC7 DDS lacks DX10 header')
        dxgi=struct.unpack_from('<I',data,128)[0]
        if dxgi!=98:raise ValueError(f'BNTX-Extractor BC7 DDS DXGI format mismatch: {dxgi}')
        payload=data[148:]
        expected=((width+3)//4)*((height+3)//4)*16
        if len(payload)!=expected:raise ValueError(f'BC7 payload size mismatch: {len(payload)} != {expected}')
        try:
            import texture2ddecoder
        except ImportError as exc:
            raise RuntimeError('texture2ddecoder==1.0.6 is required for BC7') from exc
        bgra=texture2ddecoder.decode_bc7(payload,width,height)
        if len(bgra)!=width*height*4:raise ValueError('BC7 decoder returned an unexpected pixel count')
        rgba=bytearray(len(bgra))
        rgba[0::4]=bgra[2::4];rgba[1::4]=bgra[1::4];rgba[2::4]=bgra[0::4];rgba[3::4]=bgra[3::4]
        return width,height,bytes(rgba),{
            'pixel_format':format_name,'decoder':'texture2ddecoder.decode_bc7/1.0.6',
            'channel_mapping':'decoder BGRA reordered to PNG RGBA','color_space':'sRGB' if format_name.endswith('SRGB') else 'linear',
        }
    if format_name=='R8_UNORM':
        if pixel_format!=b'\0\0\0\0' or data[80:84]!=struct.pack('<I',0x00020000):
            raise ValueError('R8 DDS is not the verified luminance layout')
        payload=data[128:];expected=width*height
        if len(payload)!=expected:raise ValueError(f'R8 payload size mismatch: {len(payload)} != {expected}')
        rgba=bytearray(expected*4);rgba[0::4]=payload;rgba[1::4]=payload;rgba[2::4]=payload;rgba[3::4]=b'\xff'*expected
        return width,height,bytes(rgba),{'pixel_format':format_name,'decoder':'BNTX-Extractor deswizzle + RGBA expansion','channel_mapping':'R copied to PNG R/G/B; alpha set opaque','color_space':'linear'}
    if format_name=='R8_G8_UNORM':
        if pixel_format!=b'\0\0\0\0' or data[80:84]!=struct.pack('<I',0x00020001):
            raise ValueError('R8_G8 DDS is not the verified A8L8 layout')
        payload=data[128:];expected=width*height*2
        if len(payload)!=expected:raise ValueError(f'R8_G8 payload size mismatch: {len(payload)} != {expected}')
        rgba=bytearray(width*height*4)
        rgba[0::4]=payload[0::2];rgba[1::4]=payload[1::2];rgba[2::4]=b'\0'*(width*height);rgba[3::4]=b'\xff'*(width*height)
        return width,height,bytes(rgba),{'pixel_format':format_name,'decoder':'BNTX-Extractor deswizzle + RGBA expansion','channel_mapping':'first component to PNG R, second to G, B=0, alpha opaque','color_space':'linear'}
    raise NotImplementedError(f'No validated direct DDS decoder for {format_name}')


def decode_bntx_r16(data: bytes, width: int, height: int) -> bytes:
    """Expand a deswizzled R16_UNORM single channel into opaque PNG RGBA8."""
    if width < 1 or height < 1 or len(data) != width * height * 2:
        raise ValueError('R16 dimensions or deswizzled payload length mismatch')
    values = struct.unpack(f'<{width * height}H', data)
    rgba = bytearray(width * height * 4)
    for index, value in enumerate(values):
        gray = (value * 255 + 32767) // 65535
        offset = index * 4
        rgba[offset:offset + 4] = bytes((gray, gray, gray, 255))
    return bytes(rgba)


def convert_bntx(source: Path, output: Path, root: Path, ffmpeg: Path, log: list) -> dict:
    # Run upstream in a disposable directory. Validate all names before it writes.
    script="""import sys,json;sys.path.insert(0,sys.argv[1]);import bntx_extract as b
from pathlib import Path
textures=b.readBNTX(Path(sys.argv[2]).read_bytes())
sys.path.insert(0,sys.argv[3]);from lgpe_research.assets_decode import safe_name
for t in textures:safe_name(t.name)
metadata=[{'name':t.name,'format':b.formats.get(t.format,'R16_UNORM' if t.format==0x0A01 else 'UNKNOWN'),'format_code':t.format,'width':t.width,'height':t.height,'faces':t.numFaces,'component_selectors':list(t.compSel)} for t in textures]
Path(sys.argv[4]).write_text(json.dumps(metadata),encoding='utf8')
if len(textures)==1 and textures[0].format==0x0A01 and textures[0].numFaces==1:
 t=textures[0];raw=b.swizzle.deswizzle(t.width,t.height,1,1,2,t.tileMode,t.alignment,t.sizeRange,t.data)
 Path(sys.argv[5]).write_bytes(raw[:t.width*t.height*2])
else:b.saveTextures(textures)
"""
    with tempfile.TemporaryDirectory(prefix='bntx-',dir=root/'work') as tmp:
        scratch=Path(tmp)
        metadata_path=scratch/'texture-metadata.json'
        r16_path=scratch/'texture-r16.raw'
        run_command([sys.executable,'-c',script,str(root/'tools/src/BNTX-Extractor'),str(source),str(root/'src'),str(metadata_path),str(r16_path)],log,scratch)
        metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
        if len(metadata)==1 and metadata[0]['format_code']==0x0A01 and metadata[0]['faces']==1 and r16_path.exists():
            temporary=scratch/'out.png'
            rgba=decode_bntx_r16(r16_path.read_bytes(),metadata[0]['width'],metadata[0]['height'])
            write_png_rgba(temporary,metadata[0]['width'],metadata[0]['height'],rgba)
            validate_output(temporary)
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('xb') as f:f.write(temporary.read_bytes())
            return {
                'pixel_format':'R16_UNORM','decoder':'BNTX-Extractor swizzle.deswizzle + R16_UNORM normalization',
                'channel_mapping':'16-bit Red UNORM mapped to 8-bit grayscale; alpha set opaque',
                'color_space':'linear','source_format_code':metadata[0]['format_code'],
                'component_selectors':metadata[0]['component_selectors'],'width':metadata[0]['width'],'height':metadata[0]['height'],
            }
        if len(metadata)!=1:
            raise NotImplementedError(f'Multi-texture BNTX output mapping is not validated ({len(metadata)} textures)')
        if metadata[0]['faces']!=1:
            raise NotImplementedError(f'BNTX texture faces are not validated ({metadata[0]["faces"]} faces)')
        files=list(scratch.glob('*.dds'))
        if len(files)!=1:raise NotImplementedError(f'BNTX-Extractor emitted {len(files)} DDS files for a supported one-texture conversion')
        temporary=scratch/'out.png'
        dds_data=files[0].read_bytes()
        format_name=metadata[0]['format']
        if format_name in {'BC7_UNORM','BC7_SRGB','R8_UNORM','R8_G8_UNORM'}:
            width,height,rgba,conversion=decode_bntx_dds(dds_data,format_name)
            if (width,height)!=(metadata[0]['width'],metadata[0]['height']):raise ValueError('DDS dimensions differ from BNTX metadata')
            write_png_rgba(temporary,width,height,rgba,srgb=format_name=='BC7_SRGB')
            conversion.update({'source_format_code':metadata[0]['format_code'],'component_selectors':metadata[0]['component_selectors']})
            validate_output(temporary)
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('xb') as f:f.write(temporary.read_bytes())
            return conversion
        run_command([str(ffmpeg),'-hide_banner','-n','-i',str(files[0]),'-frames:v','1','-update','1',str(temporary)],log)
        validate_output(temporary)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as f:f.write(temporary.read_bytes())
        return {'pixel_format':format_name,'decoder':'ffmpeg','channel_mapping':'FFmpeg DDS conversion','width':metadata[0]['width'],'height':metadata[0]['height']}


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--execute',action='store_true')
    parser.add_argument('--blender',type=Path,default=Path('D:/Tool/Blender 5.1/blender.exe'))
    parser.add_argument('--ffmpeg',type=Path,default=Path('D:/Tool/ffmpeg-8.0.1-full_build/bin/ffmpeg.exe'))
    args=parser.parse_args(argv);root=args.root.resolve();src=root.parent/'1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1';dest=root/'decoded/1.0.2/romfs'
    records=[]
    git=shutil.which('git') or 'D:/Tool/Git/cmd/git.exe'
    tools={}
    for name in ['BNTX-Extractor','Switch-Toolbox','Pokemon-Switch-Model-Importer-Blender','io_scene_gfbanm','vgmstream']:
        r=subprocess.run([git,'-C',str(root/'tools/src'/name),'rev-parse','HEAD'],capture_output=True,text=True)
        tools[name]={'commit':r.stdout.strip() if r.returncode==0 else 'UNKNOWN'}
    tools['blender']={'executable_sha256':sha256(args.blender)}
    tools['ffmpeg']={'executable_sha256':sha256(args.ffmpeg)}
    tools['vgmstream']['executable_sha256']=sha256(root/'tools/bin/vgmstream-r2168/vgmstream-cli.exe')
    for kind,rel in SAMPLES.items():
        source=src/rel;suffix={'texture':'.png','model':'.glb','animation':'.json','particle':'.json','audio':'.wav'}[kind]
        output=(dest/rel).with_suffix(suffix);record={'kind':kind,'source':rel,'source_sha256':sha256(source),'source_bytes':source.stat().st_size,'output':str(output.relative_to(root)),'commands':[],'tools':tools}
        if not args.execute:record['status']='DRY_RUN';records.append(record);continue
        try:
            output.parent.mkdir(parents=True,exist_ok=True)
            if output.exists():
                record['status']='VALID_EXISTING_UNATTRIBUTED'
            else:
                if kind=='texture':convert_bntx(source,output,root,args.ffmpeg,record['commands'])
                elif kind=='model':
                    with tempfile.TemporaryDirectory(prefix='gfbmdl-',dir=root/'work') as tmp:
                        staging=Path(tmp)/'out.glb'
                        run_command([str(args.blender),'--background','--factory-startup','--python',str(Path(__file__).with_name('assets_blender.py')),'--',str(root),str(source),str(staging)],record['commands'])
                        validate_output(staging)
                        with output.open('xb') as f:f.write(staging.read_bytes())
                elif kind=='audio':
                    with tempfile.TemporaryDirectory(prefix='wem-',dir=root/'work') as tmp:
                        staging=Path(tmp)/'out.wav'
                        run_command([str(root/'tools/bin/vgmstream-r2168/vgmstream-cli.exe'),'-i','-o',str(staging),str(source)],record['commands'])
                        validate_output(staging)
                        with output.open('xb') as f:f.write(staging.read_bytes())
                else:
                    obj=animation_json(source,root/'tools/src/io_scene_gfbanm') if kind=='animation' else ptcl_sections(source.read_bytes())
                    with output.open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
                record['status']='DECODED' if kind not in {'animation','particle'} else 'STRUCTURE_DECODED_RENDER_UNSUPPORTED'
            record['validation']=validate_output(output);record['output_sha256']=sha256(output);record['output_bytes']=output.stat().st_size
            if sha256(source)!=record['source_sha256']:raise ValueError('Source changed during conversion')
        except Exception as exc:record['status']='FAILED';record['error']=str(exc)
        records.append(record)
    if args.execute:
        out=root/'logs/assets_samples.json';out.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
        (root/'logs/assets_samples.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf8')
    print(json.dumps([{k:v for k,v in r.items() if k!='commands'} for r in records],ensure_ascii=False,indent=2))
    return int(any(r['status']=='FAILED' for r in records))

if __name__=='__main__':raise SystemExit(main())
