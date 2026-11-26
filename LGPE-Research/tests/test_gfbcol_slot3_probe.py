import struct
import unittest

from lgpe_research.gfbcol_slot3_probe import inspect_slot3_words


def slot3_candidate_buffer(words=(28, 0xC2C80000, 0, 0x45160000, 0x451C4000, 0, 0x467A0000, 1), tail=(0,)):
    data = bytearray(48 + len(words) * 4 + len(tail) * 4)
    struct.pack_into("<I", data, 0, 16)
    struct.pack_into("<HHHHHH", data, 4, 12, 20, 0, 0, 0, 16)
    struct.pack_into("<i", data, 16, 12)
    # The only present root slot is slot 3; its target begins at byte 44.
    struct.pack_into("<I", data, 32, 12)
    struct.pack_into("<I", data, 44, len(words))
    struct.pack_into("<" + "I" * len(words), data, 48, *words)
    if tail:
        struct.pack_into("<" + "I" * len(tail), data, 48 + len(words) * 4, *tail)
    return bytes(data)


class GfbcolSlot3ProbeTests(unittest.TestCase):
    def test_records_raw_words_and_marks_relative_target_as_hypothesis(self):
        result = inspect_slot3_words(slot3_candidate_buffer())

        self.assertEqual(result["schema_status"], "UNKNOWN")
        self.assertEqual(result["interpretation_status"], "HYPOTHESIS_ONLY")
        self.assertEqual(result["vector_count_candidate"], 8)
        self.assertEqual([word["u32"] for word in result["words"]], [
            28, 0xC2C80000, 0, 0x45160000, 0x451C4000, 0, 0x467A0000, 1,
        ])
        candidate = result["first_word_relative_target_candidate"]
        self.assertEqual(candidate["target_offset"], 76)
        self.assertEqual(candidate["target_u32_candidate"], 1)
        self.assertTrue(candidate["extent_in_bounds"])
        self.assertEqual(candidate["raw_words"], [0])

    def test_reports_out_of_bounds_target_without_assigning_a_type(self):
        data = slot3_candidate_buffer(words=(0xFFFFFFFC, 0, 0, 0, 0, 0, 0, 1))
        result = inspect_slot3_words(data)

        candidate = result["first_word_relative_target_candidate"]
        self.assertFalse(candidate["target_in_bounds"])
        self.assertIsNone(candidate["target_u32_candidate"])
        self.assertEqual(result["schema_status"], "UNKNOWN")

    def test_rejects_non_eight_word_slot_three_candidate(self):
        with self.assertRaisesRegex(ValueError, "expected 8 candidate words"):
            inspect_slot3_words(slot3_candidate_buffer(words=(28, 1)))


if __name__ == "__main__":
    unittest.main()
