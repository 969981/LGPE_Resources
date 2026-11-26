import unittest

from lgpe_research.encounter_weights import probability_intervals


class EncounterWeightTests(unittest.TestCase):
    def test_builds_half_open_intervals_and_retains_zero_weight_slots(self):
        rows = probability_intervals([30, 0, 70], 100)
        self.assertEqual(rows, [
            {"slot_index": 0, "roll_start_inclusive": 0, "roll_end_exclusive": 30, "probability": 30},
            {"slot_index": 1, "roll_start_inclusive": 30, "roll_end_exclusive": 30, "probability": 0},
            {"slot_index": 2, "roll_start_inclusive": 30, "roll_end_exclusive": 100, "probability": 70},
        ])

    def test_zero_total_produces_empty_intervals(self):
        self.assertEqual(
            probability_intervals([0, 0], 0),
            [
                {"slot_index": 0, "roll_start_inclusive": 0, "roll_end_exclusive": 0, "probability": 0},
                {"slot_index": 1, "roll_start_inclusive": 0, "roll_end_exclusive": 0, "probability": 0},
            ],
        )

    def test_rejects_bad_totals_and_negative_weights(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            probability_intervals([40, 50], 100)
        with self.assertRaisesRegex(ValueError, "negative"):
            probability_intervals([110, -10], 100)
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            probability_intervals([101], 101)


if __name__ == "__main__":
    unittest.main()
