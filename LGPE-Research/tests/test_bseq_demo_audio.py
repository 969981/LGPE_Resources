import hashlib
from pathlib import Path
import struct
import unittest

from lgpe_research.bseq_demo_audio import analyze_demo_audio, extract_candidates, parse_hirc_events
from lgpe_research.core import PROJECT, source_dirs


def _sequence(payload):
    return b"SESD\x03\0\0\0" + bytes(8) + payload + b"\xff" * 4


def _chunk(tag, payload):
    return tag + struct.pack("<I", len(payload)) + payload


def _bank(objects, count=None):
    return (_chunk(b"BKHD", struct.pack("<II", 128, 42))
            + _chunk(b"HIRC", struct.pack("<I", len(objects) if count is None else count)
                     + b"".join(objects)))


class DemoAudioBoundsTests(unittest.TestCase):
    def test_accepts_bounded_identifier_with_exact_offsets(self):
        raw = _sequence(bytes(16) + b"Play_test" + bytes(23))
        item, = extract_candidates(raw)
        self.assertEqual(item["literalOffset"], 32)
        self.assertEqual(item["nulOffset"], 41)
        self.assertEqual(item["literal"], "Play_test")
        self.assertEqual(item["window32Hex"], raw[32:64].hex())

    def test_rejects_embedded_unterminated_nonzero_padding_and_overlong_literals(self):
        for payload in (
            b"xPlay_test" + bytes(23),
            b"Play_" + b"x" * 27 + bytes(32),
            b"Stop_test" + b"x" * 30,
            b"Play_test\0z" + bytes(21),
            b"Play_test\0",
        ):
            with self.subTest(payload=payload):
                self.assertEqual(extract_candidates(_sequence(payload)), [])

    def test_empty_candidate_input_is_explicit(self):
        self.assertEqual(extract_candidates(_sequence(bytes(64))), [])
        with self.assertRaises(ValueError):
            extract_candidates(b"SESD\x04" + bytes(32))

    def test_hirc_reads_type4_and_raw_action_offsets(self):
        event = b"\x04" + struct.pack("<II", 9, 123) + b"\x01" + struct.pack("<I", 456)
        other = b"\x02" + struct.pack("<II", 4, 789)
        raw = _bank([event, other])
        parsed = parse_hirc_events(raw)
        self.assertEqual(list(parsed["events"]), [123])
        item = parsed["events"][123]
        self.assertEqual(item["hircType"], 4)
        self.assertEqual(item["actions"], [{"offset": 38, "id": 456}])
        self.assertEqual(struct.unpack_from("<I", raw, item["eventIdOffset"])[0], 123)

    def test_hirc_rejects_truncated_objects_counts_and_action_arrays(self):
        event = b"\x04" + struct.pack("<II", 9, 123) + b"\x01" + struct.pack("<I", 456)
        wrong_actions = b"\x04" + struct.pack("<II", 9, 123) + b"\x02" + bytes(4)
        for raw in (_bank([event])[:-1], _bank([event], count=2),
                    _bank([event, event]), _bank([wrong_actions])):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_hirc_events(raw)


class RealDemoAudioRegressionTests(unittest.TestCase):
    """Optional private-corpus checks: no game files are included in this repository."""

    @classmethod
    def setUpClass(cls):
        cls.project = PROJECT
        cls.root = PROJECT.parent
        sample = source_dirs(cls.root)["romfs"] / "bin/demo/sequence/ev0050_get.bseq"
        if not sample.is_file() or not (PROJECT / "manifests/bseq.jsonl").is_file():
            raise unittest.SkipTest("private LGPE 1.0.2 corpus/receipts unavailable")
        cls.receipt_before = hashlib.sha256((PROJECT / "manifests/bseq.jsonl").read_bytes()).hexdigest()
        cls.report = analyze_demo_audio(cls.root, cls.project)
        cls.sources = {Path(x["source"]).name: x for x in cls.report["sources"]}

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "receipt_before"):
            after = hashlib.sha256((PROJECT / "manifests/bseq.jsonl").read_bytes()).hexdigest()
            if cls.receipt_before != after:
                raise AssertionError("demo research changed the decoder manifest")

    def _assert_link(self, name, digest, offset, literal, event_id, bank, media_id):
        source = self.sources[name]
        self.assertEqual(source["sourceSha256"], digest)
        self.assertEqual(source["sourceDecoderStatus"], "UNSUPPORTED")
        item = next(x for x in source["candidates"] if x["literalOffset"] == offset)
        self.assertEqual(item["literal"], literal)
        self.assertEqual(item["eventIdFNV1_32"], event_id)
        candidate, = item["bankCandidates"]
        self.assertEqual(Path(candidate["bankSource"]).name, bank)
        self.assertEqual(candidate["hircType"], 4)
        media = candidate["eventActionRows"][0]["mediaReferences"][0]
        self.assertEqual(media["sourceId"], str(media_id))
        self.assertEqual(media["bankMedia"]["output"].split("/")[-1], f"{media_id}.wem")
        self.assertEqual(self.report["semanticsStatus"], "UNKNOWN")

    def test_exact_ev0050_link(self):
        self._assert_link("ev0050_get.bseq",
                          "5cee23f728c980c1830faefa688132f20e96e0e66ff253da5f733d18f96be2df",
                          0x18c0, "Play_ev0050_get_01", 3182649025,
                          "ev0050_get_pk.bnk", 26569135)

    def test_exact_sd9060_link(self):
        self._assert_link("sd9060_fly.bseq",
                          "c5a392549c5bb5776f19591badb05a9346d553e052cf336d4b318d953e360353",
                          0x7b8, "Play_SE_field_hiden_008_cut_in", 4184399362,
                          "System_Common.bnk", 453451329)

    def test_exact_sd9130_link(self):
        self._assert_link("sd9130_trade.bseq",
                          "86cad0876f07db9cbebd43c1cf3b9d3e609cc1dc39de124410e5161ba4284fdb",
                          0x183c, "Play_sd9130_trade_01", 689516791,
                          "sd9130_trade.bnk", 784726135)

    def test_zero_prefix_file_and_complete_private_census(self):
        source = self.sources["sd9111_evolution_after.bseq"]
        self.assertEqual(source["sourceSha256"], "3e2a832902caf2093be30735aba5aab536068ef7ca0c31a5cc69ddf2ef3640aa")
        self.assertEqual(source["status"], "NO_PREFIX_LITERAL_CANDIDATE")
        self.assertEqual(source["candidates"], [])
        summary = self.report["summary"]
        self.assertEqual(summary["sources"], 28)
        self.assertEqual(summary["literalOccurrences"], 206)
        self.assertEqual(summary["distinctLiterals"], 161)
        self.assertEqual(summary["statuses"], {"STATIC_ID_CANDIDATE": 206})
        self.assertEqual(summary["preceding2HexCounts"], {"2700": 184, "2a00": 22})


if __name__ == "__main__":
    unittest.main()
