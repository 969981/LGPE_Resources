from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest
from unittest.mock import patch
import lgpe_research.core as core
from lgpe_research.core import decode_destination, source_dirs, snapshot_scan, ensure_inside, iter_regular_files
from lgpe_research.tree import export_tree, parse_tree

class PipelineTest(unittest.TestCase):
    def test_extension_mirror(self):
        with TemporaryDirectory() as d:
            p=decode_destination('romfs','bin/message/English/common/bag.dat','.json',Path(d))
            self.assertEqual(p,Path(d)/'decoded/1.0.2/romfs/bin/message/English/common/bag.json')
    def test_path_traversal_rejected(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):decode_destination('romfs','../../outside.dat','.json',Path(d))
    def test_partition_locations(self):
        paths=source_dirs(Path('C:/some/game'))
        self.assertEqual(paths['romfs'].name,'1')
        self.assertEqual(paths['exefs'].name,'0')
    def test_scan_signature(self):
        with TemporaryDirectory() as d:
            root=Path(d);paths=source_dirs(root)
            for p in paths.values():p.mkdir(parents=True)
            (paths['romfs']/'fake.bntx').write_bytes(b'BNTX'+b'\0'*12)
            result=snapshot_scan(root,root/'out.csv')
            self.assertEqual(result['scanned'],1)
            self.assertEqual(result['counts']['.bntx'],1)
            self.assertNotIn(b'\r',(root/'out.summary.json').read_bytes())
    def test_regular_file_walk_is_sorted_recursive_and_does_not_follow_symlinks(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            (root/'nested').mkdir()
            (root/'A.bin').write_bytes(b'a')
            (root/'b.bin').write_bytes(b'b')
            (root/'nested'/'c.bin').write_bytes(b'c')
            link=root/'link.bin'
            try:
                link.symlink_to(root/'A.bin')
                linked=True
            except (OSError,NotImplementedError):
                linked=False
            files=iter_regular_files(root)
            self.assertEqual([path.relative_to(root).as_posix() for path in files],[
                'A.bin','b.bin','nested/c.bin'
            ])
            if linked:
                self.assertNotIn(link,files)
    def test_parallel_snapshot_scan_keeps_sorted_paths_across_probe_batches(self):
        with TemporaryDirectory() as d:
            root=Path(d);paths=source_dirs(root)
            paths['romfs'].mkdir(parents=True)
            paths['exefs'].mkdir(parents=True)
            for index in range(300):
                (paths['romfs']/f'file_{index:03}.bin').write_bytes(b'12345678')
            result=snapshot_scan(root,root/'out.csv')
            with (root/'out.csv').open(encoding='utf-8-sig',newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(result['scanned'],300)
            self.assertEqual(result['anomalies'],[])
            self.assertEqual([row['relative_path'] for row in rows],[
                f'file_{index:03}.bin' for index in range(300)
            ])
    def test_limited_scan_probes_only_the_requested_number_of_files(self):
        with TemporaryDirectory() as d:
            root=Path(d);paths=source_dirs(root)
            for partition in paths.values():partition.mkdir(parents=True)
            for index in range(5):
                (paths['romfs']/f'file_{index}.bin').write_bytes(b'12345678')
            with patch.object(core,'probe',wraps=core.probe) as probe:
                result=snapshot_scan(root,root/'out.csv',limit=1)
            self.assertEqual(result['scanned'],1)
            self.assertEqual(probe.call_count,1)
    def test_tree_utf16(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'tree.txt'
            p.write_text('└─1.0.2\n    └─abc_NCA\n        └─1\n            └─bin\n                file.dat\n',encoding='utf-16')
            self.assertIn('1.0.2/abc_NCA/1/bin/file.dat',list(parse_tree(p)))
            inventory=Path(d)/'inventory.csv'
            summary=export_tree(p,inventory)
            self.assertEqual(summary['files'],1)
            self.assertNotIn(b'\r',inventory.read_bytes())

if __name__=='__main__':unittest.main()
