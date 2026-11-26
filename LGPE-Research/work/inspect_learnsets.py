import hashlib, json, struct
from collections import Counter
from pathlib import Path
project = Path(__file__).resolve().parents[1]
source = 'bin/archive/waza_oboe.gfpak'
archive_rows = [json.loads(line) for line in (project/'manifests/archives.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
archive = next(row for row in archive_rows if row.get('source','').casefold() == source.casefold())
print('archive_receipt', json.dumps({k:archive.get(k) for k in ('source','status','member_count','output','source_sha256','output_sha256','method')}, sort_keys=True))
member_rows = [json.loads(line) for line in (project/'manifests/outputs.jsonl').read_text(encoding='utf-8').splitlines() if line.strip() and json.loads(line).get('relative_source','').casefold() == source.casefold()]
print('member_receipts', len(member_rows), 'example_fields', sorted(member_rows[0]) if member_rows else [])
root = project/'decoded/1.0.2/romfs/bin/archive/waza_oboe.gfpak.contents'
files = sorted((path for path in root.rglob('*') if path.is_file()), key=lambda p:p.as_posix().casefold())
sizes = Counter(); endings = Counter(); invalid = 0; exact_terminator = 0
for path in files:
    data = path.read_bytes(); sizes[len(data)] += 1
    if len(data) < 4 or len(data) % 4:
        invalid += 1; continue
    endings[data[-4:].hex()] += 1
    exact_terminator += data[-4:] == b'\xff'*4
print('member_count', len(files), 'size_histogram', sizes.most_common(12), 'invalid_length', invalid)
print('trailing_words', endings.most_common(12), 'ffffffff_count', exact_terminator)
for path in files[:6]:
    data = path.read_bytes()
    words = [struct.unpack_from('<hh', data, i) for i in range(0, max(0,len(data)-4), 4)]
    print('sample', path.relative_to(root).as_posix(), 'bytes',len(data),'head',data[:20].hex(),'tail',data[-4:].hex(),'pairs',words[:3])
