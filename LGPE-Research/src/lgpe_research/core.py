"""Paths and content metadata. Never modify sources under the game dump."""
from __future__ import annotations
import hashlib
import os
import json
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv

PROJECT = Path(__file__).resolve().parents[2]
NCA = "2b7730a9e56498bbafac2002d4908c6b_NCA"
VERSION = "1.0.2"
EXT_KIND = {
    '.gfpak':'archive-gfpak', '.arc':'archive-unknown',
    '.gfbmdl':'model', '.gfbanm':'animation', '.gfbanmcfg':'animation-config',
    '.gfbcol':'collision', '.gfbmad':'material', '.gfbcam':'camera',
    '.gfbcama':'camera-animation', '.gfbpokecfg':'pokemon-config',
    '.bntx':'texture', '.ptcl':'particle',
    '.bffnt':'font', '.bfotf':'font',
    '.wem':'audio-wwise', '.bnk':'audio-bank', '.wav':'audio-wave',
    '.dat':'data-unknown', '.tbl':'table-unknown', '.bin':'binary-unknown',
    '.amx':'script-unknown', '.webm':'video', '.bseq':'audio-sequence-unknown',
    '.bnsh_vsh':'shader', '.bnsh_fsh':'shader', '.bnsh':'shader',
}
# Only simple signatures; no false-positive parser claims.
MAGIC = [(b'BNTX','BNTX'),(b'GFLXPACK','GFLXPACK'),(b'SARC','SARC'),(b'VFXB','VFXB'),(b'SESD','SESD'),(b'RIFF','RIFF'),
         (b'BKHD','Wwise BKHD'),(b'NSO0','Nintendo NSO'),(b'FRES','BFRES'),
         (b'BNSH','BNSH'),(b'\x1aE\xdf\xa3','EBML/WebM'),(b'AHTB','AHTB'),
         (b'\xd9\x9b\x87\x1a','BFOTF'),(b'\x36\xf8\x1a\x1e','BFOTF'),
         (b'\xf3\x68\xde\xc1','BFOTF'),(b'FFNT','BFFNT')]

def source_dirs(root: Path) -> dict[str,Path]:
    base = root.expanduser().resolve() / VERSION / NCA
    return {'exefs':base / '0','romfs':base / '1'}

def ensure_inside(p:Path, parent:Path) -> Path:
    p = p.resolve()
    parent = parent.resolve()
    try: p.relative_to(parent)
    except ValueError as e: raise ValueError(f"path outside allowed directory: {p}") from e
    return p

def probe(path:Path, full_hash: bool=False) ->dict:
    st=path.stat()
    with path.open('rb') as f:
        hdr=f.read(64)
        if full_hash:
            h=hashlib.sha256();h.update(hdr)
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
            digest=h.hexdigest()
        else:digest=''
    if len(hdr)<8: sig='short/unknown'
    else:sig=next((name for sig,name in MAGIC if hdr.startswith(sig)), 'unidentified')
    return {'size':st.st_size,'header_hex':hdr[:16].hex(),
            'signature':sig,'sha256':digest}

def iter_regular_files(base:Path) ->list[Path]:
    """List regular files without following symlinks, in stable path order."""
    pending=[Path(base)]
    files=[]
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    files.append(Path(entry.path))
    files.sort(key=lambda path:(path.as_posix().casefold(),path.as_posix()))
    return files

def _probe_result(path:Path, full_hash:bool):
    try:
        return probe(path,full_hash),None
    except OSError as error:
        return None,error

def _iter_probed(paths:list[Path], full_hash:bool, workers:int=8):
    """Probe in bounded batches and yield results in the input path order."""
    iterator=iter(paths)
    batch_size=workers*32
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while batch:=list(islice(iterator,batch_size)):
            results=executor.map(lambda path:_probe_result(path,full_hash),batch)
            yield from zip(batch,results)

