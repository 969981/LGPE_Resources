from __future__ import annotations

import importlib
import io
import json
import struct
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from pathlib import Path

from lgpe_research.cli import main


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack("<I", len(payload)) + payload


def _bank_with_one_media() -> tuple[bytes, bytes]:
    payload = b"RIFF\x04\x00\x00\x00WAVE"
    bkhd = struct.pack("<II", 128, 0x12345678) + bytes(12)
    didx = struct.pack("<III", 0x10203040, 0, len(payload))
    bank = b"".join((
        _chunk(b"BKHD", bkhd),
        _chunk(b"DIDX", didx),
        _chunk(b"DATA", payload),
        _chunk(b"HIRC", b"\x00\x00\x00\x00"),
    ))
    return bank, payload


def _bank_with_two_media(bank_id: int) -> bytes:
    first = b"RIFF\x04\x00\x00\x00WAVE"
    second = b"RIFF\x04\x00\x00\x00WAVE"
    bkhd = struct.pack("<II", 128, bank_id) + bytes(12)
    didx = b"".join((
        struct.pack("<III", bank_id * 2, 0, len(first)),
        struct.pack("<III", bank_id * 2 + 1, len(first), len(second)),
    ))
    return b"".join((
        _chunk(b"BKHD", bkhd), _chunk(b"DIDX", didx),
        _chunk(b"DATA", first + second), _chunk(b"HIRC", b"\x00\x00\x00\x00"),
    ))


