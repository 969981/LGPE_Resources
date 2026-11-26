import csv
import hashlib
import io
import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from lgpe_research import batch
from lgpe_research.coverage import build_coverage
from lgpe_research.core import VERSION, NCA, decode_destination


def _chunk(tag: bytes, payload: bytes) -> bytes:
    pad = b"\x00" if len(payload) & 1 else b""
    return tag + struct.pack("<I", len(payload)) + payload + pad


def _wave(fmt_tag: int, *, fact_samples: int | None = 500) -> bytes:
    if fmt_tag == 2:
        fmt = (
            struct.pack("<HHIIHHHHH", 2, 1, 16000, 8000, 512, 4, 32, 500, 7)
            + struct.pack("<14h", 256, 0, 512, -256, 0, 0, 192, 64, 240, 0, 460, -208, 392, -232)
        )
    else:
        fmt = struct.pack("<HHIIHH", fmt_tag, 1, 16000, 32000, 2, 16)
    chunks = [_chunk(b"fmt ", fmt)]
    if fact_samples is not None:
        chunks.append(_chunk(b"fact", struct.pack("<I", fact_samples)))
    chunks.append(_chunk(b"data", bytes(512 if fmt_tag == 2 else 2)))
    body = b"WAVE" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _pcm16_wave(frames: int = 500) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(struct.pack(f"<{frames}h", *range(frames)))
    return output.getvalue()


