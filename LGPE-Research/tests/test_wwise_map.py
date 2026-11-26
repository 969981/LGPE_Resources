from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lgpe_research.wwise_map import (
    _make_bank_media_index,
    map_bank_events,
    map_unreferenced_wem_hirc_objects,
    parse_wwiser_bank,
)


def bank_xml(bank_id: int, objects: str) -> str:
    return f'''<root version="128">
  <object name="BankHeader"><object name="AkBankHeader">
    <field offset="12" type="sid" name="dwSoundBankID" value="{bank_id}" />
  </object></object>
  <object name="HircChunk"><list name="listLoadedItem">{objects}</list></object>
</root>'''


EVENT_ACTION = '''<object name="CAkEvent" index="0">
  <field offset="100" name="ulID" value="100" />
  <object name="EventInitialValues"><list name="actions">
    <object name="Action" index="0"><field offset="104" type="tid" name="ulActionID" value="200" /></object>
  </list></object>
</object>
<object name="CAkActionPlay" index="1">
  <field offset="200" name="ulID" value="200" />
  <field offset="204" name="ulActionType" value="1027" valuefmt="Play" />
  <object name="ActionInitialValues">
    <field offset="210" type="tid" name="idExt" value="300" />
    <object name="PlayActionParams"><field offset="220" type="tid" name="bankID" value="20" /></object>
  </object>
</object>'''


TARGET_AND_SOUND = '''<object name="CAkRanSeqCntr" index="2">
  <field offset="300" name="ulID" value="300" />
  <object name="Children"><list>
    <object index="0"><field offset="310" type="tid" name="ulChildID" value="400" /></object>
  </list></object>
</object>
<object name="CAkSound" index="3">
  <field offset="400" name="ulID" value="400" />
  <object name="SoundInitialValues"><object name="AkBankSourceData">
    <field offset="420" name="StreamType" value="2" />
    <object name="AkMediaInformation">
      <field offset="430" type="tid" name="sourceID" value="12345" />
      <field offset="438" name="uInMemoryMediaSize" value="99" />
    </object>
  </object></object>
</object>'''