class BnkMediaParserTests(unittest.TestCase):
    def test_cli_exposes_bounded_bnk_media_decoder(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = None
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                main(["decode-bnk-media", "--help"])
        except SystemExit as exc:
            exit_code = exc.code

        self.assertEqual(exit_code, 0, stderr.getvalue())
        self.assertIn("--limit", stdout.getvalue())
        self.assertIn("--execute", stdout.getvalue())

    def test_version_128_didx_entry_extracts_exact_data_slice(self):
        try:
            module = importlib.import_module("lgpe_research.bnk_media")
        except ImportError:
            module = None
        self.assertIsNotNone(module, "version-128 BNK media parser module must exist")
        parser = getattr(module, "parse_bnk_media", None)
        self.assertTrue(callable(parser), "BNK media parser API must exist")

        bank, expected_payload = _bank_with_one_media()
        parsed = parser(bank)

        self.assertEqual(parsed["bank_version"], 128)
        self.assertEqual(parsed["bank_id"], 0x12345678)
        self.assertEqual(len(parsed["members"]), 1)
        self.assertEqual(parsed["members"][0]["index"], 0)
        self.assertEqual(parsed["members"][0]["media_id"], 0x10203040)
        self.assertEqual(parsed["members"][0]["offset"], 0)
        self.assertEqual(parsed["members"][0]["size"], len(expected_payload))
        self.assertEqual(parsed["members"][0]["data"], expected_payload)

    def test_member_destination_uses_container_name_contents_and_media_id(self):
        try:
            module = importlib.import_module("lgpe_research.bnk_media")
        except ImportError:
            module = None
        self.assertIsNotNone(module, "BNK media parser module must exist")
        make_path = getattr(module, "bnk_member_output_path", None)
        self.assertTrue(callable(make_path), "BNK member path mapper API must exist")

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "LGPE-Research"
            output = make_path(project, "bin/sound/bank/System_Common.bnk", 540928976)

            self.assertEqual(
                output,
                project / "decoded/1.0.2/romfs/bin/sound/bank/System_Common.bnk.contents/540928976.wem",
            )

    def test_batch_extracts_nested_wem_and_decodes_mirrored_wav(self):
        module = importlib.import_module("lgpe_research.bnk_media")
        runner = getattr(module, "run_bnk_media_batch", None)
        self.assertTrue(callable(runner), "BNK media batch command API must exist")

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            project = folder / "LGPE-Research"
            root = folder / "game"
            relative_source = "bin/sound/bank/System_Common.bnk"
            source = root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1" / relative_source
            source.parent.mkdir(parents=True)
            bank, expected_payload = _bank_with_one_media()
            source.write_bytes(bank)
            source_hash = __import__("hashlib").sha256(bank).hexdigest()
            (project / "manifests").mkdir(parents=True)
            (project / "manifests/bnk.jsonl").write_text(
                json.dumps({
                    "source": relative_source,
                    "status": "DECODED",
                    "source_sha256": source_hash,
                    "source_bytes": len(bank),
                }) + "\n",
                encoding="utf-8",
            )
            tool = project / "tools/vgmstream-cli"
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"test stub executable")

            def fake_vgmstream(args, **kwargs):
                wav_path = Path(args[3])
                wav_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(wav_path), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(48000)
                    output.writeframes(b"\x00\x00")
                class Result:
                    returncode = 0
                    stdout = "decoded"
                    stderr = ""
                return Result()

            with patch("subprocess.run", side_effect=fake_vgmstream):
                summary = runner(root, project, limit=1, execute=True, tool=tool)

            wem = project / "decoded/1.0.2/romfs/bin/sound/bank/System_Common.bnk.contents/270544960.wem"
            wav = wem.with_suffix(".wav")
            self.assertEqual(summary["decoded_members"], 1)
            self.assertEqual(wem.read_bytes(), expected_payload)
            self.assertTrue(wav.is_file())
            receipt_rows = [
                json.loads(line) for line in (project / "manifests/outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(receipt_rows), 2)
            self.assertEqual(
                {row["internal_path"] for row in receipt_rows},
                {"270544960.wem", "270544960.wav"},
            )

    def test_source_filter_skips_unselected_banks_before_reading_them(self):
        module = importlib.import_module("lgpe_research.bnk_media")
        runner = getattr(module, "run_bnk_media_batch", None)
        self.assertTrue(callable(runner))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            project = folder / "LGPE-Research"
            root = folder / "game"
            good_relative = "bin/sound/bank/Selected.bnk"
            bad_relative = "bin/sound/bank/Unselected.bnk"
            good_source = root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1" / good_relative
            good_source.parent.mkdir(parents=True)
            bank, _ = _bank_with_one_media()
            good_source.write_bytes(bank)
            manifest_dir = project / "manifests"
            manifest_dir.mkdir(parents=True)
            rows = [
                {"source": good_relative, "status": "DECODED", "source_sha256": __import__("hashlib").sha256(bank).hexdigest()},
                {"source": bad_relative, "status": "DECODED", "source_sha256": "0" * 64},
            ]
            (manifest_dir / "bnk.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8",
            )

            summary = runner(
                root, project, limit=1, execute=False,
                only_sources={good_relative},
            )

            self.assertEqual(summary["banks_scanned"], 1)
            self.assertEqual(summary["banks_failed"], 0)
            bank_rows = [
                json.loads(line)
                for line in (manifest_dir / "bnk_media_banks.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual({row["source"] for row in bank_rows}, {good_relative})

    def test_bounded_sample_round_robins_across_selected_banks(self):
        module = importlib.import_module("lgpe_research.bnk_media")
        runner = getattr(module, "run_bnk_media_batch", None)
        self.assertTrue(callable(runner))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            project = folder / "LGPE-Research"
            root = folder / "game"
            romfs = root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
            relative_sources = ["bin/sound/bank/A.bnk", "bin/sound/bank/B.bnk"]
            rows = []
            for bank_id, relative in enumerate(relative_sources, 1):
                source = romfs / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                bank = _bank_with_two_media(bank_id)
                source.write_bytes(bank)
                rows.append({
                    "source": relative,
                    "status": "DECODED",
                    "source_sha256": __import__("hashlib").sha256(bank).hexdigest(),
                })
            manifest_dir = project / "manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "bnk.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8",
            )

            summary = runner(
                root, project, limit=2, execute=False,
                only_sources=set(relative_sources),
            )

            media_rows = [
                json.loads(line)
                for line in (manifest_dir / "bnk_media.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            dry_run_sources = {row["source"] for row in media_rows if row["status"] == "DRY_RUN"}
            self.assertEqual(summary["selected_members"], 2)
            self.assertEqual(dry_run_sources, set(relative_sources))
            self.assertEqual(sum(row["status"] == "PENDING" for row in media_rows), 2)

    def test_existing_exact_wem_gets_receipt_even_when_wav_decode_fails(self):
        module = importlib.import_module("lgpe_research.bnk_media")
        runner = getattr(module, "run_bnk_media_batch", None)
        self.assertTrue(callable(runner))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            project = folder / "LGPE-Research"
            root = folder / "game"
            relative_source = "bin/sound/bank/System_Common.bnk"
            source = root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1" / relative_source
            source.parent.mkdir(parents=True)
            bank, expected_payload = _bank_with_one_media()
            source.write_bytes(bank)
            source_hash = __import__("hashlib").sha256(bank).hexdigest()
            manifest_dir = project / "manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "bnk.jsonl").write_text(
                json.dumps({"source": relative_source, "status": "DECODED", "source_sha256": source_hash}) + "\n",
                encoding="utf-8",
            )
            wem = project / "decoded/1.0.2/romfs/bin/sound/bank/System_Common.bnk.contents/270544960.wem"
            wem.parent.mkdir(parents=True)
            wem.write_bytes(expected_payload)
            tool = project / "tools/vgmstream-cli"
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"test stub executable")

            class FailedResult:
                returncode = 7
                stdout = ""
                stderr = "unsupported test payload"

            with patch("subprocess.run", return_value=FailedResult()):
                summary = runner(root, project, limit=1, execute=True, tool=tool)

            receipt_rows = [
                json.loads(line)
                for line in (manifest_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(summary["failed_members"], 1)
            self.assertEqual(len(receipt_rows), 1)
            self.assertEqual(receipt_rows[0]["internal_path"], "270544960.wem")

    def test_prefetch_fragment_is_preserved_as_binary_without_wav_decode(self):
        module = importlib.import_module("lgpe_research.bnk_media")
        runner = getattr(module, "run_bnk_media_batch", None)
        self.assertTrue(callable(runner))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            project = folder / "LGPE-Research"
            root = folder / "game"
            relative_source = "bin/sound/bank/System_Common.bnk"
            source = root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1" / relative_source
            source.parent.mkdir(parents=True)
            full_wem = b"RIFF" + struct.pack("<I", 0x1000) + b"WAVE" + bytes(0x1000 - 4)
            fragment = full_wem[:16]
            bank = b"".join((
                _chunk(b"BKHD", struct.pack("<II", 128, 0x12345678) + bytes(12)),
                _chunk(b"DIDX", struct.pack("<III", 0x10203040, 0, len(fragment))),
                _chunk(b"DATA", fragment),
                _chunk(b"HIRC", b"\x00\x00\x00\x00"),
            ))
            source.write_bytes(bank)
            external = source.with_name("270544960.wem")
            external.write_bytes(full_wem)
            source_hash = __import__("hashlib").sha256(bank).hexdigest()
            manifest_dir = project / "manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "bnk.jsonl").write_text(
                json.dumps({"source": relative_source, "status": "DECODED", "source_sha256": source_hash}) + "\n",
                encoding="utf-8",
            )
            tool = project / "tools/vgmstream-cli"
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"test stub executable")

            with patch("subprocess.run", side_effect=AssertionError("prefetch fragments must not reach vgmstream")):
                summary = runner(root, project, limit=1, execute=True, tool=tool)

            fragment_output = project / "decoded/1.0.2/romfs/bin/sound/bank/System_Common.bnk.contents/270544960.prefetch.bin"
            wav_output = fragment_output.with_name("270544960.wav")
            media_rows = [
                json.loads(line)
                for line in (manifest_dir / "bnk_media.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            media = media_rows[0]
            receipt_rows = [
                json.loads(line)
                for line in (manifest_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(summary["unsupported_members"], 1)
            self.assertEqual(summary["failed_members"], 0)
            self.assertEqual(media["status"], "UNSUPPORTED")
            self.assertTrue(media["external_wem_prefix_matches"])
            self.assertEqual(fragment_output.read_bytes(), fragment)
            self.assertFalse(wav_output.exists())
            self.assertEqual(receipt_rows[0]["internal_path"], "270544960.prefetch.bin")

    def test_dry_run_preserves_existing_unsupported_member_status(self):
        module = importlib.import_module("lgpe_research.bnk_media")
        runner = getattr(module, "run_bnk_media_batch", None)
        self.assertTrue(callable(runner))

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            project = folder / "LGPE-Research"
            root = folder / "game"
            relative_source = "bin/sound/bank/System_Common.bnk"
            source = root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1" / relative_source
            source.parent.mkdir(parents=True)
            bank, _ = _bank_with_one_media()
            source.write_bytes(bank)
            source_hash = __import__("hashlib").sha256(bank).hexdigest()
            manifest_dir = project / "manifests"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "bnk.jsonl").write_text(
                json.dumps({"source": relative_source, "status": "DECODED", "source_sha256": source_hash}) + "\n",
                encoding="utf-8",
            )
            (manifest_dir / "bnk_media.jsonl").write_text(
                json.dumps({
                    "source": relative_source, "container_index": 0,
                    "status": "UNSUPPORTED", "unsupported_reason": "known prefetch fragment",
                }) + "\n",
                encoding="utf-8",
            )

            summary = runner(root, project, limit=1, execute=False)

            media_row = json.loads((manifest_dir / "bnk_media.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(media_row["status"], "UNSUPPORTED")
            self.assertEqual(summary["unsupported_members"], 1)
            self.assertEqual(summary["pending_members"], 0)


if __name__ == "__main__":
    unittest.main()
