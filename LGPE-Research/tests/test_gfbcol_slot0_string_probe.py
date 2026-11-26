import struct
import unittest

from lgpe_research.gfbcol_slot0_probe import inspect_slot0_string_candidates


def slot0_string_buffer(value=b"col_wall", terminator=b"\0", object_bytes=8, relative_offset=16):
    data = bytearray(max(93, 60 + object_bytes))
    struct.pack_into("<I", data, 0, 16)
    struct.pack_into("<HHH", data, 4, 6, 20, 4)
    struct.pack_into("<iI", data, 16, 12, 20)
    struct.pack_into("<II", data, 40, 1, 16)
    struct.pack_into("<HHH", data, 52, 6, object_bytes, 4)
    struct.pack_into("<iI", data, 60, 8, relative_offset)
    struct.pack_into("<I", data, 80, len(value))
    data[84:84 + len(value)] = value
    data[84 + len(value):84 + len(value) + len(terminator)] = terminator
    return bytes(data[:max(84 + len(value) + len(terminator), 60 + object_bytes)])


class GfbcolSlot0StringProbeTests(unittest.TestCase):
    def test_decodes_length_prefixed_nul_terminated_utf8_candidate(self):
        result = inspect_slot0_string_candidates(slot0_string_buffer())

        self.assertEqual(result["schema_status"], "UNKNOWN")
        self.assertFalse(result["field_types_assigned"])
        self.assertEqual(result["root_slot_classification"], "VECTOR_OF_VALID_TABLE_ENVELOPES")
        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE")
        self.assertEqual(candidate["decoded_text"], "col_wall")
        self.assertEqual(candidate["raw_bytes_hex"], "636f6c5f77616c6c")
        self.assertEqual(candidate["target_offset"], 80)
        self.assertEqual(candidate["length"], 8)

    def test_preserves_invalid_utf8_as_unresolved(self):
        result = inspect_slot0_string_candidates(slot0_string_buffer(b"\xff"))

        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UNRESOLVED")
        self.assertIn("UTF-8", candidate["reason"])
        self.assertEqual(candidate["raw_bytes_hex"], "ff")

    def test_rejects_unterminated_length_prefixed_bytes(self):
        result = inspect_slot0_string_candidates(slot0_string_buffer(terminator=b"!"))

        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UNRESOLVED")
        self.assertIn("NUL", candidate["reason"])

    def test_does_not_read_a_four_byte_offset_across_the_child_object_boundary(self):
        result = inspect_slot0_string_candidates(slot0_string_buffer(object_bytes=5))

        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UNRESOLVED")
        self.assertIn("complete four-byte", candidate["reason"])

    def test_rejects_unaligned_string_target_candidate(self):
        result = inspect_slot0_string_candidates(slot0_string_buffer(relative_offset=17))

        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UNRESOLVED")
        self.assertIn("unaligned", candidate["reason"])

    def test_rejects_candidate_string_extent_overlapping_child_table(self):
        result = inspect_slot0_string_candidates(slot0_string_buffer(object_bytes=36))

        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UNRESOLVED")
        self.assertIn("overlaps", candidate["reason"])

    def test_rejects_oversized_candidate_length(self):
        data = bytearray(slot0_string_buffer())
        struct.pack_into("<I", data, 80, 0x7FFFFFFF)
        result = inspect_slot0_string_candidates(bytes(data))

        candidate = result["elements"][0]["string_candidate"]
        self.assertEqual(candidate["classification"], "UNRESOLVED")
        self.assertIn("outside the buffer", candidate["reason"])


if __name__ == "__main__":
    unittest.main()
