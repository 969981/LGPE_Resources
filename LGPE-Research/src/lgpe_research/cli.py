"""Command line interface for auditable extraction and conversion."""
from __future__ import annotations
import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from .core import PROJECT, VERSION, NCA, decode_destination, source_dirs, ensure_inside, snapshot_scan, probe, sha256, add_receipt
from .tree import export_tree, compare_snapshot_to_scan
from . import assets_decode
from .batch import run_archive_batch, run_gamedata_batch, run_learnset_batch, run_audio_batch, run_wave_batch, read_source_list, register_sample_evidence, verify_samples, verify_outputs, register_gamedata_manifest
from .asset_batch import run_asset_batch
from .bffnt_batch import run_bffnt_batch
from .font_batch import run_font_batch
from .collision_batch import run_collision_batch, verify_collision_outputs
from .bnk_batch import run_bnk_batch
from .bnk_media import run_bnk_media_batch
from .gamemanagergg_worker import run_gamemanagergg_worker
from .wwise_map import build_wwise_event_media_map
from .bseq_wwise_map import build_sequence_wwise_map
from .bseq_demo_audio import write_demo_audio_report
from .coverage import build_coverage
from .runlog import RunJournal
from .amx_catalog import catalog_amx_headers
from .amx_decode import decode_amx
from .bseq_decode import run_bseq_batch
from .encounter_weights import write_encounter_weight_report
from .spawn_rng_crossref import write_spawn_rng_crossref
from .save_api_crossref import build_save_api_crossref_report
from .save_worker_pointer_scan import build_save_worker_pointer_scan_report
from .gfbcol_main_crossref import build_gfbcol_main_crossref_report
from .sort_string_profile import profile_sort_string
from .sort_string_crossref import write_sort_string_message_crossrefs
from .monsname_crossref import build_personal_monsname_crossref
from .nso_relocation_crossref import build_nso_relocation_crossref_report
from .bseq_dispatch_boundary import build_bseq_dispatch_boundary_report
from .capture_getter_crossref import build_capture_getter_crossref_report
from .capture_api_resource_search import build_capture_api_resource_search
from .script_registry_operand_scan import build_script_registry_operand_scan_report


