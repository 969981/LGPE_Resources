import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from lgpe_research.amx_catalog import HEADER, catalog_amx_headers, parse_amx_header
from lgpe_research.core import NCA


ROOT = Path(__file__).resolve().parents[1]
ROMFS = ROOT.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
AMX_DIR = ROMFS / "bin/battle/ai_script"


def synthetic_amx(*, size=128, magic=0xF1E1, defsize=12, hea=0x210):
    fields = (
        size, magic, 10, 10, 4, defsize,
        0x70, 0x200, hea, 0x300, 0x198,
        0x3C, 0x3C, 0x48, 0x48, 0x6C, 0x6C, 0x6C,
    )
    return HEADER.pack(*fields) + b"\0" * (size - HEADER.size)


class AmxHeaderTests(unittest.TestCase):
    def test_parses_candidate_header_but_keeps_body_unknown(self):
        parsed = parse_amx_header(synthetic_amx())
        self.assertEqual(parsed["header_status"], "AMX_HEADER_CANDIDATE")
        self.assertEqual(parsed["body_status"], "UNKNOWN")
        self.assertEqual(parsed["known_magic_cell_bytes"], 8)
        self.assertEqual(parsed["fields"]["defsize"], 12)
        self.assertEqual(parsed["pinned_pawn64_comparison"]["compatibility"], "MISMATCH")
        self.assertFalse(parsed["pinned_pawn64_comparison"]["hea_equals_size_reference_invariant"])
        self.assertEqual(len(bytes.fromhex(parsed["header_hex"])), HEADER.size)

    def test_game_header_gate_accepts_supported_12_byte_stub_case(self):
        parsed = parse_amx_header(synthetic_amx())
        gate = parsed["lgpe_runtime_header_check"]
        self.assertEqual(gate["status"], "STATIC_PASS")
        self.assertEqual(gate["name_table_length"], 0)
        self.assertEqual(gate["definition_record_size"], 12)
        self.assertTrue(gate["flag_0x04_set"])

    def test_game_header_gate_rejects_name_table_length_at_64(self):
        data = bytearray(synthetic_amx())
        struct.pack_into("<H", data, 0x6C, 0x40)
        parsed = parse_amx_header(bytes(data))
        gate = parsed["lgpe_runtime_header_check"]
        self.assertEqual(gate["status"], "STATIC_REJECT")
        self.assertEqual(gate["name_table_length"], 0x40)

    def test_marks_unknown_magic_without_guessing_a_dialect(self):
        parsed = parse_amx_header(synthetic_amx(magic=0x1234))
        self.assertEqual(parsed["header_status"], "UNKNOWN_HEADER")
        self.assertIsNone(parsed["known_magic_cell_bytes"])
        self.assertEqual(parsed["body_status"], "UNKNOWN")

    def test_rejects_truncated_header(self):
        with self.assertRaisesRegex(ValueError, "truncated AMX header"):
            parse_amx_header(b"\0" * (HEADER.size - 1))

    def test_catalog_preserves_other_sources_on_bounded_refresh(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "game"
            src = root / "1.0.2" / NCA / "1" / "bin/battle/ai_script"
            src.mkdir(parents=True)
            (src / "a.amx").write_bytes(synthetic_amx())
            (src / "b.amx").write_bytes(synthetic_amx())
            project = base / "project"

            complete = catalog_amx_headers(root, project)
            self.assertEqual(complete["scanned"], 2)
            self.assertEqual(complete["static_header_pass"], 2)
            self.assertEqual(complete["static_header_reject"], 0)
            self.assertEqual(complete["unknown"], 2)
            (src / "c.amx").write_bytes(synthetic_amx())
            bounded = catalog_amx_headers(root, project, limit=1)
            self.assertEqual(bounded["scanned"], 1)
            manifest = project / "manifests/amx_headers.jsonl"
            rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
            self.assertEqual({row["source"] for row in rows}, {
                "bin/battle/ai_script/a.amx", "bin/battle/ai_script/b.amx",
            })
            self.assertTrue(all(row["status"] == "UNKNOWN" for row in rows))

    def test_catalog_reads_receipted_script_archive_member_with_container_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "game"
            nca = root / "1.0.2" / NCA
            archive = nca / "1/bin/archive/script_amx.gfpak"
            archive.parent.mkdir(parents=True)
            archive_data = b"synthetic container source"
            archive.write_bytes(archive_data)

            data = synthetic_amx()
            internal_path = "A830472B45868B06/37A21F6E58876C11"
            member_output = (
                base / "project/decoded/1.0.2/romfs/bin/archive/"
                "script_amx.gfpak.contents" / internal_path
            )
            member_output.parent.mkdir(parents=True)
            member_output.write_bytes(data)
            archive_row = {
                "source": "bin/archive/script_amx.gfpak",
                "source_size": len(archive_data),
                "source_sha256": hashlib.sha256(archive_data).hexdigest(),
                "status": "DECODED",
                "members": [{
                    "index": index,
                    "internal_path": internal_path,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                } for index in (0, 1)],
            }
            project = base / "project"
            archive_manifest = project / "manifests/archives.jsonl"
            archive_manifest.parent.mkdir(parents=True)
            archive_manifest.write_text(json.dumps(archive_row) + "\n", encoding="utf-8")

            result = catalog_amx_headers(root, project)
            rows = [json.loads(line) for line in (project / "manifests/amx_headers.jsonl").read_text().splitlines()]
            member = next(row for row in rows if row.get("source_kind") == "gfpak_member")
            members = [row for row in rows if row.get("source_kind") == "gfpak_member"]
            self.assertEqual(result["archive_member_scanned"], 2)
            self.assertEqual(result["static_header_pass"], 2)
            self.assertEqual(result["unknown"], 2)
            self.assertEqual(len(members), 2)
            self.assertEqual({row["container_index"] for row in members}, {0, 1})
            self.assertEqual(member["source"], "bin/archive/script_amx.gfpak.contents/" + internal_path)
            self.assertEqual(member["container_source"], "bin/archive/script_amx.gfpak")
            self.assertEqual(member["container_index"], 0)
            self.assertEqual(member["internal_path"], internal_path)
            self.assertEqual(member["source_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(member["status"], "UNKNOWN")

    def test_catalog_does_not_claim_expected_member_hash_when_container_receipt_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "game"
            archive = root / "1.0.2" / NCA / "1/bin/archive/script_amx.gfpak"
            archive.parent.mkdir(parents=True)
            archive_data = b"actual container bytes"
            archive.write_bytes(archive_data)
            data = synthetic_amx()
            internal_path = "A830472B45868B06/37A21F6E58876C11"
            member_output = (
                base / "project/decoded/1.0.2/romfs/bin/archive/"
                "script_amx.gfpak.contents" / internal_path
            )
            member_output.parent.mkdir(parents=True)
            member_output.write_bytes(data)
            archive_row = {
                "source": "bin/archive/script_amx.gfpak",
                "source_size": len(archive_data),
                "source_sha256": "0" * 64,
                "status": "DECODED",
                "members": [{
                    "index": 3,
                    "internal_path": internal_path,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }],
            }
            project = base / "project"
            archive_manifest = project / "manifests/archives.jsonl"
            archive_manifest.parent.mkdir(parents=True)
            archive_manifest.write_text(json.dumps(archive_row) + "\n", encoding="utf-8")

            result = catalog_amx_headers(root, project)
            manifest = project / "manifests/amx_headers.jsonl"
            row = json.loads(manifest.read_text(encoding="utf-8").strip())
            self.assertEqual(result["failed"], 1)
            self.assertEqual(row["status"], "FAILED")
            self.assertEqual(row["decoder_status"], "CONTAINER_RECEIPT_INVALID")
            self.assertNotIn("source_sha256", row)
            self.assertEqual(row["container_sha256"], hashlib.sha256(archive_data).hexdigest())

    @unittest.skipUnless(AMX_DIR.is_dir(), "private local dump unavailable")
    def test_all_local_lgpe_ai_scripts_match_candidate_header_and_remain_unknown(self):
        paths = sorted(AMX_DIR.glob("*.amx"))
        self.assertEqual(len(paths), 7)
        before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        parsed = [parse_amx_header(path.read_bytes()) for path in paths]
        self.assertTrue(all(item["header_status"] == "AMX_HEADER_CANDIDATE" for item in parsed))
        self.assertTrue(all(item["fields"]["magic"] == 0xF1E1 for item in parsed))
        self.assertTrue(all(item["fields"]["file_version"] == 10 for item in parsed))
        self.assertTrue(all(item["fields"]["amx_version"] == 10 for item in parsed))
        self.assertTrue(all(item["fields"]["defsize"] == 12 for item in parsed))
        self.assertTrue(all(item["body_status"] == "UNKNOWN" for item in parsed))
        self.assertTrue(all(item["lgpe_runtime_header_check"]["status"] == "STATIC_PASS" for item in parsed))
        self.assertTrue(all(item["lgpe_runtime_header_check"]["name_table_length"] == 63 for item in parsed))
        self.assertEqual(
            before,
            {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        )


if __name__ == "__main__":
    unittest.main()
