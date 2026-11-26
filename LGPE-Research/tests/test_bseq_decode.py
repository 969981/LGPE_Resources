import unittest

from lgpe_research.bseq_decode import (
    decode_bseq_bytes,
    demo_sequence_unsupported_reason,
    format_exception_chain,
    parser_failure_diagnostic,
)


class _FakeParsedSequence:
    def get_json_dict_simple(self, seq_name="", opts_setting=1):
        return {
            "Metadata": {"Game": "LGPE", "Name": seq_name},
            "Data": [{"GrpNo": 0, "GroupOptions": {"Option0": 0}, "Commands": []}],
        }

    def get_bseq(self):
        return b"SESD\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff"


class _FakeSESD:
    @classmethod
    def from_bytes(cls, data, game, ref):
        if game != "LGPE" or ref != "fake-reference":
            raise ValueError("unexpected parser configuration")
        if data[:4] != b"SESD":
            raise ValueError("bad magic")
        return _FakeParsedSequence()


class BseqDecodeTests(unittest.TestCase):
    def test_exception_chain_preserves_parser_cause_hidden_by_upstream_handler(self):
        try:
            try:
                b"\x80".decode("utf-8")
            except UnicodeDecodeError as cause:
                raise NameError("name 'i' is not defined") from cause
        except NameError as exc:
            rendered = format_exception_chain(exc)
        self.assertIn("NameError: name 'i' is not defined", rendered)
        self.assertIn("UnicodeDecodeError: 'utf-8' codec can't decode", rendered)
        self.assertLess(rendered.index("NameError"), rendered.index("UnicodeDecodeError"))

    def test_exception_chain_stops_on_a_cyclic_context(self):
        error = RuntimeError("cycle")
        error.__context__ = error
        self.assertEqual(format_exception_chain(error), "RuntimeError: cycle")

    def test_parser_diagnostic_records_unknown_string_bytes_and_command_header(self):
        class Param:
            names = ["rawLikeString"]
            value_type = "String"
            length = 16

        source = b"SESD" + b"\x03\0\0\0" + bytes(8) + bytes(range(16))

        def from_bytes():
            offset = 16
            cmd_id = "2D00"
            crsr = 32
            opts = {"Option0": 0, "Option1": 0}
            param = Param()
            arg_bytes = b"\x80data:/demo/res/item.gfbcam\0"
            try:
                arg_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise NameError("upstream formatter failed")

        try:
            from_bytes()
        except NameError as exc:
            result = parser_failure_diagnostic(exc, source)
        self.assertEqual(result["command_offset"], 16)
        self.assertEqual(result["command_id_hex"], "2D00")
        self.assertEqual(result["command_header_raw_hex"], source[16:32].hex())
        self.assertEqual(result["parser_parameter"], {
            "name": "rawLikeString", "value_type": "String", "length": 16,
        })
        self.assertEqual(result["parameter_bytes"]["length"], 28)
        self.assertIn("data:/demo/res/item.gfbcam", result["nearby_ascii_runs"])
        self.assertEqual(result["cause"]["type"], "UnicodeDecodeError")

    def test_parser_diagnostic_records_unmapped_raw_command_id(self):
        source = b"SESD" + b"\x03\0\0\0" + bytes(8) + b"\0" * 14 + b"ta"

        def from_bytes():
            offset = 16
            cmd_id = "7461"
            crsr = 32
            opts = {"Option0": 0, "Option1": 0}
            raise KeyError(cmd_id)

        try:
            from_bytes()
        except KeyError as exc:
            result = parser_failure_diagnostic(exc, source)
        self.assertEqual(result["command_offset"], 16)
        self.assertEqual(result["command_id_hex"], "7461")
        self.assertEqual(result["lookup_key"], "7461")
        self.assertEqual(result["command_header_raw_hex"], source[16:32].hex())

    def test_only_the_observed_demo_sequence_tree_uses_the_upstream_unsupported_gate(self):
        self.assertIsNotNone(demo_sequence_unsupported_reason("bin/demo/sequence/ev0050_get.bseq"))
        self.assertIsNone(demo_sequence_unsupported_reason("bin/battle/waza/sequence/ew063.bseq"))

    def test_raw_bytes_are_retained_when_parser_normalizes_serialization(self):
        original = b"SESD\x03\x00\x00\x00" + bytes(8) + b"opaque-tail"
        result = decode_bseq_bytes(
            original, "sample", _FakeSESD, "fake-reference", "dictionary-hash",
        )
        self.assertEqual(result["source"]["raw_hex"], original.hex())
        self.assertEqual(result["source"]["size"], len(original))
        self.assertFalse(result["validation"]["byte_roundtrip_exact"])
        self.assertTrue(result["validation"]["semantic_roundtrip_equal"])
        self.assertEqual(result["decoder"]["command_dictionary_sha256"], "dictionary-hash")

    def test_rejects_non_sesd_and_wrong_lgpe_version(self):
        with self.assertRaisesRegex(ValueError, "not a complete SESD"):
            decode_bseq_bytes(b"NOPE" + bytes(12), "bad", _FakeSESD, "fake-reference")
        with self.assertRaisesRegex(ValueError, "not the LGPE version 3"):
            decode_bseq_bytes(b"SESD\x04\x00\x00\x00" + bytes(8), "bad", _FakeSESD, "fake-reference")


if __name__ == "__main__":
    unittest.main()
