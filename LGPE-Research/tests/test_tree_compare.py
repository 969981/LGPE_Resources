import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import lgpe_research.tree as tree


class TreeCompareTest(unittest.TestCase):
    def test_reports_extensionless_exefs_files_without_calling_them_missing(self):
        compare = getattr(tree, "compare_snapshot_to_scan", None)
        self.assertTrue(callable(compare), "tree compare helper must report catalog differences")
        if not callable(compare):
            return

        with TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot.csv"
            scan = root / "scan.csv"
            with snapshot.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("relative_to_game", "suffix", "partition"))
                writer.writerow(("1.0.2/test_NCA/1/bin/a.dat", ".dat", "romfs"))
                writer.writerow(("1.0.2/test_NCA/0/main.npdm", ".npdm", "exefs"))
            with scan.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("partition", "relative_path"))
                writer.writerow(("romfs", "bin/a.dat"))
                writer.writerow(("exefs", "main.npdm"))
                writer.writerow(("exefs", "main"))

            result = compare(snapshot, scan, "1.0.2", "test_NCA")

        self.assertEqual(result["snapshot_entries"], 2)
        self.assertEqual(result["scanned_entries"], 3)
        self.assertEqual(result["matched_paths"], 2)
        self.assertEqual(result["snapshot_only"], [])
        self.assertEqual(result["scan_only"], [{"partition": "exefs", "relative_path": "main"}])


if __name__ == "__main__":
    unittest.main()