def snapshot_scan(root:Path, dest:Path, full_hash:bool=False, limit:int=0) -> dict:
    src=source_dirs(root)
    for kind,p in src.items():
        if not p.is_dir(): raise FileNotFoundError(f'{kind} missing: {p}')
    dest.parent.mkdir(parents=True,exist_ok=True)
    headers=['partition','relative_path','suffix','kind','bytes','signature','header_hex','sha256']
    counts=Counter(); anomalies=[]; files=0
    with dest.open('w',encoding='utf-8-sig',newline='') as fd:
        w=csv.DictWriter(fd,fieldnames=headers);w.writeheader()
        def write_probe(partition,base,path,result):
            nonlocal files
            info,error=result
            if error is not None:
                anomalies.append({'file':str(path),'error':str(error)});return
            rel=path.relative_to(base).as_posix();suffix=path.suffix.lower()
            w.writerow({'partition':partition,'relative_path':rel,'suffix':suffix,
                'kind':EXT_KIND.get(suffix,'unknown'), 'bytes':info['size'],
                'signature':info['signature'],'header_hex':info['header_hex'],
                'sha256':info['sha256']})
            counts[suffix or '<no extension>']+=1;files+=1
        for partition,base in src.items():
            paths=iter_regular_files(base)
            if limit:
                for p in paths:
                    if files>=limit:break
                    write_probe(partition,base,p,_probe_result(p,full_hash))
            else:
                for p,result in _iter_probed(paths,full_hash):
                    write_probe(partition,base,p,result)
            if limit and files>=limit:break
    result={'scanned':files,'partitions':{k:str(v) for k,v in src.items()},
            'counts':dict(counts.most_common()),'anomalies':anomalies,'full_hash':full_hash,
            'timestamp_utc':datetime.now(timezone.utc).isoformat()}
    dest.with_suffix('.summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8',newline='\n')
    return result

def decode_destination(partition:str, relative_path:str, new_ext:str, project:Path=PROJECT) ->Path:
    if partition not in ('romfs','exefs'):raise ValueError('partition must be romfs/exefs')
    rel=Path(relative_path.replace('\\','/'))
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:raise ValueError('unsafe relative path')
    if not new_ext.startswith('.') or '/' in new_ext or '\\' in new_ext or new_ext in ('.','..'):
        raise ValueError('new extension must be like .json, .png, .wav')
    path=project/'decoded'/VERSION/partition/rel.with_suffix(new_ext)
    ensure_inside(path,project/'decoded')
    return path

def sha256(p:Path) ->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):h.update(block)
    return h.hexdigest()


def _trusted_decoded_path(value: Path, project: Path) -> Path:
    output = Path(os.path.abspath(os.fspath(value)))
    decoded = Path(os.path.abspath(os.fspath(project / "decoded")))
    try:
        relative = output.relative_to(decoded)
    except ValueError as exc:
        raise ValueError(f"path outside allowed directory: {output}") from exc
    if not relative.parts or ".." in relative.parts:
        raise ValueError(f"path outside allowed directory: {output}")
    return output


