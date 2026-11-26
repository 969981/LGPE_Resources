"""Parse the actual Windows `tree /f` UTF-16 text snapshot, without needing binary files."""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path


def parse_tree(src:Path):
    # `tree /f` in PowerShell redirection frequently outputs UTF-16LE.
    head=src.read_bytes()[:4]
    encoding='utf-16' if head.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    stack=[]
    for line in src.read_text(encoding=encoding,errors='replace').splitlines():
        branches=[x for x in (line.find('├─'),line.find('└─')) if x>=0]
        if branches:
            offset=max(branches); name=line[offset+2:].strip()
            while stack and stack[-1][0]>=offset:stack.pop()
            stack.append((offset,name))
        elif stack and line.strip(' │\t'):
            filename=line.strip(' │\t')
            if filename:
                yield '/'.join([x[1] for x in stack]+[filename])

def export_tree(src:Path,dest:Path)->dict:
    dest.parent.mkdir(parents=True,exist_ok=True)
    files=0; suffix=Counter(); prefixes=Counter()
    with dest.open('w',encoding='utf-8-sig',newline='') as out:
        w=csv.writer(out,lineterminator='\n');w.writerow(('relative_to_game','suffix','partition'))
        for path in parse_tree(src):
            if not path.startswith('1.0.2/'):continue
            name=Path(path)
            ext=name.suffix.lower()
            # Ignore the version directory and listing (folder names have no reliable ext test).
            if not ext or (path.count('/')<3):continue
            partition='romfs' if '/1/' in path else 'exefs' if '/0/' in path else 'other'
            w.writerow((path,ext,partition));suffix[ext]+=1;prefixes[partition]+=1;files+=1
    return {'files':files,'extensions':dict(suffix.most_common()),'partitions':dict(prefixes)}

def compare_snapshot_to_scan(snapshot:Path, scan:Path, version:str, nca_folder:str)->dict:
    """Compare snapshot paths with the real scan, keeping extensionless files visible."""
    snapshot_rows=[]
    with snapshot.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            parts=row.get('relative_to_game','').replace('\\','/').split('/')
            if parts[:2] != [version,nca_folder] or len(parts) < 4:
                continue
            partition={'0':'exefs','1':'romfs'}.get(parts[2])
            relative='/'.join(parts[3:])
            if partition and relative:
                snapshot_rows.append((partition,relative))

    scan_rows=[]
    with scan.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            partition=row.get('partition','')
            relative=row.get('relative_path','').replace('\\','/')
            if partition in {'exefs','romfs'} and relative:
                scan_rows.append((partition,relative))

    snapshot_set=set(snapshot_rows)
    scan_set=set(scan_rows)
    def paths(rows):
        return [{'partition':p,'relative_path':r} for p,r in sorted(rows)]
    def duplicates(rows):
        counts=Counter(rows)
        return [
            {'partition':p,'relative_path':r,'count':count}
            for (p,r),count in sorted(counts.items()) if count > 1
        ]

    return {
        'snapshot_entries':len(snapshot_rows),
        'scanned_entries':len(scan_rows),
        'matched_paths':len(snapshot_set & scan_set),
        'snapshot_only':paths(snapshot_set - scan_set),
        'scan_only':paths(scan_set - snapshot_set),
        'snapshot_duplicate_paths':duplicates(snapshot_rows),
        'scan_duplicate_paths':duplicates(scan_rows),
    }