def write_json(path:Path, obj, *, newline=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    serialized = json.dumps(obj, ensure_ascii=False, indent=2)
    if newline is None:
        path.write_text(serialized, encoding='utf-8', newline='\n')
    else:
        path.write_text(serialized + '\n', encoding='utf-8', newline=newline)

def src_path(root:Path, partition:str, relative:str)->Path:
    dirs=source_dirs(root)
    if partition not in dirs:raise ValueError('partition must be romfs/exefs')
    return ensure_inside(dirs[partition] / relative,dirs[partition])

def cmd_doctor(args):
    paths=source_dirs(args.root)
    print('Project:',PROJECT)
    print('Game root:',args.root.resolve())
    for k,v in paths.items(): print(k+':',v,'FOUND' if v.is_dir() else 'MISSING')
    print('uv:',shutil.which('uv') or 'not found on PATH')
    print('git:',shutil.which('git') or 'not found on PATH')
    print('dotnet:',shutil.which('dotnet') or 'not found on PATH')
    print('vgmstream:',shutil.which('vgmstream-cli') or 'not found on PATH')
    print('tree reference:', 'FOUND' if (PROJECT/'docs/source_snapshot/pikachu.1.0.2.txt').is_file() else 'MISSING')
    return 0 if all(p.is_dir() for p in paths.values()) else 2

def cmd_scan(args):
    dest=PROJECT/'manifests/files.csv'
    result=snapshot_scan(args.root,dest,full_hash=args.full_sha256,limit=args.limit)
    print('scanned',result['scanned'],'files ->',dest)
    for e,n in list(result['counts'].items())[:20]: print(e,n)
    return 0 if not result['anomalies'] else 3

def cmd_tree(args):
    p=Path(args.input) if args.input else PROJECT/'docs/source_snapshot/pikachu.1.0.2.txt'
    if not p.exists():raise FileNotFoundError(p)
    dest=PROJECT/'docs/catalog/snapshot_file_inventory.csv'
    summary=export_tree(p,dest)
    write_json(PROJECT/'docs/catalog/snapshot_summary.json',summary)
    print('tree metadata entries',summary['files'],'->',dest)
    return 0

def cmd_profile_sort_string(args):
    romfs = source_dirs(args.root)['romfs']
    result = profile_sort_string(romfs)
    manifest = ensure_inside(args.manifest, PROJECT/'manifests')
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n'
                                for row in result['files']), encoding='utf-8')
    summary_path = manifest.with_suffix('.summary.json')
    write_json(summary_path, result['summary'])
    print(json.dumps({**result['summary'], 'manifest': str(manifest),
                      'summary_file': str(summary_path)}, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_crossref_sort_string(args):
    result = write_sort_string_message_crossrefs(PROJECT, args.root, args.manifest)
    print(json.dumps({**result["summary"], "manifest": str(result["manifest"]),
                      "summary_file": str(result["summary_file"])},
                     ensure_ascii=False, sort_keys=True))
    return 0

def cmd_check_personal_monsname(args):
    result = build_personal_monsname_crossref(PROJECT, args.root)
    output = ensure_inside(args.output, PROJECT/'manifests')
    write_json(output, result)
    print(json.dumps({**result['comparison'], 'report': str(output)},
                     ensure_ascii=False, sort_keys=True))
    return 0 if result['comparison']['same_ordered_prefix'] else 5

METHODS={
 '.gfpak':('P1','pkNX / Switch-Toolbox / new verified GFPAK CLI'),
 '.arc':('P2','signature identification first; do not equate with SARC'),
 '.dat':('P1','only bin/message/*.dat with paired .tbl -> pokedat; others unknown'),
 '.tbl':('P1','paired bin/message tables; no standalone blind conversion'),
 '.bin':('P1','pkNX GG parser for known tables, otherwise schema first'),
 '.gfbmdl':('P2','Switch-Toolbox / Blender LGPE importer'),
 '.bntx':('P2','Switch-Toolbox texture export'),
 '.bfotf':('P2','pinned Switch-Toolbox BFTTF XOR reader -> validated OpenType'),
 '.bffnt':('P2','Pinned Switch-Toolbox NX FFNT section reader; local num_00 sample is structurally decoded, its embedded BNTX sheet exported to PNG; other variants remain UNKNOWN'),
 '.gfbanm':('P2','Blender io_scene_gfbanm'),
 '.wem':('P2','vgmstream-cli'),
 '.wav':('P2','Microsoft ADPCM WAVE -> PCM16 WAVE with vgmstream-cli; native PCM remains UNKNOWN unless a conversion is performed'),
 '.bseq':('P2','SESD structure → JSON via pinned pbseqtool LGPE parser; preserve source bytes; command semantics unverified'),
 '.bnk':('P2','wwiser and vgmstream-cli; may be metadata-only'),
 '.ptcl':('P3','Switch-Toolbox support depends on variant'),
 '.gfbcol':('P2','validate FlatBuffers root envelope; schema and slot meanings remain UNKNOWN'),
 '.amx':('P2','decode compact cells only when the exact LGPE 1.0.2 opcode verifier accepts them'),
}
PATH_METHODS={
 'bin/pokelib/item/battle_pocket.dat':('P1','byte map matches pinned pkNX GameManagerGG Item.PocketBattle for 1,058/1,058 items; main loader/accessor not confirmed -> JSON'),
 'bin/pokelib/item/field_pocket.dat':('P1','exact 1.0.2 byte-map reader; 1,058/1,058 pkNX PocketField cross-checks -> JSON'),
 'bin/pokelib/item/item_hash_to_index.dat':('P1','exact LGPE 1.0.2 main reader confirms count + 0x10 rows; raw fields preserved -> JSON'),
}

def cmd_compare_tree(args):
    result=compare_snapshot_to_scan(args.snapshot,args.scan,VERSION,NCA)
    result.update({'source_version':"Let's Go Pikachu "+VERSION,'nca_folder':NCA,
                   'timestamp_utc':datetime.now(timezone.utc).isoformat()})
    write_json(args.output,result)
    print('matched=',result['matched_paths'],'snapshot_only=',len(result['snapshot_only']),
          'scan_only=',len(result['scan_only']),'->',args.output)
    return 0


def cmd_decode_archives(args):
    summary = run_archive_batch(args.root, PROJECT, args.limit, args.execute)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] and not summary["unsupported"] else 4

def cmd_decode_gamedata(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_gamedata_batch(
        args.root, PROJECT, args.limit, args.execute, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4

def cmd_crosscheck_gamemanagergg(args):
    summary = run_gamemanagergg_worker(args.root, PROJECT)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return summary["exitCode"]

def cmd_decode_learnsets(args):
    summary = run_learnset_batch(args.root, PROJECT, args.limit, args.execute)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed_members"] else 4

def cmd_decode_collisions(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_collision_batch(
        args.root, PROJECT, args.limit, args.execute, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4

def cmd_verify_collisions(args):
    summary = verify_collision_outputs(args.root, PROJECT)
    print(json.dumps({key: value for key, value in summary.items() if key != "errors"}, ensure_ascii=False, sort_keys=True))
    if summary["errors"]:
        print(json.dumps({"errors": summary["errors"][:20]}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 5
    return 0

def cmd_decode_assets(args):
    argv = ["--root", str(PROJECT)]
    if args.execute:
        argv.append("--execute")
    result = assets_decode.main(argv)
    if args.execute:
        print(json.dumps(register_sample_evidence(args.root, PROJECT), ensure_ascii=False, sort_keys=True))
    return result

def cmd_register_samples(args):
    summary = verify_samples(args.root, PROJECT)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["bad"] and not summary["failed_or_unsupported"] else 5

def cmd_plan(args):
    src=PROJECT/'manifests/files.csv'
    if not src.exists():raise FileNotFoundError('run `uv run lgpe scan` first')
    out=PROJECT/'manifests/plan.csv'
    coverage={}
    coverage_src=PROJECT/'manifests/coverage.csv'
    if coverage_src.is_file():
        with coverage_src.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                key=(row.get('partition','').casefold(),row.get('relative_path','').replace('\\','/').casefold())
                coverage[key]=row.get('analysis_status','PENDING')
    with src.open(encoding='utf-8-sig',newline='') as f, out.open('w',encoding='utf-8-sig',newline='') as g:
        r=csv.DictReader(f)
        w=csv.DictWriter(g,fieldnames=['priority','partition','relative_path','extension','method','status'])
        w.writeheader();n=0
        for x in r:
            rel=x['relative_path'].replace('\\','/')
            if rel.casefold().startswith('bin/message/grammar/') and x['suffix'].casefold()=='.dat':
                prio,method=('P1','LGPE grammar structural decoder; exact 1.0.2 path xref, UTF-16LE segments; second header byte/interstitial semantics UNKNOWN')
            else:
                prio,method=PATH_METHODS.get(rel.casefold(),METHODS.get(x['suffix'],('P3','unclassified; probe by signature and related files')))
            w.writerow({'priority':prio,'partition':x['partition'],'relative_path':x['relative_path'],
                        'extension':x['suffix'],'method':method,
                        'status':coverage.get((x['partition'].casefold(),rel.casefold()),'PENDING')});n+=1
    print('planned',n,'entries ->',out)
    return 0

def record_output(args,source:Path,target:Path,method:str):
    add_receipt(PROJECT,{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'version':VERSION,'partition':args.partition,'relative_source':args.source,
        'source_file':str(source),'source_sha256':sha256(source),
        'output_file':str(target),'output_sha256':sha256(target),
        'output_size':target.stat().st_size,'method':method,
        'tool_version':getattr(args,'tool_version','unspecified')})

def copy_safe(source:Path,target:Path,overwrite:bool):
    if not source.is_file():raise FileNotFoundError(source)
    if target.exists() and not overwrite:raise FileExistsError(f'{target} exists; use --overwrite explicitly')
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+'.lgpe.partial')
    if temp.exists(): raise FileExistsError(f'remove stale partial manually: {temp}')
    try:
        with source.open('rb') as inp, temp.open('xb') as out:shutil.copyfileobj(inp,out,1024*1024)
        temp.replace(target)
    finally:
        if temp.exists():temp.unlink()

def cmd_ingest(args):
    source=src_path(args.root,args.partition,args.source)
    if not source.is_file():raise FileNotFoundError(source)
    export=Path(args.export).expanduser().resolve()
    target=decode_destination(args.partition,args.source,args.suffix,PROJECT)
    if target.resolve()==source.resolve():raise ValueError('refuse source overwrite')
    if args.dry_run:
        print('DRY-RUN',export,'=>',target);return 0
    copy_safe(export,target,args.overwrite)
    record_output(args,source,target,'ingest: '+args.method)
    print('INGESTED',target);return 0

def cmd_ingest_container(args):
    source=src_path(args.root,args.partition,args.source)
    if not source.is_file():raise FileNotFoundError(source)
    folder=Path(args.export_dir).expanduser().resolve()
    if not folder.is_dir():raise NotADirectoryError(folder)
    # A named folder makes many-to-one conversion explicit and prevents filename collisions.
    rel=Path(args.source.replace('\\','/'))
    if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe relative path')
    outbase=PROJECT/'decoded'/VERSION/args.partition/rel.parent/(rel.name+'.contents')
    ensure_inside(outbase,PROJECT/'decoded')
    copied=[]
    for candidate in sorted(folder.rglob('*')):
        if not candidate.is_file() or candidate.is_symlink():continue
        internal=candidate.relative_to(folder)
        target=outbase/internal
        ensure_inside(target,outbase)
        if args.max_files and len(copied)>=args.max_files:break
        if args.dry_run:
            print('DRY-RUN',candidate,'=>',target);copied.append(str(target));continue
        copy_safe(candidate,target,args.overwrite)
        add_receipt(PROJECT,{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'version':VERSION,'partition':args.partition,'relative_source':args.source,
            'source_file':str(source),'source_sha256':sha256(source),
            'output_file':str(target),'output_sha256':sha256(target),'output_size':target.stat().st_size,
            'method':'container-ingest: '+args.method,'internal_path':internal.as_posix(),
            'tool_version':args.tool_version})
        copied.append(str(target))
    print('container',source.name,'entries:',len(copied));return 0

def cmd_register_gamedata(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = register_gamedata_manifest(args.root, PROJECT, only_sources=only_sources)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 5


def cmd_coverage(args):
    summary = build_coverage(PROJECT)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_amx_catalog(args):
    summary = catalog_amx_headers(args.root, PROJECT, limit=args.limit)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4


def cmd_decode_amx(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = decode_amx(
        args.root, PROJECT, args.limit, args.execute, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary.get("failed", 0) else 4

def cmd_decode_sequences(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_bseq_batch(
        args.root, PROJECT, args.limit, args.execute, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4


def cmd_retry_failed(args):
    path = PROJECT / "manifests" / "failures.jsonl"
    if not path.is_file():
        print(json.dumps({"failures": 0, "retried": {}}, sort_keys=True))
        return 0
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    allowed = {"FAILED"}
    if args.include_unsupported:
        allowed.add("UNSUPPORTED")
    selected = {}
    for row in rows:
        domain = str(row.get("domain", ""))
        if row.get("status") not in allowed or not row.get("source"):
            continue
        if args.domain != "all" and domain != args.domain:
            continue
        selected.setdefault(domain, set()).add(row["source"])
    summaries = {}
    for domain, sources in selected.items():
        if domain == "archive":
            summaries[domain] = run_archive_batch(args.root, PROJECT, 0, args.execute, only_sources=sources)
        elif domain == "gamedata":
            summaries[domain] = run_gamedata_batch(args.root, PROJECT, 0, args.execute, only_sources=sources)
        elif domain == "learnset":
            summaries[domain] = run_learnset_batch(args.root, PROJECT, 0, args.execute, only_sources=sources)
        elif domain == "audio":
            summaries[domain] = run_audio_batch(
                args.root, PROJECT, 0, args.execute, args.vgmstream,
                timeout=args.timeout, only_sources=sources,
            )
        elif domain == "wave":
            summaries[domain] = run_wave_batch(
                args.root, PROJECT, 0, args.execute, args.vgmstream,
                timeout=args.timeout, only_sources=sources,
            )
        elif domain == "bnk":
            summaries[domain] = run_bnk_batch(
                args.root, PROJECT, 0, args.execute,
                timeout=args.timeout, only_sources=sources,
            )
        elif domain == "font":
            summaries[domain] = run_font_batch(
                args.root, PROJECT, 0, args.execute, only_sources=sources,
            )
        elif domain == "bffnt":
            summaries[domain] = run_bffnt_batch(
                args.root, PROJECT, 0, args.execute, ffmpeg=args.ffmpeg,
                only_sources=sources,
            )
        elif domain in {"texture", "model", "animation", "particle"}:
            summaries[domain] = run_asset_batch(
                domain, args.root, PROJECT, 0, args.execute,
                blender=args.blender, ffmpeg=args.ffmpeg, only_sources=sources,
                timeout=args.timeout,
            )
        elif domain == "collision":
            summaries[domain] = run_collision_batch(
                args.root, PROJECT, 0, args.execute, only_sources=sources,
            )
        elif domain == "amx":
            summaries[domain] = decode_amx(
                args.root, PROJECT, 0, args.execute, only_sources=sources,
            )
        elif domain == "bseq":
            summaries[domain] = run_bseq_batch(
                args.root, PROJECT, 0, args.execute, only_sources=sources,
            )
    summary = {
        "failure_rows_before": len(rows),
        "sources_selected": {key: sorted(value) for key, value in selected.items()},
        "execute": args.execute,
        "retried": summaries,
    }
    summary["coverage"] = build_coverage(PROJECT)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if all(value.get("failed", 0) == 0 for value in summaries.values()) else 4


def cmd_decode_asset_type(args):
    only_sources = read_source_list(args.sources_file) if getattr(args, "sources_file", None) else None
    summary = run_asset_batch(
        args.kind, args.root, PROJECT, args.limit, args.execute,
        blender=getattr(args, "blender", None),
        ffmpeg=getattr(args, "ffmpeg", None),
        only_sources=only_sources,
        timeout=getattr(args, "timeout", 180),
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4


def cmd_decode_fonts(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_font_batch(
        args.root, PROJECT, args.limit, args.execute, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4


def cmd_decode_bffnt(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_bffnt_batch(
        args.root, PROJECT, args.limit, args.execute,
        ffmpeg=args.ffmpeg, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4


def cmd_run(args):
    scan_path = PROJECT / "manifests" / "files.csv"
    scan = snapshot_scan(args.root, scan_path, full_hash=args.full_sha256)
    cmd_tree(argparse.Namespace(input=None))
    cmd_compare_tree(argparse.Namespace(
        snapshot=PROJECT / "docs" / "catalog" / "snapshot_file_inventory.csv",
        scan=scan_path,
        output=PROJECT / "docs" / "catalog" / "scan_snapshot_diff.json",
    ))
    cmd_plan(argparse.Namespace())
    tree_diff = json.loads((PROJECT / "docs" / "catalog" / "scan_snapshot_diff.json").read_text(encoding="utf-8"))
    args._journal.checkpoint("inventory", {
        "scan": {"scanned": scan["scanned"], "anomalies": len(scan["anomalies"])},
        "tree_diff": {
            "matched_paths": tree_diff.get("matched_paths"),
            "snapshot_only": len(tree_diff.get("snapshot_only", [])),
            "scan_only": len(tree_diff.get("scan_only", [])),
        },
        "plan_entries": scan["scanned"],
    })
    summary = {
        "scan": {"scanned": scan["scanned"], "anomalies": len(scan["anomalies"])},
        "limit": args.limit,
        "execute": args.execute,
    }
    summary["archives"] = run_archive_batch(args.root, PROJECT, args.limit, args.execute)
    args._journal.checkpoint("archives", summary["archives"])
    archive_catalog = PROJECT / "manifests" / "archives.jsonl"
    archive_rows = [
        json.loads(line) for line in archive_catalog.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if archive_catalog.is_file() else []
    learnset_archive = next((
        row for row in archive_rows
        if str(row.get("source", "")).casefold() == "bin/archive/waza_oboe.gfpak"
    ), None)
    if args.limit and (learnset_archive is None or learnset_archive.get("status") not in {"DECODED", "DECODED_EXISTING_VERIFIED"}):
        summary["learnsets"] = {
            "archive": "bin/archive/waza_oboe.gfpak", "decoded_members": 0,
            "failed": 0, "failed_members": 0,
            "pending_members": int(learnset_archive.get("member_count", 0)) if learnset_archive else 0,
            "unknown_members": 0, "selected_members": 0,
            "execute": args.execute, "skipped": True,
            "reason": "source archive was not selected or extracted in this bounded run",
        }
    else:
        summary["learnsets"] = run_learnset_batch(args.root, PROJECT, args.limit, args.execute)
    args._journal.checkpoint("learnsets", summary["learnsets"])
    summary["gamedata"] = run_gamedata_batch(args.root, PROJECT, args.limit, args.execute)
    args._journal.checkpoint("gamedata", summary["gamedata"])
    summary["bnk"] = run_bnk_batch(
        args.root, PROJECT, args.limit, args.execute, timeout=args.timeout,
    )
    args._journal.checkpoint("bnk", summary["bnk"])
    for kind in ("texture", "model", "animation", "particle"):
        summary[kind] = run_asset_batch(
            kind, args.root, PROJECT, args.limit, args.execute,
            blender=args.blender, ffmpeg=args.ffmpeg, timeout=args.timeout,
        )
        args._journal.checkpoint(kind, summary[kind])
    summary["font"] = run_font_batch(args.root, PROJECT, args.limit, args.execute)
    args._journal.checkpoint("font", summary["font"])
    summary["bffnt"] = run_bffnt_batch(
        args.root, PROJECT, args.limit, args.execute, ffmpeg=args.ffmpeg,
    )
    args._journal.checkpoint("bffnt", summary["bffnt"])
    summary["collision"] = run_collision_batch(
        args.root, PROJECT, args.limit, args.execute,
    )
    args._journal.checkpoint("collision", summary["collision"])
    summary["audio"] = run_audio_batch(
        args.root, PROJECT, args.limit, args.execute, tool=args.vgmstream,
        timeout=args.timeout,
    )
    args._journal.checkpoint("audio", summary["audio"])
    summary["wave"] = run_wave_batch(
        args.root, PROJECT, args.limit, args.execute, tool=args.vgmstream,
        timeout=args.timeout,
    )
    args._journal.checkpoint("wave", summary["wave"])
    summary["amx"] = catalog_amx_headers(args.root, PROJECT, limit=args.limit)
    args._journal.checkpoint("amx", summary["amx"])
    summary["amx_decode"] = decode_amx(args.root, PROJECT, args.limit, args.execute)
    args._journal.checkpoint("amx_decode", summary["amx_decode"])
    summary["sequences"] = run_bseq_batch(args.root, PROJECT, args.limit, args.execute)
    args._journal.checkpoint("sequences", summary["sequences"])
    if args.execute and args.limit == 0:
        summary["bnk_media"] = run_bnk_media_batch(
            args.root, PROJECT, args.limit, args.execute,
            tool=args.vgmstream, timeout=args.timeout,
        )
        args._journal.checkpoint("bnk_media", summary["bnk_media"])
        summary["audio_event_map"] = build_wwise_event_media_map(args.root, PROJECT)
        args._journal.checkpoint("audio_event_map", summary["audio_event_map"])
        summary["sequence_audio_map"] = build_sequence_wwise_map(args.root, PROJECT)
        args._journal.checkpoint("sequence_audio_map", summary["sequence_audio_map"])
        summary["demo_audio_map"] = write_demo_audio_report(args.root, PROJECT)
        args._journal.checkpoint("demo_audio_map", summary["demo_audio_map"])
    if args.execute:
        summary["sample_registration"] = register_sample_evidence(args.root, PROJECT)
        args._journal.checkpoint("sample_registration", summary["sample_registration"])
        summary["verification"] = verify_outputs(PROJECT, root=args.root)
        args._journal.checkpoint("verification", summary["verification"])
    summary["coverage"] = build_coverage(PROJECT)
    args._journal.checkpoint("coverage", summary["coverage"])
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    failed = sum(
        sum(int(value.get(key, 0)) for key in (
            "failed", "failed_members", "banks_failed", "banksFailed",
            "pending", "pending_members", "failedSequences", "pendingSequences",
        ))
        for key, value in summary.items() if isinstance(value, dict)
    )
    bad = summary.get("verification", {}).get("bad", 0)
    return 0 if not failed and not bad else 5


def cmd_audio(args):
    if args.execute:
        register_sample_evidence(args.root, PROJECT)
    summary = run_audio_batch(
        args.root, PROJECT, args.limit, args.execute,
        args.vgmstream, args.overwrite, args.timeout,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4

def cmd_wave(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_wave_batch(
        args.root, PROJECT, args.limit, args.execute, args.vgmstream,
        args.overwrite, args.timeout, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4

def cmd_decode_banks(args):
    summary = run_bnk_batch(
        args.root, PROJECT, args.limit, args.execute, timeout=args.timeout,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["failed"] else 4

def cmd_map_audio_events(args):
    summary = build_wwise_event_media_map(args.root, PROJECT)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["banksFailed"] == 0 else 4

def cmd_map_sequence_audio(args):
    summary = build_sequence_wwise_map(args.root, PROJECT)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "ANALYZED" else 4

def cmd_map_demo_audio(args):
    summary = write_demo_audio_report(args.root, PROJECT, dry_run=args.dry_run)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_encounter_weights(args):
    summary = write_encounter_weight_report(
        PROJECT, args.root,
        args.csv or PROJECT / "manifests" / "encounter-weight-intervals.csv",
        args.json or PROJECT / "manifests" / "encounter-weight-intervals.json",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_spawn_rng_crossref(args):
    output = args.output or PROJECT / "manifests" / "spawn_rng-value-crossref.json"
    summary = write_spawn_rng_crossref(PROJECT, args.root, output)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_bseq_dispatch_boundary(args):
    trace_log = args.trace_log or PROJECT / "logs" / "ghidra-bseq-dispatch-boundary-v1-evidence.tsv"
    output = ensure_inside(
        args.output or PROJECT / "manifests" / "bseq-dispatch-boundary.json",
        PROJECT / "manifests",
    )
    script = PROJECT / "scripts" / "ghidra" / "InspectBseqDispatchBoundary.java"
    wrapper = PROJECT / "scripts" / "ghidra" / "Run-InspectBseqDispatchBoundary.ps1"
    report = build_bseq_dispatch_boundary_report(
        trace_log.read_text(encoding="utf-8"),
        script_sha256=sha256(script),
        wrapper_sha256=sha256(wrapper),
        log_sha256=sha256(trace_log),
    )
    try:
        trace_label = trace_log.resolve().relative_to(PROJECT.resolve()).as_posix()
    except ValueError:
        trace_label = str(trace_log)
    report["provenance"]["normalized_evidence_log"] = trace_label
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["build"]["main_sha256"],
        "target_instruction": report["target_probe"]["instruction"],
        "scanned_extra_slots": report["extended_pointer_scan"]["inspected_slots"],
        "extra_executable_targets": report["extended_pointer_scan"]["executable_targets"],
        "full_table_length_proven": report["extended_pointer_scan"]["full_table_length_proven"],
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_save_api_crossref(args):
    trace_log = args.trace_log or PROJECT / "logs" / "ghidra-save-api-references-v1-script.log"
    output = args.output or PROJECT / "manifests" / "save-api-crossref.json"
    script = PROJECT / "scripts" / "ghidra" / "InspectSaveApiReferences.java"
    wrapper = PROJECT / "scripts" / "ghidra" / "Run-InspectSaveApiReferences.ps1"
    report = build_save_api_crossref_report(
        trace_log.read_text(encoding="utf-8"),
        trace_script_sha256=sha256(script),
        trace_wrapper_sha256=sha256(wrapper),
    )
    try:
        trace_label = trace_log.resolve().relative_to(PROJECT.resolve()).as_posix()
    except ValueError:
        trace_label = str(trace_log)
    report["trace"]["log"] = trace_label
    report["trace"]["log_sha256"] = sha256(trace_log)
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["main"]["sha256"],
        "save_worker_incoming_references": report["save_worker"]["incoming_references"],
        "filesystem_operation_callers": report["counts"]["filesystem_operation_parents"],
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_capture_getter_crossref(args):
    trace_log = args.trace_log or PROJECT / "logs" / "ghidra-capture-getter-callers-v1.stdout.log"
    output = ensure_inside(
        args.output or PROJECT / "manifests" / "capture-getter-callers.json",
        PROJECT / "manifests",
    )
    script = PROJECT / "scripts" / "ghidra" / "InspectCaptureGetterCallers.java"
    wrapper = PROJECT / "scripts" / "ghidra" / "Run-InspectCaptureGetterCallers.ps1"
    report = build_capture_getter_crossref_report(
        trace_log.read_text(encoding="utf-8"),
        script_sha256=sha256(script),
        wrapper_sha256=sha256(wrapper),
        log_sha256=sha256(trace_log),
    )
    try:
        trace_label = trace_log.resolve().relative_to(PROJECT.resolve()).as_posix()
    except ValueError:
        trace_label = str(trace_log)
    report["trace"]["evidence_log"] = trace_label
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["build"]["main_sha256"],
        "shared_handler_callers": report["shared_handler"]["direct_incoming_reference_count"],
        "handler_specific_to_capture": report["interpretation"]["handler_specific_to_capture"],
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_capture_api_resource_search(args):
    paths = source_dirs(args.root)
    main_path = paths["exefs"] / "main"
    output = ensure_inside(
        args.output or PROJECT / "manifests" / "capture-api-resource-search.json",
        PROJECT / "manifests",
    )
    report = build_capture_api_resource_search(
        PROJECT,
        paths["romfs"],
        main_sha256=sha256(main_path),
    )
    try:
        report["build"]["main_path"] = main_path.resolve().relative_to(args.root.resolve()).as_posix()
    except ValueError:
        report["build"]["main_path"] = str(main_path.resolve())
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["build"]["main_sha256"],
        "files_scanned": report["search"]["files_scanned"],
        "bytes_scanned": report["search"]["bytes_scanned"],
        "literal_occurrences": sum(
            len(match["literal_occurrences"]) for match in report["matches"]
        ),
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_script_registry_operand_scan(args):
    paths = source_dirs(args.root)
    main_path = paths["exefs"] / "main"
    trace_log = args.trace_log or PROJECT / "logs" / "ghidra-script-registry-operands-v1.stdout.log"
    output = ensure_inside(
        args.output or PROJECT / "manifests" / "script-registry-operand-scan.json",
        PROJECT / "manifests",
    )
    report = build_script_registry_operand_scan_report(
        PROJECT,
        trace_log,
        main_sha256=sha256(main_path),
    )
    try:
        report["build"]["main_path"] = main_path.resolve().relative_to(args.root.resolve()).as_posix()
    except ValueError:
        report["build"]["main_path"] = str(main_path.resolve())
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["build"]["main_sha256"],
        "instruction_count": report["trace"]["instruction_count"],
        "operand_hits": report["trace"]["operand_hit_count"],
        "owners": report["trace"]["owner_count"],
        "decompile_failures": report["trace"]["decompile_failures"],
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_save_worker_pointer_scan(args):
    trace_log = args.trace_log or PROJECT / "logs" / "ghidra-save-worker-pointers-v1-script.log"
    output = args.output or PROJECT / "manifests" / "save-worker-pointer-scan.json"
    script = PROJECT / "scripts" / "ghidra" / "ScanSaveWorkerPointers.java"
    wrapper = PROJECT / "scripts" / "ghidra" / "Run-ScanSaveWorkerPointers.ps1"
    report = build_save_worker_pointer_scan_report(
        trace_log.read_text(encoding="utf-8"),
        trace_script_sha256=sha256(script),
        trace_wrapper_sha256=sha256(wrapper),
        trace_log_sha256=sha256(trace_log),
    )
    try:
        trace_label = trace_log.resolve().relative_to(PROJECT.resolve()).as_posix()
    except ValueError:
        trace_label = str(trace_log)
    report["trace"]["log"] = trace_label
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["main"]["sha256"],
        "absolute_qword_matches": report["scan"]["absolute_qword_matches"],
        "image_offset_dword_matches": report["scan"]["image_offset_dword_matches"],
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_nso_relocation_crossref(args):
    output = ensure_inside(
        args.output or PROJECT / "manifests" / "nso-relocation-crossref.json",
        PROJECT / "manifests",
    )
    report = build_nso_relocation_crossref_report(PROJECT, args.root)
    write_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "output": str(output),
        "main_sha256": report["main"]["sha256"],
        "relative_count": report["relocations"]["relative_count"],
        "dispatcher_body_matches": next(
            row["match_count"] for row in report["queries"]
            if row["id"] == "spawn_dispatcher_body"
        ),
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_crossref_gfbcol_main(args):
    output = ensure_inside(
        args.output or PROJECT / "manifests" / "gfbcol-main-token-crossref.json",
        PROJECT / "manifests",
    )
    report = build_gfbcol_main_crossref_report(PROJECT, args.root)
    write_json(output, report, newline='\r\n')
    print(json.dumps({
        "status": report["analysis_status"],
        "output": str(output),
        **report["summary"],
        "gfbcol_sources": report["gfbcol_probe"]["sources_read"],
        "main_sha256": report["main"]["sha256"],
        "owner_candidate": report["ghidra_owner_candidate_trace"]["summary"]["entry"],
        "owner_candidate_calls": report["ghidra_owner_candidate_trace"]["summary"]["call_sites"],
    }, ensure_ascii=False, sort_keys=True))
    return 0

def cmd_decode_bnk_media(args):
    only_sources = read_source_list(args.sources_file) if args.sources_file else None
    summary = run_bnk_media_batch(
        args.root, PROJECT, args.limit, args.execute,
        tool=args.vgmstream, timeout=args.timeout, only_sources=only_sources,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if not summary["banks_failed"] and not summary["failed_members"] else 4


def cmd_verify(args):
    if args.sources_file:
        selected_sources = read_source_list(args.sources_file)
        selected_names = {source.replace("\\", "/").casefold() for source in selected_sources}
        summary = verify_outputs(PROJECT, only_sources=selected_sources, root=args.root)
        failure_path = PROJECT / "manifests" / "failures.jsonl"
        selected_failures = [
            json.loads(line)
            for line in failure_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
            and str(json.loads(line).get("source", "")).replace("\\", "/").casefold() in selected_names
        ] if failure_path.is_file() else []
        summary["failed"] = sum(row.get("status") == "FAILED" for row in selected_failures)
        summary["unsupported"] = sum(row.get("status") == "UNSUPPORTED" for row in selected_failures)
        summary["failed_or_unsupported"] = len(selected_failures)
    else:
        summary = verify_samples(args.root, PROJECT)
    journal = getattr(args, "_journal", None)
    if journal is not None:
        journal.checkpoint("verification", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    failed_count = summary.get("failed", summary.get("failed_or_unsupported", 0))
    unclassified_count = summary.get("unclassified_failure_statuses", 0)
    return 0 if not summary["bad"] and not failed_count and not unclassified_count else 5


def main(argv=None)->int:
    a=argparse.ArgumentParser(prog='lgpe',description='LGPE 1.0.2 file research, never writes original dump')
    sub=a.add_subparsers(dest='command',required=True)
    def base(sp):sp.add_argument('--root',type=Path,default=PROJECT.parent,help='game directory (parent of 1.0.2)')
    sp=sub.add_parser('doctor');base(sp);sp.set_defaults(func=cmd_doctor)
    sp=sub.add_parser('scan');base(sp);sp.add_argument('--full-sha256',action='store_true');sp.add_argument('--limit',type=int,default=0);sp.set_defaults(func=cmd_scan)
    sp=sub.add_parser('tree-catalog');sp.add_argument('--input');sp.set_defaults(func=cmd_tree)
    sp=sub.add_parser('profile-sort-string',help='record read-only byte profiles for localized sort_string DAT candidates')
    base(sp);sp.add_argument('--manifest',type=Path,default=PROJECT/'manifests/sort_string_candidates.jsonl')
    sp.set_defaults(func=cmd_profile_sort_string)
    sp=sub.add_parser('crossref-sort-string',help='hash-check localized sort_table candidates against decoded message lines without decoding the candidates')
    base(sp);sp.add_argument('--manifest',type=Path,default=PROJECT/'manifests/sort_string_message_crossrefs.jsonl')
    sp.set_defaults(func=cmd_crossref_sort_string)
    sp=sub.add_parser('check-personal-monsname',help='rehash and compare the unlabeled personal text against decoded JPN common monsname by index')
    base(sp);sp.add_argument('--output',type=Path,default=PROJECT/'manifests/personal_monsname_crossref.json')
    sp.set_defaults(func=cmd_check_personal_monsname)
    sp=sub.add_parser('compare-tree',help='compare snapshot names with the real scan manifest')
    sp.add_argument('--snapshot',type=Path,default=PROJECT/'docs/catalog/snapshot_file_inventory.csv')
    sp.add_argument('--scan',type=Path,default=PROJECT/'manifests/files.csv')
    sp.add_argument('--output',type=Path,default=PROJECT/'docs/catalog/scan_snapshot_diff.json')
    sp.set_defaults(func=cmd_compare_tree)

    sp=sub.add_parser('plan');sp.set_defaults(func=cmd_plan)
    def source_args(sp):
        base(sp);sp.add_argument('--partition',choices=['romfs','exefs'],default='romfs')
        sp.add_argument('--source',required=True,help='source relative to 1 (RomFS) or 0 (ExeFS)')
        sp.add_argument('--method',required=True,help='producer and exact version/technique')
        sp.add_argument('--tool-version',default='unspecified');sp.add_argument('--overwrite',action='store_true');sp.add_argument('--dry-run',action='store_true')
    sp=sub.add_parser('ingest',help='one-to-one output: foo.dat -> foo.json');source_args(sp)
    sp.add_argument('--export',required=True);sp.add_argument('--suffix',required=True);sp.set_defaults(func=cmd_ingest)
    sp=sub.add_parser('ingest-container',help='one-to-many: foo.gfpak -> foo.gfpak.contents/..');source_args(sp)
    sp.add_argument('--export-dir',required=True);sp.add_argument('--max-files',type=int,default=0);sp.set_defaults(func=cmd_ingest_container)
    sp=sub.add_parser('decode-archives',help='bounded GFPAK/SARC batch; --limit 0 means all compatible inputs')
    base(sp);sp.add_argument('--limit',type=int,default=20);sp.add_argument('--execute',action='store_true')
    sp.set_defaults(func=cmd_decode_archives)
    sp=sub.add_parser('decode-gamedata',help='decode verified message, personal, localized sort, zukan-sort, item, trainer, evolution, move, and encounter data')
    base(sp);sp.add_argument('--limit',type=int,default=20);sp.add_argument('--execute',action='store_true')
    sp.add_argument('--sources-file',type=Path,help='decode only listed ROMFS-relative source paths (one per line; # comments allowed)')
    sp.set_defaults(func=cmd_decode_gamedata)
    sp=sub.add_parser('crosscheck-gamemanagergg',help='run pinned pkNX GameManagerGG in a read-only .NET worker and verify source hashes')
    base(sp);sp.set_defaults(func=cmd_crosscheck_gamemanagergg)
    sp=sub.add_parser('decode-learnsets',help='decode the extracted waza_oboe GFPAK members as pkNX Learnset6 records')
    base(sp);sp.add_argument('--limit',type=int,default=20);sp.add_argument('--execute',action='store_true')
    sp.set_defaults(func=cmd_decode_learnsets)
    sp=sub.add_parser('decode-collisions',help='inspect the generic GFBCol root table while retaining UNKNOWN schema status')
    base(sp);sp.add_argument('--limit',type=int,default=20);sp.add_argument('--execute',action='store_true')
    sp.add_argument('--sources-file',type=Path,help='inspect only listed ROMFS-relative source paths')
    sp.set_defaults(func=cmd_decode_collisions)
    sp=sub.add_parser('verify-collisions',help='rehash and verify every GFBCol root-structure JSON output')
    base(sp);sp.set_defaults(func=cmd_verify_collisions)
    sp=sub.add_parser("decode-banks",help="decode Wwise BNK metadata to mirrored XML with wwiser")
    base(sp);sp.add_argument("--limit",type=int,default=20);sp.add_argument("--execute",action="store_true")
    sp.add_argument("--timeout",type=int,default=300);sp.set_defaults(func=cmd_decode_banks)
    sp=sub.add_parser("decode-sequences",help="decode LGPE SESD .bseq structure to JSON while preserving source bytes")
    base(sp);sp.add_argument("--limit",type=int,default=20);sp.add_argument("--execute",action="store_true")
    sp.add_argument("--sources-file",type=Path,help="process only listed RomFS-relative .bseq paths")
    sp.set_defaults(func=cmd_decode_sequences)
    sp=sub.add_parser("map-audio-events",help="map wwiser event/action graphs to referenced WEM files without assigning event names")
    base(sp);sp.set_defaults(func=cmd_map_audio_events)
    sp=sub.add_parser("map-sequence-audio",help="cross-reference BSEQ parser literals to Wwise FNV-1 event IDs with bank and hash receipts")
    base(sp);sp.set_defaults(func=cmd_map_sequence_audio)
    sp=sub.add_parser("map-demo-audio",help="inspect raw unsupported demo BSEQ literals against verified Wwise HIRC events; retain UNKNOWN semantics")
    base(sp);sp.add_argument("--dry-run",action="store_true");sp.set_defaults(func=cmd_map_demo_audio)
    sp=sub.add_parser("encounter-weights",help="derive exact-source, static-candidate encounter roll intervals with FlatBuffer byte offsets")
    base(sp)
    sp.add_argument('--csv',type=Path,help='CSV output path (default: manifests/encounter-weight-intervals.csv)')
    sp.add_argument('--json',type=Path,help='JSON summary path (default: manifests/encounter-weight-intervals.json)')
    sp.set_defaults(func=cmd_encounter_weights)
    sp=sub.add_parser("spawn-rng-crossref",help="hash-check LGPE spawn RNG and event-record values against pinned sources and local data without assigning opaque semantics")
    base(sp);sp.add_argument('--output',type=Path,help='JSON output path (default: manifests/spawn_rng-value-crossref.json)')
    sp.set_defaults(func=cmd_spawn_rng_crossref)
    sp=sub.add_parser("bseq-dispatch-boundary",help="validate exact-main BSEQ target bytes and extended pointer observations while preserving UNKNOWN table length")
    sp.add_argument('--trace-log',type=Path,help='normalized read-only Ghidra evidence records (default: logs/ghidra-bseq-dispatch-boundary-v1-evidence.tsv)')
    sp.add_argument('--output',type=Path,help='JSON output path (default: manifests/bseq-dispatch-boundary.json)')
    sp.set_defaults(func=cmd_bseq_dispatch_boundary)
    sp=sub.add_parser("save-api-crossref",help="build a version-pinned JSON manifest from the latest read-only Ghidra save/filesystem API trace")
    sp.add_argument('--trace-log',type=Path,help='Ghidra script log (default: logs/ghidra-save-api-references-v1-script.log)')
    sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/save-api-crossref.json)')
    sp.set_defaults(func=cmd_save_api_crossref)
    sp=sub.add_parser("capture-getter-crossref",help="validate exact-build read-only capture-getter caller xrefs without assigning capture semantics")
    sp.add_argument('--trace-log',type=Path,help='Ghidra output log (default: logs/ghidra-capture-getter-callers-v1.stdout.log)')
    sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/capture-getter-callers.json)')
    sp.set_defaults(func=cmd_capture_getter_crossref)
    sp=sub.add_parser("capture-api-resource-search",help="search exact LGPE script/message resources for literal capture API names; does not infer calls from strings")
    base(sp);sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/capture-api-resource-search.json)')
    sp.set_defaults(func=cmd_capture_api_resource_search)
    sp=sub.add_parser("script-registry-operand-scan",help="validate a read-only exact-build Ghidra scan for explicit script-registry page operands")
    base(sp);sp.add_argument('--trace-log',type=Path,help='Ghidra stdout log (default: logs/ghidra-script-registry-operands-v1.stdout.log)');sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/script-registry-operand-scan.json)')
    sp.set_defaults(func=cmd_script_registry_operand_scan)
    sp=sub.add_parser("save-worker-pointer-scan",help="validate exact-build raw pointer candidates for the save worker without assigning dispatch semantics")
    sp.add_argument('--trace-log',type=Path,help='Ghidra script log (default: logs/ghidra-save-worker-pointers-v1-script.log)')
    sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/save-worker-pointer-scan.json)')
    sp.set_defaults(func=cmd_save_worker_pointer_scan)
    sp=sub.add_parser("nso-relocation-crossref",help="parse exact-build NSO RELATIVE/RELR relocations and cross-reference pinned function ranges")
    base(sp);sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/nso-relocation-crossref.json)')
    sp.set_defaults(func=cmd_nso_relocation_crossref)
    sp=sub.add_parser("crossref-gfbcol-main",help="cross-reference exact-build main string literals with GFBCol slot-0 candidates without assigning semantics")
    base(sp);sp.add_argument('--output',type=Path,help='JSON report output (default: manifests/gfbcol-main-token-crossref.json)')
    sp.set_defaults(func=cmd_crossref_gfbcol_main)
    sp=sub.add_parser("decode-bnk-media",help="extract indexed Wwise v128 BNK media to .bnk.contents and decode WAV")
    base(sp);sp.add_argument("--limit",type=int,default=20,help="maximum DIDX media members; 0 means all")
    sp.add_argument("--execute",action="store_true")
    sp.add_argument("--sources-file",type=Path,help="process only listed BNK source paths")
    sp.add_argument("--vgmstream",type=Path,default=PROJECT/"tools/bin/vgmstream-r2168/vgmstream-cli.exe")
    sp.add_argument("--timeout",type=int,default=240)
    sp.set_defaults(func=cmd_decode_bnk_media)
    sp=sub.add_parser('decode-assets',help='convert representative BNTX/model/animation/PTCL/WEM samples')
    base(sp);sp.add_argument('--execute',action='store_true');sp.set_defaults(func=cmd_decode_assets)
    for command, kind, help_text in [
        ("decode-textures", "texture", "batch BNTX to one-to-one PNG outputs"),
        ("decode-models", "model", "batch GFBMDL to one-to-one GLB outputs"),
        ("decode-animations", "animation", "batch GFbANM structure to JSON"),
        ("decode-particles", "particle", "batch VFXB particle structure to JSON"),
    ]:
        sp=sub.add_parser(command, help=help_text);base(sp)
        sp.add_argument("--limit",type=int,default=20);sp.add_argument("--execute",action="store_true")
        sp.add_argument("--sources-file",type=Path,help="process only listed ROMFS-relative source paths")
        if kind == "texture":
            sp.add_argument("--ffmpeg",type=Path,default=Path(r"D:\Tool\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"))
        if kind == "model":
            sp.add_argument("--blender",type=Path,default=Path(r"D:\Tool\Blender 5.1\blender.exe"))
            sp.add_argument("--timeout",type=int,default=180)
        sp.set_defaults(func=cmd_decode_asset_type,kind=kind)
    sp=sub.add_parser("decode-fonts", help="decrypt verified BFOTF fonts to path-mirrored OpenType (.otf)")
    base(sp);sp.add_argument("--limit",type=int,default=20);sp.add_argument("--execute",action="store_true")
    sp.add_argument("--sources-file",type=Path,help="process only listed ROMFS-relative BFOTF source paths")
    sp.set_defaults(func=cmd_decode_fonts)
    sp=sub.add_parser("decode-bffnt", help="decode supported NX BFFNT sections and embedded BNTX texture sheets")
    base(sp);sp.add_argument("--limit",type=int,default=20);sp.add_argument("--execute",action="store_true")
    sp.add_argument("--sources-file",type=Path,help="process only listed ROMFS-relative BFFNT source paths")
    sp.add_argument("--ffmpeg",type=Path,default=Path(r"D:\Tool\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"))
    sp.set_defaults(func=cmd_decode_bffnt)
    sp=sub.add_parser("register-gamedata",help="rehash and register outputs from an existing completed game-data manifest")
    base(sp);sp.add_argument("--sources-file",type=Path,help="rehash only listed ROMFS-relative source paths (one per line; # comments allowed)")
    sp.set_defaults(func=cmd_register_gamedata)
    sp=sub.add_parser("coverage",help="summarize SCANNED/DECODED/FAILED/UNKNOWN sources")
    sp.set_defaults(func=cmd_coverage)
    sp=sub.add_parser("amx-catalog",help="inspect AMX headers and the static LGPE gate; keep bodies UNKNOWN")
    base(sp);sp.add_argument("--limit",type=int,default=0);sp.set_defaults(func=cmd_amx_catalog)
    sp=sub.add_parser("decode-amx",help="decode AMX compact cells and validate against the exact LGPE 1.0.2 opcode checker")
    base(sp);sp.add_argument("--limit",type=int,default=0,help="0 means all catalogued scripts")
    sp.add_argument("--execute",action="store_true")
    sp.add_argument("--sources-file",type=Path,help="process only listed RomFS-relative AMX source paths")
    sp.set_defaults(func=cmd_decode_amx)
    sp=sub.add_parser("retry-failed",help="retry only FAILED sources; preserve successful manifest rows")
    base(sp);sp.add_argument("--domain",choices=["all","archive","gamedata","learnset","audio","wave","bnk","texture","model","animation","particle","collision","font","bffnt","amx","bseq"],default="all")
    sp.add_argument("--include-unsupported",action="store_true");sp.add_argument("--execute",action="store_true")
    sp.add_argument("--timeout",type=int,default=240)
    sp.add_argument("--vgmstream",type=Path,default=PROJECT/"tools/bin/vgmstream-r2168/vgmstream-cli.exe")
    sp.add_argument("--blender",type=Path,default=Path(r"D:\Tool\Blender 5.1\blender.exe"))
    sp.add_argument("--ffmpeg",type=Path,default=Path(r"D:\Tool\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"))
    sp.set_defaults(func=cmd_retry_failed)
    sp=sub.add_parser('run',help='scan, compare, plan, then run bounded domain batches')
    base(sp);sp.add_argument("--limit",type=int,default=20,help="0 means all compatible inputs")
    sp.add_argument("--execute",action="store_true");sp.add_argument("--full-sha256",action="store_true")
    sp.add_argument("--timeout",type=int,default=240)
    sp.add_argument("--blender",type=Path,default=None,help="optional Blender executable override")
    sp.add_argument("--ffmpeg",type=Path,default=None,help="optional FFmpeg executable override")
    sp.add_argument("--vgmstream",type=Path,default=None,help="optional vgmstream-cli executable override")
    sp.set_defaults(func=cmd_run)
    sp=sub.add_parser('decode-audio');base(sp)
    sp.add_argument('--vgmstream',type=Path,default=PROJECT/'tools/bin/vgmstream-r2168/vgmstream-cli.exe')
    sp.add_argument('--execute',action='store_true');sp.add_argument('--overwrite',action='store_true')
    sp.add_argument('--limit',type=int,default=20);sp.add_argument('--timeout',type=int,default=240)
    sp.add_argument('--tool-version',default='vgmstream r2168');sp.set_defaults(func=cmd_audio)
    sp=sub.add_parser('decode-wave',help='decode Microsoft ADPCM WAVE sources to mirrored PCM16 WAVE outputs')
    base(sp);sp.add_argument('--vgmstream',type=Path,default=PROJECT/'tools/bin/vgmstream-r2168/vgmstream-cli.exe')
    sp.add_argument('--execute',action='store_true');sp.add_argument('--overwrite',action='store_true')
    sp.add_argument('--limit',type=int,default=20);sp.add_argument('--timeout',type=int,default=240)
    sp.add_argument('--sources-file',type=Path,help='process only listed ROMFS-relative .wav paths')
    sp.set_defaults(func=cmd_wave)
    sp=sub.add_parser('register-samples',help='verify and register existing three-domain sample evidence')
    base(sp);sp.set_defaults(func=cmd_register_samples)
    sp=sub.add_parser('verify');base(sp)
    sp.add_argument('--sources-file',type=Path,help='verify receipts for listed ROMFS-relative source paths (one per line; # comments allowed)')
    sp.set_defaults(func=cmd_verify)
    args=a.parse_args(argv)
    arguments = vars(args).copy()
    arguments.pop("func", None)
    journal = RunJournal(PROJECT, args.command, arguments)
    args._journal = journal
    try:
        code = args.func(args)
    except (OSError,ValueError,subprocess.SubprocessError) as e:
        journal.finish(1, f"{type(e).__name__}: {e}")
        print(type(e).__name__+':',e,file=sys.stderr)
        return 1
    except Exception as e:
        journal.finish(1, f"{type(e).__name__}: {e}")
        raise
    journal.finish(code)
    return code

if __name__=='__main__':raise SystemExit(main())
