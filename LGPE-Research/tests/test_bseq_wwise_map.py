import unittest

from lgpe_research.bseq_wwise_map import (
    _candidate_status,
    _load_bank_references,
    _play_commands,
    fnv1_32,
)


class BseqWwiseMapTests(unittest.TestCase):
    def test_uses_lowercase_utf8_fnv1_not_fnv1a(self):
        self.assertEqual(fnv1_32(""), 2166136261)
        self.assertEqual(fnv1_32("Play_SE_w0132"), 532430182)
        self.assertEqual(fnv1_32("Play_SE_w0132"), fnv1_32("play_se_W0132"))

    def test_extracts_exact_sequence_bank_and_event_literals_with_indexes(self):
        sequence = {
            "Data": [
                {"Commands": [
                    {"Name": "BelugaSoundLoadBank", "Parameters": {"name": "Waza_ew0063"}},
                    {"Name": "BelugaSoundPlaySe", "StartFrame": 1, "EndFrame": 1,
                     "Parameters": {"event": "Play_SE_w0132", "is3d": 0}},
                ]},
            ],
        }
        self.assertEqual(_load_bank_references(sequence), [{
            "groupIndex": 0, "commandIndex": 0, "literal": "Waza_ew0063",
        }])
        event = _play_commands(sequence)[0]
        self.assertEqual(event["groupIndex"], 0)
        self.assertEqual(event["commandIndex"], 1)
        self.assertEqual(event["startFrame"], 1)
        self.assertEqual(event["eventLiteral"], "Play_SE_w0132")
        self.assertEqual(event["eventIdFNV1_32"], 532430182)
        self.assertEqual(event["parserParameters"], {"event": "Play_SE_w0132", "is3d": 0})

    def test_reports_referenced_unique_ambiguous_global_only_and_missing_matches(self):
        one = {"bankSource": "bin/sound/Waza_ew0063.bnk", "eventIndex": "13"}
        other = {"bankSource": "bin/sound/System_Common.bnk", "eventIndex": "545"}
        self.assertEqual(
            _candidate_status([one], {one["bankSource"]})[0],
            "STATIC_ID_MATCH_IN_SEQUENCE_REFERENCED_BANK",
        )
        self.assertEqual(
            _candidate_status([one, {**one, "eventIndex": "14"}], {one["bankSource"]})[0],
            "AMBIGUOUS_STATIC_ID_MATCH_IN_SEQUENCE_BANKS",
        )
        self.assertEqual(
            _candidate_status([other], {one["bankSource"]})[0],
            "STATIC_ID_MATCH_ONLY_OUTSIDE_SEQUENCE_BANKS",
        )
        self.assertEqual(_candidate_status([], {one["bankSource"]})[0], "NO_STATIC_ID_MATCH")


if __name__ == "__main__":
    unittest.main()
