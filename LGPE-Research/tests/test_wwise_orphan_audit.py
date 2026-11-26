import hashlib
import importlib
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


NCA = "2b7730a9e56498bbafac2002d4908c6b_NCA"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


class WwiseOrphanAuditTests(unittest.TestCase):
    def test_scans_binary_decimal_and_hex_encodings_with_offsets(self):
        source_id = 0x1234ABCD
        data = (
            bytes.fromhex("cdab3412")
            + b"|305441741|1234abcd|1234ABCD|0x1234abcd|0x1234ABCD|0X1234abcd|0X1234ABCD"
        )

        module_spec = importlib.util.find_spec("lgpe_research.wwise_orphan_audit")
        self.assertIsNotNone(module_spec, "the repeatable Wwise orphan audit is missing")
        module = importlib.import_module("lgpe_research.wwise_orphan_audit")
        result = module.scan_id_occurrences(data, source_id)

        self.assertEqual(
            result["countsByEncoding"],
            {
                "u32le": 1,
                "u32be": 0,
                "u64le": 0,
                "u64be": 0,
                "decimal_ascii": 1,
                "hex8_lower_ascii": 3,
                "hex8_upper_ascii": 3,
                "hex0x_lower_ascii": 1,
                "hex0x_upper_ascii": 1,
                "hex0X_lower_ascii": 1,
                "hex0X_upper_ascii": 1,
            },
        )
        self.assertEqual(
            result["matches"],
            [
                {"encoding": "u32le", "offset": 0},
                {"encoding": "decimal_ascii", "offset": 5},
                {"encoding": "hex8_lower_ascii", "offset": 15},
                {"encoding": "hex8_upper_ascii", "offset": 24},
                {"encoding": "hex0x_lower_ascii", "offset": 33},
                {"encoding": "hex8_lower_ascii", "offset": 35},
                {"encoding": "hex0x_upper_ascii", "offset": 44},
                {"encoding": "hex8_upper_ascii", "offset": 46},
                {"encoding": "hex0X_lower_ascii", "offset": 55},
                {"encoding": "hex8_lower_ascii", "offset": 57},
                {"encoding": "hex0X_upper_ascii", "offset": 66},
                {"encoding": "hex8_upper_ascii", "offset": 68},
            ],
        )

    def test_writes_hash_checked_didx_and_bseq_audit(self):
        module = importlib.import_module("lgpe_research.wwise_orphan_audit")
        writer = getattr(module, "write_unreferenced_wem_id_audit", None)
        self.assertTrue(callable(writer), "the repeatable Wwise orphan audit writer is missing")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "game"
            project = base / "LGPE-Research"
            romfs = root / "1.0.2" / NCA / "1"
            bank_source = "bin/sound/NX64/wwise/bank/test.bnk"
            bseq_source = "bin/battle/waza/sequence/test.bseq"
            wem_id = 305441741
            wem_source = f"bin/sound/NX64/wwise/bank/{wem_id}.wem"
            wav_output = f"decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/{wem_id}.wav"
            xml_output = "decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/test.xml"

            def write_source(relative, data):
                path = romfs.joinpath(*Path(relative).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                return path

            bank_data_chunk = b"xyz"
            didx_record = struct.pack("<III", 7, 0, len(bank_data_chunk))
            bank_bytes = (
                b"BKHD" + struct.pack("<I", 8) + struct.pack("<II", 128, 99)
                + b"DIDX" + struct.pack("<I", 12) + didx_record
                + b"DATA" + struct.pack("<I", len(bank_data_chunk)) + bank_data_chunk
            )
            write_source(bank_source, bank_bytes)
            xml_path = project / xml_output
            xml_path.parent.mkdir(parents=True, exist_ok=True)
            xml_path.write_bytes(b"<bank />")
            bseq_bytes = b"SESD|305441741"
            bseq_path = write_source(bseq_source, bseq_bytes)
            wem_path = write_source(wem_source, b"synthetic-wem")
            wav_path = project / wav_output
            wav_path.parent.mkdir(parents=True, exist_ok=True)
            wav_path.write_bytes(b"synthetic-wav")

            bank_hash = _sha256(bank_bytes)
            _write_jsonl(project / "manifests" / "bnk.jsonl", [{
                "source": bank_source,
                "source_sha256": bank_hash,
                "source_bytes": len(bank_bytes),
                "status": "DECODED_EXISTING_VERIFIED",
                "output": xml_output,
                "output_sha256": _sha256(xml_path.read_bytes()),
            }])
            _write_jsonl(project / "manifests" / "bnk_media_banks.jsonl", [{
                "source": bank_source,
                "source_sha256": bank_hash,
                "source_bytes": len(bank_bytes),
                "status": "INDEXED",
                "bank_version": 128,
                "bank_id": 99,
                "chunk_tags": ["BKHD", "DIDX", "DATA"],
                "data_bytes": len(bank_data_chunk),
                "member_count": 1,
                "member_bytes": len(bank_data_chunk),
            }])
            _write_jsonl(project / "manifests" / "bnk_media.jsonl", [{
                "source": bank_source,
                "source_sha256": bank_hash,
                "container_index": 0,
                "media_id": 7,
                "index_record_hex": didx_record.hex(),
                "data_offset": 0,
                "size_bytes": len(bank_data_chunk),
                "internal_path": "7.wem",
                "status": "UNSUPPORTED",
            }])
            _write_jsonl(project / "manifests" / "bseq.jsonl", [{
                "source": bseq_source,
                "source_sha256": _sha256(bseq_bytes),
                "source_bytes": len(bseq_bytes),
                "status": "UNSUPPORTED",
            }])
            audio_row = {
                "source": wem_source,
                "source_sha256": _sha256(wem_path.read_bytes()),
                "source_bytes": wem_path.stat().st_size,
                "output": wav_output,
                "output_sha256": _sha256(wav_path.read_bytes()),
                "output_bytes": wav_path.stat().st_size,
                "status": "DECODED_EXISTING_VERIFIED",
            }
            _write_jsonl(project / "manifests" / "audio.jsonl", [audio_row])
            _write_jsonl(project / "manifests" / "wwise_unreferenced_wem.jsonl", [{
                "schema": "lgpe-wwise-unreferenced-wem-hirc-v1",
                "sourceVersion": "Let's Go Pikachu 1.0.2",
                "sourceId": str(wem_id),
                "wemSource": wem_source,
                "wemSourceSha256": audio_row["source_sha256"],
                "wemSourceBytes": audio_row["source_bytes"],
                "audioReceiptStatus": audio_row["status"],
                "wav": wav_output,
                "wavSha256": audio_row["output_sha256"],
                "hircSearchBankCount": 1,
                "hircSearchBankFailures": 0,
                "hircMatches": [],
                "hircMatchCount": 0,
                "status": "NO_LOCAL_HIRC_SOURCEID_MATCH",
            }])

            summary = writer(root, project)

            report_path = project / "manifests" / "wwise_unreferenced_wem_id_audit.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            target = report["targets"][0]
            self.assertEqual(summary["status"], "ANALYZED")
            self.assertEqual(target["hirc"]["matchCount"], 0)
            self.assertEqual(target["didx"]["matchCount"], 0)
            self.assertEqual(target["bseq"]["countsByEncoding"]["decimal_ascii"], 1)
            self.assertEqual(
                target["bseq"]["matches"],
                [{"source": bseq_source, "encoding": "decimal_ascii", "offset": 5}],
            )
            self.assertEqual(report["coverage"]["verifiedBseqSources"], 1)
            self.assertEqual(report["coverage"]["verifiedBnkSources"], 1)

            media_rows = json.loads(
                (project / "manifests" / "bnk_media.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )
            media_rows["media_id"] = wem_id
            _write_jsonl(project / "manifests" / "bnk_media.jsonl", [media_rows])
            with self.assertRaisesRegex(ValueError, "DIDX media manifest differs"):
                writer(root, project)

    def test_sequence_audio_map_includes_the_orphan_id_audit_summary(self):
        module = importlib.import_module("lgpe_research.bseq_wwise_map")
        audit_summary = {"status": "ANALYZED", "report": "manifests/wwise_unreferenced_wem_id_audit.json"}
        sequence_summary = {
            "bseqManifestRows": 0,
            "bseqStatusCounts": {},
            "decodedSequencesVerified": 0,
            "unsupportedSequences": 0,
            "failedSequences": 0,
            "pendingSequences": 0,
            "bankNameReferenceOccurrences": 0,
            "exactBankNameReferenceOccurrences": 0,
            "distinctBankNameLiterals": 0,
        }

        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            root = project / "game"
            with (
                patch.object(module, "_bank_manifest_index", return_value=({}, {})),
                patch.object(module, "_sequence_rows", return_value=([], sequence_summary)),
                patch.object(
                    module,
                    "write_unreferenced_wem_id_audit",
                    create=True,
                    return_value=audit_summary,
                ) as audit_writer,
            ):
                summary = module.build_sequence_wwise_map(root, project)

        self.assertEqual(summary.get("unreferencedWemIdAudit"), audit_summary)
        audit_writer.assert_called_once_with(root, project)


if __name__ == "__main__":
    unittest.main()