class WwiseEventMediaMapTests(unittest.TestCase):
    def parse(self, directory: Path, bank_id: int, objects: str, name: str):
        path = directory / name
        path.write_text(bank_xml(bank_id, objects), encoding="utf-8")
        return parse_wwiser_bank(path, name)

    def test_unreferenced_wems_distinguish_hirc_sourceid_from_no_hirc_match(self):
        bank = {
            "source": "bin/sound/bank/test.bnk",
            "sourceSha256": "bank-hash",
            "xmlRelative": "decoded/1.0.2/romfs/bin/sound/bank/test.xml",
            "xmlSha256": "xml-hash",
            "bankId": "20",
            "bankVersion": "128",
            "objects": [{
                "objectId": "400", "objectIndex": "3", "className": "CAkSound",
                "media": [{
                    "sourceId": "12345",
                    "sourceIdField": {"name": "sourceID", "offset": 430, "value": "12345"},
                    "streamType": "2", "hasSourceFlag": "1",
                }],
            }],
        }
        wem_index = {
            "12345": [{"source": "bin/sound/12345.wem", "sourceSha256": "wem-a", "audioReceiptStatus": "DECODED"}],
            "67890": [{"source": "bin/sound/67890.wem", "sourceSha256": "wem-b", "audioReceiptStatus": "DECODED"}],
        }
        event_rows = [{"mediaReferences": [{
            "wemMatchStatus": "MATCHED_DECIMAL_WEM_MANIFEST_NAME",
            "wem": {"source": "bin/sound/67890.wem"},
        }]}]

        rows = map_unreferenced_wem_hirc_objects([bank], wem_index, event_rows)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["wemSource"], "bin/sound/12345.wem")
        self.assertEqual(rows[0]["status"], "STATIC_HIRC_OBJECT_NOT_REACHED_FROM_MAPPED_EVENTS")
        self.assertEqual(rows[0]["hircMatches"][0]["hircObjectId"], "400")
        self.assertEqual(rows[0]["hircMatches"][0]["sourceIdField"]["offset"], 430)

        no_match = map_unreferenced_wem_hirc_objects([], {"12345": wem_index["12345"]}, [])
        self.assertEqual(no_match[0]["status"], "NO_LOCAL_HIRC_SOURCEID_MATCH")

    def test_event_action_cross_bank_target_reaches_exact_wem_stem(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source_bank = self.parse(folder, 10, EVENT_ACTION, "event.xml")
            media_bank = self.parse(folder, 20, TARGET_AND_SOUND, "media.xml")
            for bank in (source_bank, media_bank):
                bank["sourceSha256"] = "source-hash"
                bank["xmlRelative"] = f"decoded/{bank['source']}"
            wem_index = {
                "12345": [{
                    "source": "bin/sound/wwise/bank/12345.wem",
                    "sourceSha256": "wem-source-hash",
                    "audioReceiptStatus": "DECODED",
                    "wav": "decoded/1.0.2/romfs/bin/sound/wwise/bank/12345.wav",
                    "wavSha256": "wav-hash",
                }]
            }

            rows = map_bank_events([source_bank, media_bank], wem_index)

            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["eventId"], "100")
            self.assertEqual(row["actionClass"], "CAkActionPlay")
            self.assertEqual(row["targetObjectResolution"], "DECLARED_BANK_ID_AND_HIRC_ID")
            self.assertEqual(row["status"], "STATIC_REACHABILITY_WITH_WEM_MANIFEST_ENTRY")
            self.assertEqual(row["matchedWemReferenceCount"], 1)
            self.assertEqual(row["receiptBackedWavReferenceCount"], 1)
            self.assertEqual(row["mediaReferences"][0]["wem"]["source"], "bin/sound/wwise/bank/12345.wem")
            self.assertIsNone(row["eventName"])

    def test_unmatched_media_id_stays_explicit_and_raw_offset_is_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            bank = self.parse(folder, 20, EVENT_ACTION + TARGET_AND_SOUND, "bank.xml")
            bank["sourceSha256"] = "source-hash"
            bank["xmlRelative"] = "decoded/bank.xml"
            rows = map_bank_events([bank], {})

            self.assertEqual(rows[0]["status"], "STATIC_REACHABILITY_WITH_MEDIA_ID")
            self.assertEqual(rows[0]["mediaReferences"][0]["sourceId"], "12345")
            self.assertIsNone(rows[0]["mediaReferences"][0]["wem"])
            self.assertEqual(rows[0]["mediaReferences"][0]["sourceIdField"]["offset"], 430)

    def test_source_id_joins_only_same_bank_didx_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source_bank = self.parse(folder, 10, EVENT_ACTION, "event.xml")
            media_bank = self.parse(folder, 20, TARGET_AND_SOUND, "media.xml")
            for bank in (source_bank, media_bank):
                bank["sourceSha256"] = "source-hash"
                bank["xmlRelative"] = f"decoded/{bank['source']}"
            internal_index = _make_bank_media_index([{
                "bank_id": 20,
                "media_id": 12345,
                "source": "bin/sound/media.bnk",
                "source_sha256": "bank-hash",
                "container_index": 0,
                "index_record_hex": "393000000000000063000000",
                "data_offset": 0,
                "size_bytes": 99,
                "extract_status": "DECODED",
                "output": "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.wem",
                "output_sha256": "embedded-wem-hash",
                "wav_status": "DECODED",
                "wav_output": "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.wav",
                "wav_output_sha256": "embedded-wav-hash",
            }])

            rows = map_bank_events([source_bank, media_bank], {}, internal_index)

            media = rows[0]["mediaReferences"][0]
            self.assertEqual(media["sourceBankId"], "20")
            self.assertEqual(media["bankMediaMatchStatus"], "MATCHED_INTERNAL_MEDIA_AND_WAV")
            self.assertEqual(media["bankMedia"]["output"], "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.wem")
            self.assertEqual(media["bankMedia"]["outputSha256"], "embedded-wem-hash")
            self.assertEqual(media["bankMedia"]["wavOutputSha256"], "embedded-wav-hash")
            self.assertEqual(rows[0]["matchedBankMediaReferenceCount"], 1)
            self.assertEqual(rows[0]["decodedBankMediaReferenceCount"], 1)

    def test_internal_prefetch_fragment_is_linked_without_claiming_wav_decode(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source_bank = self.parse(folder, 10, EVENT_ACTION, "event.xml")
            media_bank = self.parse(folder, 20, TARGET_AND_SOUND, "media.xml")
            for bank in (source_bank, media_bank):
                bank["sourceSha256"] = "source-hash"
                bank["xmlRelative"] = f"decoded/{bank['source']}"
            internal_index = _make_bank_media_index([{
                "bank_id": 20,
                "media_id": 12345,
                "source": "bin/sound/media.bnk",
                "source_sha256": "bank-hash",
                "container_index": 0,
                "index_record_hex": "393000000000000063000000",
                "data_offset": 0,
                "size_bytes": 99,
                "extract_status": "EXACT_BINARY_EXTRACTED",
                "output": "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.prefetch.bin",
                "output_sha256": "fragment-hash",
                "wav_status": "UNSUPPORTED",
                "wav_output": "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.wav",
                "wav_output_sha256": None,
            }])

            rows = map_bank_events([source_bank, media_bank], {}, internal_index)

            media = rows[0]["mediaReferences"][0]
            self.assertEqual(media["bankMediaMatchStatus"], "MATCHED_INTERNAL_MEDIA_FRAGMENT")
            self.assertEqual(media["bankMedia"]["output"].rsplit("/", 1)[-1], "12345.prefetch.bin")
            self.assertIsNone(media["bankMedia"]["wavOutput"])
            self.assertEqual(rows[0]["matchedBankMediaReferenceCount"], 1)
            self.assertEqual(rows[0]["decodedBankMediaReferenceCount"], 0)

    def test_same_media_id_in_different_bank_does_not_match_internal_index(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source_bank = self.parse(folder, 10, EVENT_ACTION, "event.xml")
            media_bank = self.parse(folder, 20, TARGET_AND_SOUND, "media.xml")
            for bank in (source_bank, media_bank):
                bank["sourceSha256"] = "source-hash"
                bank["xmlRelative"] = f"decoded/{bank['source']}"
            internal_index = _make_bank_media_index([{
                "bank_id": 30,
                "media_id": 12345,
                "source": "bin/sound/other.bnk",
                "source_sha256": "other-bank-hash",
                "container_index": 0,
                "index_record_hex": "393000000000000063000000",
                "data_offset": 0,
                "size_bytes": 99,
                "extract_status": "DECODED",
                "output": "decoded/1.0.2/romfs/bin/sound/other.bnk.contents/12345.wem",
                "output_sha256": "other-wem-hash",
                "wav_status": "DECODED",
                "wav_output": "decoded/1.0.2/romfs/bin/sound/other.bnk.contents/12345.wav",
                "wav_output_sha256": "other-wav-hash",
            }])

            rows = map_bank_events([source_bank, media_bank], {}, internal_index)

            media = rows[0]["mediaReferences"][0]
            self.assertEqual(media["bankMediaMatchStatus"], "NO_SAME_BANK_DIDX_MATCH")
            self.assertIsNone(media["bankMedia"])
            self.assertEqual(rows[0]["matchedBankMediaReferenceCount"], 0)

    def test_internal_receipt_requires_hash_match_to_verified_bnk_source(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source_bank = self.parse(folder, 10, EVENT_ACTION, "event.xml")
            media_bank = self.parse(folder, 20, TARGET_AND_SOUND, "media.xml")
            for bank in (source_bank, media_bank):
                bank["sourceSha256"] = "current-source-hash"
                bank["xmlRelative"] = f"decoded/{bank['source']}"
            internal_index = _make_bank_media_index([{
                "bank_id": 20,
                "media_id": 12345,
                "source": "bin/sound/media.bnk",
                "source_sha256": "stale-source-hash",
                "container_index": 0,
                "index_record_hex": "393000000000000063000000",
                "data_offset": 0,
                "size_bytes": 99,
                "extract_status": "DECODED",
                "output": "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.wem",
                "output_sha256": "embedded-wem-hash",
                "wav_status": "DECODED",
                "wav_output": "decoded/1.0.2/romfs/bin/sound/media.bnk.contents/12345.wav",
                "wav_output_sha256": "embedded-wav-hash",
            }], {"bin/sound/media.bnk": "current-source-hash"})

            rows = map_bank_events([source_bank, media_bank], {}, internal_index)

            media = rows[0]["mediaReferences"][0]
            self.assertEqual(media["bankMediaMatchStatus"], "BANK_MEDIA_SOURCE_HASH_NOT_VERIFIED")
            self.assertIsNone(media["bankMedia"])
            self.assertEqual(rows[0]["matchedBankMediaReferenceCount"], 0)

    def test_xml_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bank.xml"
            path.write_text(bank_xml(10, EVENT_ACTION), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "XML hash mismatch"):
                parse_wwiser_bank(path, "bank.bnk", "wrong-hash")

    def test_duplicate_global_target_id_remains_ambiguous_without_bank_context(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            event_without_bank = EVENT_ACTION.replace(
                '<object name="PlayActionParams"><field offset="220" type="tid" name="bankID" value="20" /></object>',
                "",
            )
            event_bank = self.parse(folder, 10, event_without_bank, "event.xml")
            target_one = self.parse(folder, 20, TARGET_AND_SOUND, "target-one.xml")
            target_two = self.parse(folder, 30, TARGET_AND_SOUND, "target-two.xml")
            banks = [event_bank, target_one, target_two]
            for bank in banks:
                bank["sourceSha256"] = "source-hash"
                bank["xmlRelative"] = f"decoded/{bank['source']}"

            rows = map_bank_events(banks, {})

            self.assertEqual(rows[0]["status"], "AMBIGUOUS_GLOBAL_HIRC_ID")
            self.assertEqual(rows[0]["targetObjectResolution"], "AMBIGUOUS_GLOBAL_HIRC_ID")
            self.assertEqual(rows[0]["mediaReferences"], [])


if __name__ == "__main__":
    unittest.main()
