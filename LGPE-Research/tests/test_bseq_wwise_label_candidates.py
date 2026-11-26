import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.bseq_wwise_map import (
    MAPPING_METHOD,
    SEMANTICS,
    SCHEMA,
    WWISER_COMMIT,
    build_sequence_event_literal_candidates,
    fnv1_32,
    write_sequence_event_literal_candidates,
)


PARSER_COMMIT = "6f122d1b7945797cae472960b798bf28523f8acd"
HASH_A = "a" * 64
HASH_B = "b" * 64


def _event_candidate(bank_source, bank_id, event_id, event_literal):
    return {
        "bankId": str(bank_id),
        "bankSource": bank_source,
        "bankSourceSha256": HASH_A if bank_id == 100 else HASH_B,
        "bankStem": Path(bank_source).stem,
        "bankXml": "decoded/1.0.2/romfs/" + str(Path(bank_source).with_suffix(".xml")),
        "bankXmlSha256": HASH_B if bank_id == 100 else HASH_A,
        "eventActionRowCount": 1,
        "eventActionStatuses": ["STATIC_REACHABILITY_WITH_MEDIA_ID"],
        "eventId": str(event_id),
        "eventIdHex": f"0x{event_id:08x}",
        "eventIndex": "4",
        "eventName": None,
        "eventNameStatus": "UNKNOWN_WWNAMES_DB_ABSENT",
        "mediaReferenceCount": 0,
        "mediaReferences": [],
    }


def _map_row(event_literal="Play_SE_test"):
    event_id = fnv1_32(event_literal)
    first = _event_candidate(
        "bin/sound/NX64/wwise/bank/BankA.bnk", 100, event_id, event_literal,
    )
    second = _event_candidate(
        "bin/sound/NX64/wwise/bank/BankB.bnk", 200, event_id, event_literal,
    )
    return {
        "schema": SCHEMA,
        "method": MAPPING_METHOD,
        "semanticsStatus": SEMANTICS,
        "sourceVersion": "Let's Go Pikachu 1.0.2",
        "sequenceSource": "bin/demo/sequence/test.bseq",
        "sequenceSourceSha256": HASH_A,
        "sequenceOutput": "decoded/1.0.2/romfs/bin/demo/sequence/test.json",
        "sequenceOutputSha256": HASH_B,
        "sequenceParserCommit": PARSER_COMMIT,
        "commandDictionarySha256": HASH_A,
        "groupIndex": 0,
        "commandIndex": 3,
        "startFrame": 8,
        "endFrame": 12,
        "eventLiteral": event_literal,
        "parserParameters": {"event": event_literal, "is3d": 1},
        "eventIdFNV1_32": event_id,
        "eventIdHex": f"0x{event_id:08x}",
        "hashBasis": {
            "algorithm": "FNV-1 32-bit",
            "input": "lowercase eventLiteral encoded as UTF-8",
            "implementationSource": "pinned wwiser wfnv.py",
            "wwiserCommit": WWISER_COMMIT,
        },
        "sequenceBankNameReferences": [],
        "matchingSequenceBankSources": [first["bankSource"]],
        "staticMatchStatus": "STATIC_ID_MATCH_IN_SEQUENCE_REFERENCED_BANK",
        "sequenceBankCandidateCount": 1,
        "globalCandidateCount": 2,
        "sequenceBankCandidates": [first],
        "globalCandidates": [first, second],
    }


class BseqWwiseLabelCandidateTests(unittest.TestCase):
    def test_builds_bank_event_label_candidates_without_assigning_event_names(self):
        rows = [_map_row()]

        candidates, summary = build_sequence_event_literal_candidates(rows)

        self.assertEqual(summary["sequenceRows"], 1)
        self.assertEqual(summary["globalCandidateLinks"], 2)
        self.assertEqual(summary["candidateBankEventPairs"], 2)
        self.assertEqual(summary["sequenceReferencedBankLinks"], 1)
        self.assertEqual(summary["outsideSequenceBankLinks"], 1)
        by_bank = {item["bankSource"]: item for item in candidates}
        bank_a = by_bank["bin/sound/NX64/wwise/bank/BankA.bnk"]
        bank_b = by_bank["bin/sound/NX64/wwise/bank/BankB.bnk"]
        self.assertEqual(
            bank_a["bankXml"],
            "decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/BankA.xml",
        )
        self.assertEqual(bank_a["sequenceLiteralCandidates"][0]["literal"], "Play_SE_test")
        self.assertEqual(
            bank_a["sequenceLiteralCandidates"][0]["observations"][0]["candidateScope"],
            "SEQUENCE_REFERENCED_BANK_ID_CANDIDATE",
        )
        self.assertEqual(
            bank_b["sequenceLiteralCandidates"][0]["observations"][0]["candidateScope"],
            "OUTSIDE_SEQUENCE_BANKS_ID_CANDIDATE",
        )
        self.assertIsNone(bank_a["eventName"])
        self.assertEqual(bank_a["eventNameStatus"], "UNKNOWN_WWNAMES_DB_ABSENT")
        self.assertFalse(bank_a["eventNameWasUpdated"])

    def test_groups_repeated_observations_for_one_bank_event_pair(self):
        first = _map_row()
        second = _map_row()
        second["sequenceSource"] = "bin/demo/sequence/other.bseq"
        second["sequenceSourceSha256"] = HASH_B
        second["sequenceOutput"] = "decoded/1.0.2/romfs/bin/demo/sequence/other.json"

        candidates, summary = build_sequence_event_literal_candidates([first, second])

        self.assertEqual(len(candidates), 2)
        self.assertEqual(summary["sequenceRows"], 2)
        self.assertEqual(summary["candidateBankEventPairs"], 2)
        for candidate in candidates:
            self.assertEqual(len(candidate["sequenceLiteralCandidates"]), 1)
            self.assertEqual(
                len(candidate["sequenceLiteralCandidates"][0]["observations"]), 2,
            )

    def test_rejects_literal_hash_mismatch(self):
        row = _map_row()
        row["eventIdFNV1_32"] ^= 1

        with self.assertRaisesRegex(ValueError, "FNV-1 32-bit value"):
            build_sequence_event_literal_candidates([row])

    def test_writer_records_input_rows_hash_and_atomic_jsonl_output(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)

            summary = write_sequence_event_literal_candidates(project, [_map_row()])

            output = project / "manifests" / "wwise_sequence_event_label_candidates.jsonl"
            summary_path = project / "manifests" / "wwise_sequence_event_label_candidates.summary.json"
            output_bytes = output.read_bytes()
            summary_bytes = summary_path.read_bytes()
            self.assertNotIn(b"\r\n", output_bytes)
            self.assertNotIn(b"\r\n", summary_bytes)
            rows = [json.loads(line) for line in output_bytes.decode("utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(summary["manifestSha256"], hashlib.sha256(output_bytes).hexdigest())
            self.assertEqual(json.loads(summary_bytes.decode("utf-8")), summary)
            self.assertTrue(all("eventNameWasUpdated" in row and not row["eventNameWasUpdated"] for row in rows))


if __name__ == "__main__":
    unittest.main()
