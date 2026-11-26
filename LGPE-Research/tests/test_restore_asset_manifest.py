import json
import tempfile
import unittest
from pathlib import Path

from scripts.restore_asset_manifest_provenance import restore_asset_manifest


class RestoreAssetManifestTests(unittest.TestCase):
    def test_restores_asset_metadata_from_matching_output_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            manifests = project / "manifests"
            manifests.mkdir()
            source = "bin/app/report/sample.bntx"
            receipt = {
                "method": "lgpe_research.asset_batch/texture",
                "relative_source": source,
                "source_sha256": "source-hash",
                "output_sha256": "output-hash",
                "output_size": 123,
                "validation": {"width": 4, "height": 4},
                "conversion": {"pixel_format": "R16_UNORM"},
                "tool_version": {"BNTX-Extractor": "pinned"},
                "command": [{"command": ["decoder"]}],
            }
            (manifests / "outputs.jsonl").write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            row = {
                "domain": "texture", "source": source,
                "status": "DECODED_EXISTING_VERIFIED",
                "source_sha256": "source-hash", "output_sha256": "output-hash",
            }
            (manifests / "textures.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

            result = restore_asset_manifest(project, "texture")
            current = json.loads((manifests / "textures.jsonl").read_text(encoding="utf-8"))

            self.assertEqual(result["matched_rows"], 1)
            self.assertEqual(current["output_bytes"], 123)
            self.assertEqual(current["validation"], receipt["validation"])
            self.assertEqual(current["conversion"], receipt["conversion"])
            self.assertEqual(current["tool_versions"], receipt["tool_version"])
            self.assertEqual(current["commands"], receipt["command"])


if __name__ == "__main__":
    unittest.main()