class WaveAudioTests(unittest.TestCase):
    def test_parser_reports_microsoft_adpcm_chunks_and_sample_count(self):
        parser = getattr(batch, "parse_wave_source", None)
        self.assertTrue(callable(parser), "batch must expose the RIFF/WAVE source inspector")

        result = parser(_wave(2, fact_samples=500))

        self.assertEqual(result["format_tag"], 2)
        self.assertEqual(result["codec"], "Microsoft ADPCM")
        self.assertEqual(result["channels"], 1)
        self.assertEqual(result["sample_rate"], 16000)
        self.assertEqual(result["bits_per_sample"], 4)
        self.assertEqual(result["block_align"], 512)
        self.assertEqual(result["fact_samples"], 500)
        self.assertEqual(result["data_bytes"], 512)

    def test_parser_rejects_chunk_past_declared_riff_boundary(self):
        parser = getattr(batch, "parse_wave_source", None)
        self.assertTrue(callable(parser), "batch must expose the RIFF/WAVE source inspector")
        malformed = _wave(2)[:-1]

        with self.assertRaisesRegex(ValueError, "RIFF|chunk|truncated"):
            parser(malformed)

    def test_batch_writes_path_mirrored_pcm16_and_reuses_verified_output(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            game_root = workspace / "game"
            project = workspace / "project"
            rel = "bin/app/palma/wave/sample_adpcm.wav"
            source = game_root / VERSION / NCA / "1" / rel
            source.parent.mkdir(parents=True)
            source_bytes = _wave(2, fact_samples=500)
            source.write_bytes(source_bytes)
            scan = project / "manifests" / "files.csv"
            scan.parent.mkdir(parents=True)
            with scan.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": rel, "suffix": ".wav", "kind": "audio-wave",
                    "bytes": len(source_bytes), "signature": "RIFF", "header_hex": "",
                })
            tool = workspace / "vgmstream-cli"
            tool.write_bytes(b"test executable identity")

            def decode(command, **kwargs):
                output = Path(command[command.index("-o") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(output), "wb") as stream:
                    stream.setnchannels(1)
                    stream.setsampwidth(2)
                    stream.setframerate(16000)
                    stream.writeframes(struct.pack("<500h", *range(500)))
                return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            with patch("subprocess.run", side_effect=decode) as run:
                summary = batch.run_wave_batch(
                    game_root, project, limit=1, execute=True, tool=tool,
                )
            self.assertEqual(summary["decoded"], 1)
            self.assertEqual(summary["failed"], 0)
            run.assert_called_once()
            target = decode_destination("romfs", rel, ".wav", project)
            self.assertTrue(target.is_file())
            self.assertEqual(target.relative_to(project / "decoded" / VERSION / "romfs").as_posix(), rel)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), hashlib.sha256(source_bytes).hexdigest())
            with wave.open(str(target), "rb") as stream:
                self.assertEqual((stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()), (1, 2, 16000, 500))

            manifest = project / "manifests" / "waves.jsonl"
            row = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["status"], "DECODED")
            self.assertEqual(row["source_sha256"], hashlib.sha256(source_bytes).hexdigest())
            self.assertEqual(row["output_sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
            receipt = json.loads((project / "manifests" / "outputs.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(receipt["relative_source"], rel)
            self.assertEqual(receipt["output_file"], str(target))

            with patch("subprocess.run", side_effect=AssertionError("verified output should be reused")):
                repeated = batch.run_wave_batch(
                    game_root, project, limit=1, execute=True, tool=tool,
                )
            self.assertEqual(repeated["decoded"], 1)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])["status"], "DECODED_EXISTING_VERIFIED")
            coverage = build_coverage(project)
            self.assertEqual(coverage["decoded_sources"], 1)
            self.assertEqual(coverage["decoded_outputs"], 1)

    def test_batch_keeps_native_pcm_unknown_without_claiming_conversion(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            game_root = workspace / "game"
            project = workspace / "project"
            rel = "bin/app/palma/wave/native_pcm.wav"
            source = game_root / VERSION / NCA / "1" / rel
            source.parent.mkdir(parents=True)
            source_bytes = _wave(1, fact_samples=None)
            source.write_bytes(source_bytes)
            scan = project / "manifests" / "files.csv"
            scan.parent.mkdir(parents=True)
            with scan.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": rel, "suffix": ".wav", "kind": "audio-wave",
                    "bytes": len(source_bytes), "signature": "RIFF", "header_hex": "",
                })
            with patch("subprocess.run", side_effect=AssertionError("PCM must not be mislabeled as a conversion")):
                summary = batch.run_wave_batch(game_root, project, limit=1, execute=True)

            self.assertEqual(summary["unknown"], 1)
            self.assertEqual(summary["decoded"], 0)
            self.assertFalse(decode_destination("romfs", rel, ".wav", project).exists())
            row = json.loads((project / "manifests" / "waves.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["status"], "UNKNOWN")
            self.assertIn("already PCM", row["reason"])
            coverage = build_coverage(project)
            self.assertEqual(coverage["unknown_sources"], 1)
            self.assertEqual(coverage["decoded_sources"], 0)

    def test_batch_adopts_unreceipted_output_only_after_exact_redecode(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            game_root = workspace / "game"
            project = workspace / "project"
            rel = "bin/app/palma/wave/preexisting_adpcm.wav"
            source = game_root / VERSION / NCA / "1" / rel
            source.parent.mkdir(parents=True)
            source_bytes = _wave(2, fact_samples=500)
            source.write_bytes(source_bytes)
            scan = project / "manifests" / "files.csv"
            scan.parent.mkdir(parents=True)
            with scan.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": rel, "suffix": ".wav", "kind": "audio-wave",
                    "bytes": len(source_bytes), "signature": "RIFF", "header_hex": "",
                })
            tool = workspace / "vgmstream-cli"
            tool.write_bytes(b"test executable identity")
            target = decode_destination("romfs", rel, ".wav", project)
            target.parent.mkdir(parents=True)
            pcm_bytes = _pcm16_wave()
            target.write_bytes(pcm_bytes)

            def decode(command, **kwargs):
                output = Path(command[command.index("-o") + 1])
                output.write_bytes(pcm_bytes)
                return type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            with patch("subprocess.run", side_effect=decode) as run:
                summary = batch.run_wave_batch(
                    game_root, project, limit=1, execute=True, tool=tool,
                )

            self.assertEqual(summary["decoded"], 1)
            self.assertEqual(summary["failed"], 0)
            run.assert_called_once()
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), hashlib.sha256(pcm_bytes).hexdigest())
            row = json.loads((project / "manifests" / "waves.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["status"], "DECODED_EXISTING_VERIFIED")
            receipt = json.loads((project / "manifests" / "outputs.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(receipt["status"], "DECODED_EXISTING_VERIFIED")

    def test_batch_preserves_stale_partial_not_created_by_current_run(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            game_root = workspace / "game"
            project = workspace / "project"
            rel = "bin/app/palma/wave/stale_partial_adpcm.wav"
            source = game_root / VERSION / NCA / "1" / rel
            source.parent.mkdir(parents=True)
            source_bytes = _wave(2, fact_samples=500)
            source.write_bytes(source_bytes)
            scan = project / "manifests" / "files.csv"
            scan.parent.mkdir(parents=True)
            with scan.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": rel, "suffix": ".wav", "kind": "audio-wave",
                    "bytes": len(source_bytes), "signature": "RIFF", "header_hex": "",
                })
            tool = workspace / "vgmstream-cli"
            tool.write_bytes(b"test executable identity")
            target = decode_destination("romfs", rel, ".wav", project)
            target.parent.mkdir(parents=True)
            partial = target.with_name(target.stem + ".lgpe.partial.wav")
            partial_bytes = b"preserve unowned partial"
            partial.write_bytes(partial_bytes)

            with patch("subprocess.run", side_effect=AssertionError("stale partial must stop before decode")):
                summary = batch.run_wave_batch(
                    game_root, project, limit=1, execute=True, tool=tool,
                )

            self.assertEqual(summary["failed"], 1)
            self.assertEqual(partial.read_bytes(), partial_bytes)
            row = json.loads((project / "manifests" / "waves.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["status"], "FAILED")
            self.assertIn("stale partial", row["error"])


if __name__ == "__main__":
    unittest.main()