def add_receipts(
    project: Path, rows: list[dict], *, trusted_outputs: bool = False,
    replace_source_receipts: bool = False,
):
    """Idempotently upsert verified output receipts and a CSV projection.

    ``replace_source_receipts`` is for one-output-per-source decoders whose
    output mapping changed; it removes stale paths for each incoming
    (method, partition, relative source) identity before inserting its current
    output receipt.
    """
    manifest = project / "manifests" / "outputs.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    by_output = {}

    def key_for(value):
        # Output identity normalization must not perform tens of thousands of
        # filesystem resolutions on remote ROM/output shares.
        return os.path.normcase(os.path.abspath(os.fspath(value)))

    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            old = json.loads(line)
            by_output[key_for(old["output_file"])] = old

    fixed_fields = {
        "timestamp_utc", "version", "source_version", "nca_folder", "partition",
        "relative_source", "source_file", "source_sha256", "output_file",
        "output_sha256", "output_size", "method", "tool_version", "status",
    }

    def source_key(row):
        if not row.get("method") or not row.get("partition") or not row.get("relative_source"):
            return None
        return (
            str(row.get("method", "")),
            str(row.get("partition", "")).casefold(),
            str(row.get("relative_source", "")).replace("\\", "/").casefold(),
        )

    prepared_rows = []
    for original in rows:
        row = dict(original)
        output = (
            _trusted_decoded_path(Path(row["output_file"]), project)
            if trusted_outputs else ensure_inside(Path(row["output_file"]), project / "decoded")
        )
        row["output_file"] = str(output)
        key = key_for(output)
        prepared_rows.append((row, key))

    if replace_source_receipts:
        replacement_sources = set()
        for row, _ in prepared_rows:
            identity = source_key(row)
            if identity is not None:
                replacement_sources.add(identity)
        replacement_outputs = {key for _, key in prepared_rows}
        by_output = {
            key: row for key, row in by_output.items()
            if source_key(row) not in replacement_sources or key in replacement_outputs
        }

    for row, key in prepared_rows:
        old = by_output.get(key)
        if old and all(old.get(field) == row.get(field) for field in (
            "source_sha256", "output_sha256", "method", "tool_version", "status"
        )):
            row["timestamp_utc"] = old.get("timestamp_utc", row.get("timestamp_utc"))
        by_output[key] = row

    ordered = sorted(by_output.values(), key=lambda row: key_for(row["output_file"]))
    temporary = manifest.with_name(manifest.name + ".partial")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered),
        encoding="utf-8",
    )
    temporary.replace(manifest)

    csv_path = project / "manifests" / "outputs.csv"
    csv_temp = csv_path.with_name(csv_path.name + ".partial")
    fields = [
        "timestamp_utc", "version", "partition", "relative_source", "source_file",
        "source_sha256", "output_file", "output_sha256", "output_size", "method",
        "status", "tool_version_json", "command_json", "internal_path",
        "container_index", "details_json",
    ]
    with csv_temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in ordered:
            details = {k: v for k, v in row.items() if k not in fixed_fields | {"command"}}
            writer.writerow({
                **{key: row.get(key, "") for key in fields if key in row},
                "tool_version_json": json.dumps(row.get("tool_version"), ensure_ascii=False, sort_keys=True),
                "command_json": json.dumps(row.get("command"), ensure_ascii=False),
                "internal_path": row.get("internal_path", ""),
                "container_index": row.get("container_index", ""),
                "details_json": json.dumps(details, ensure_ascii=False, sort_keys=True),
            })
    csv_temp.replace(csv_path)
    return len(ordered)


def remove_receipts(project: Path, output_files: set[Path | str], *, method: str | None = None) -> int:
    """Remove receipts for generated outputs that a later verifier invalidated."""
    manifest = project / "manifests" / "outputs.jsonl"
    if not manifest.is_file() or not output_files:
        return 0

    def key_for(value):
        return os.path.normcase(os.path.abspath(os.fspath(value)))

    targets = {key_for(value) for value in output_files}
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    kept = []
    removed = 0
    for row in rows:
        matches = key_for(row.get("output_file", "")) in targets
        if matches and (method is None or row.get("method") == method):
            removed += 1
        else:
            kept.append(row)
    if not removed:
        return 0

    ordered = sorted(kept, key=lambda row: key_for(row["output_file"]))
    temporary = manifest.with_name(manifest.name + ".partial")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered),
        encoding="utf-8",
    )
    temporary.replace(manifest)

    csv_path = project / "manifests" / "outputs.csv"
    csv_temp = csv_path.with_name(csv_path.name + ".partial")
    fields = [
        "timestamp_utc", "version", "partition", "relative_source", "source_file",
        "source_sha256", "output_file", "output_sha256", "output_size", "method",
        "status", "tool_version_json", "command_json", "internal_path",
        "container_index", "details_json",
    ]
    fixed_fields = {
        "timestamp_utc", "version", "source_version", "nca_folder", "partition",
        "relative_source", "source_file", "source_sha256", "output_file",
        "output_sha256", "output_size", "method", "tool_version", "status",
    }
    with csv_temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in ordered:
            details = {k: v for k, v in row.items() if k not in fixed_fields | {"command"}}
            writer.writerow({
                **{key: row.get(key, "") for key in fields if key in row},
                "tool_version_json": json.dumps(row.get("tool_version"), ensure_ascii=False, sort_keys=True),
                "command_json": json.dumps(row.get("command"), ensure_ascii=False),
                "internal_path": row.get("internal_path", ""),
                "container_index": row.get("container_index", ""),
                "details_json": json.dumps(details, ensure_ascii=False, sort_keys=True),
            })
    csv_temp.replace(csv_path)
    return removed


def add_receipt(project: Path, row: dict):
    """Compatibility wrapper for callers adding one output at a time."""
    return add_receipts(project, [row])
