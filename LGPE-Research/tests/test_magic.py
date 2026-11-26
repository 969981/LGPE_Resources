from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lgpe_research.core import probe


class RealSignatureTest(unittest.TestCase):
    def test_probe_recognizes_headers_observed_in_lgpe_102(self):
        samples = {
            b"GFLXPACK": "GFLXPACK",
            b"SARC": "SARC",
            b"VFXB": "VFXB",
            b"SESD": "SESD",
            b"\x36\xf8\x1a\x1e": "BFOTF",
            b"FFNT": "BFFNT",
        }
        with TemporaryDirectory() as directory:
            for header, expected in samples.items():
                path = Path(directory) / "sample.bin"
                path.write_bytes(header + bytes(60))
                with self.subTest(signature=header.decode("ascii", errors="backslashreplace")):
                    self.assertEqual(probe(path)["signature"], expected)


if __name__ == "__main__":
    unittest.main()
