"""Build an auditable static Wwise event-to-media map from wwiser XML."""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from .core import PROJECT, VERSION, sha256, source_dirs

WWISER_COMMIT = "08e937b649bc7007c234bbd59e34a41d5eef3b38"
SUCCESS = {"DECODED", "DECODED_EXISTING_VERIFIED"}
MAPPING_METHOD = "STATIC_WWISE_HIRC_REACHABILITY"


class _HashingReader:
    """Hash XML as ElementTree reads it, avoiding a second pass over large banks."""

    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        data = self.stream.read(size)
        self.digest.update(data)
        return data

    def hexdigest(self) -> str:
        return self.digest.hexdigest()


def _field(parent: ET.Element, name: str) -> ET.Element | None:
    return next(
        (item for item in parent if item.tag == "field" and item.get("name") == name),
        None,
    )


def _field_value(parent: ET.Element, name: str) -> str | None:
    item = _field(parent, name)
    return item.get("value") if item is not None else None


def _field_evidence(item: ET.Element | None) -> dict | None:
    if item is None:
        return None
    raw_offset = item.get("offset")
    return {
        "name": item.get("name"),
        "value": item.get("value"),
        "type": item.get("type"),
        "offset": int(raw_offset) if raw_offset and raw_offset.isdigit() else None,
    }


def _canonical_id(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(int(value, 16) if value.lower().startswith("0x") else int(value, 10))
    except ValueError:
        return value


def _fields_below(parent: ET.Element, name: str) -> list[ET.Element]:
    return [item for item in parent.iter("field") if item.get("name") == name]


def _section(obj: ET.Element, name: str) -> ET.Element | None:
    return next(
        (item for item in obj.iter("object") if item is not obj and item.get("name") == name),
        None,
    )


def _reference(field: ET.Element, edge_type: str, bank_id: str | None = None) -> dict:
    return {
        "edgeType": edge_type,
        "targetId": _canonical_id(field.get("value")),
        "field": _field_evidence(field),
        "targetBankId": bank_id,
    }


def _parse_hirc_object(obj: ET.Element) -> dict | None:
    name = obj.get("name") or ""
    if not name.startswith("CAk"):
        return None
    id_field = _field(obj, "ulID")
    object_id = _canonical_id(id_field.get("value") if id_field is not None else None)
    if object_id is None:
        return None

    refs: list[dict] = []
    event_values = _section(obj, "EventInitialValues")
    if event_values is not None:
        refs.extend(_reference(item, "EVENT_ACTION") for item in _fields_below(event_values, "ulActionID"))

    action_values = _section(obj, "ActionInitialValues")
    action_target = None
    action_bank = None
    action_type = _field(obj, "ulActionType")
    if action_values is not None:
        target_field = _field(action_values, "idExt")
        if target_field is None:
            target_field = _field(action_values, "ulTargetID")
        if target_field is not None:
            action_target = _field_evidence(target_field)
            refs.append(_reference(target_field, "ACTION_TARGET"))
        play_params = _section(action_values, "PlayActionParams")
        if play_params is not None:
            action_bank_field = _field(play_params, "bankID")
            if action_bank_field is None:
                action_bank_field = _field(play_params, "fileID")
            if action_bank_field is not None:
                action_bank = _canonical_id(action_bank_field.get("value"))
                for reference in reversed(refs):
                    if reference["edgeType"] == "ACTION_TARGET":
                        reference["targetBankId"] = action_bank
                        break

    for children in (item for item in obj.iter("object") if item.get("name") == "Children"):
        refs.extend(
            _reference(item, "CHILD_ID")
            for item in children.iter("field")
            if item.get("name") == "ulChildID" or item.get("type") == "tid"
        )
    for switch_list in (item for item in obj.iter("object") if item.get("name") == "SwitchList"):
        for node_list in (item for item in switch_list.iter("object") if item.get("name") == "NodeList"):
            refs.extend(
                _reference(field_item, "SWITCH_NODE")
                for field_item in node_list.iter("field")
                if field_item.get("type") == "tid"
            )
    for playlist in (item for item in obj.iter("object") if item.get("name") == "pPlayList"):
        refs.extend(
            _reference(item, "MUSIC_PLAYLIST_SEGMENT")
            for item in playlist.iter("field")
            if item.get("name") == "SegmentID"
        )
    for associations in (item for item in obj.iter("object") if item.get("name") == "pAssocs"):
        refs.extend(
            _reference(item, "RANSEQ_ASSOC_NODE")
            for item in associations.iter("field")
            if item.get("name") == "nodeID"
        )
    for track_source in (item for item in obj.iter("object") if item.get("name") == "AkTrackSrcInfo"):
        event_field = _field(track_source, "eventID")
        if event_field is not None and _canonical_id(event_field.get("value")) not in (None, "0"):
            refs.append(_reference(event_field, "MUSIC_TRACK_EVENT"))

    media = []
    for source_data in (item for item in obj.iter("object") if item.get("name") == "AkBankSourceData"):
        for info in (item for item in source_data.iter("object") if item.get("name") == "AkMediaInformation"):
            source_field = _field(info, "sourceID")
            if source_field is None:
                continue
            media.append({
                "sourceId": _canonical_id(source_field.get("value")),
                "sourceIdField": _field_evidence(source_field),
                "streamType": _field_value(source_data, "StreamType"),
                "hasSourceFlag": next(
                    (item.get("value") for item in info.iter("field") if item.get("name") == "bHasSource"),
                    None,
                ),
            })

    return {
        "objectId": object_id,
        "objectIdField": _field_evidence(id_field),
        "objectIndex": obj.get("index"),
        "className": name,
        "actionType": _field_evidence(action_type),
        "actionTarget": action_target,
        "actionBankId": action_bank,
        "references": refs,
        "media": media,
    }


def parse_wwiser_bank(xml_path: Path, source: str, expected_xml_sha256: str | None = None) -> dict:
    """Parse one wwiser bank listing, retaining only source-backed graph fields."""
    with xml_path.open("rb") as stream:
        reader = _HashingReader(stream)
        root = ET.parse(reader).getroot()
        xml_sha256 = reader.hexdigest()
    if expected_xml_sha256 and xml_sha256 != expected_xml_sha256:
        raise ValueError(f"wwiser XML hash mismatch: {xml_path}")
    header = next(
        (item for item in root.iter("object") if item.get("name") == "AkBankHeader"),
        None,
    )
    bank_id = _canonical_id(_field_value(header, "dwSoundBankID")) if header is not None else None
    hirc = next((item for item in root.iter("object") if item.get("name") == "HircChunk"), None)
    loaded = next(
        (item for item in hirc.iter("list") if item.get("name") == "listLoadedItem"),
        None,
    ) if hirc is not None else None
    hirc_objects = list(loaded.findall("./object")) if loaded is not None else []
    if not hirc_objects and hirc is not None:
        hirc_objects = [
            item for item in hirc.iter("object")
            if item.get("name", "").startswith("CAk") and _field(item, "ulID") is not None
        ]
    parsed_objects = [item for item in (_parse_hirc_object(obj) for obj in hirc_objects) if item]
    by_id: dict[str, list[dict]] = {}
    for item in parsed_objects:
        by_id.setdefault(item["objectId"], []).append(item)
    events = [item for item in parsed_objects if item["className"] in {"CAkEvent", "CAkDialogueEvent"}]
    return {
        "source": source,
        "xml": xml_path,
        "xmlSha256": xml_sha256,
        "bankId": bank_id,
        "bankVersion": root.get("version"),
        "objects": parsed_objects,
        "objectsById": by_id,
        "events": events,
    }


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _manifest_path(value: str) -> str:
    relative = PurePosixPath(value.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "decoded":
        raise ValueError(f"unsafe project manifest path: {value}")
    return relative.as_posix()


def _make_wem_index(audio_rows: list[dict]) -> tuple[dict[str, list[dict]], int]:
    result: dict[str, list[dict]] = {}
    count = 0
    for row in audio_rows:
        source_rel = str(row.get("source", "")).replace("\\", "/")
        if not source_rel.lower().endswith(".wem"):
            continue
        count += 1
        relative = PurePosixPath(source_rel)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        output_rel = row.get("output")
        output = _manifest_path(output_rel) if output_rel else None
        result.setdefault(Path(source_rel).stem, []).append({
            "source": source_rel,
            "sourceSha256": row.get("source_sha256"),
            "sourceBytes": row.get("source_bytes"),
            "audioReceiptStatus": row.get("status"),
            "wav": output,
            "wavSha256": row.get("output_sha256"),
        })
    return result, count


def _make_bank_media_index(
    media_rows: list[dict], verified_bank_sources: dict[str, str] | None = None,
) -> dict[tuple[str, str], list[dict]]:
    """Index DIDX receipts by exact BankHeader ID and media ID.

    When source hashes are supplied, a child receipt is usable only if its BNK
    source matches the bank that was just independently hash-checked by the
    event mapper.
    """
    result: dict[tuple[str, str], list[dict]] = {}
    for row in media_rows:
        bank_id = row.get("bank_id")
        media_id = row.get("media_id")
        if bank_id is None or media_id is None:
            continue
        source = str(row.get("source", "")).replace("\\", "/")
        expected_hash = None
        verified = True
        if verified_bank_sources is not None:
            expected_hash = verified_bank_sources.get(source)
            verified = bool(expected_hash and row.get("source_sha256") == expected_hash)
        output = row.get("output")
        output = _manifest_path(output) if output else None
        wav_output = row.get("wav_output")
        wav_output = (
            _manifest_path(wav_output)
            if wav_output and row.get("wav_output_sha256")
            and row.get("wav_status") in SUCCESS
            else None
        )
        evidence = {
            "bankSource": source,
            "bankSourceSha256": row.get("source_sha256"),
            "containerIndex": row.get("container_index"),
            "indexRecordHex": row.get("index_record_hex"),
            "dataOffset": row.get("data_offset"),
            "sizeBytes": row.get("size_bytes"),
            "extractStatus": row.get("extract_status"),
            "output": output if verified else None,
            "outputSha256": row.get("output_sha256") if verified else None,
            "outputBytes": row.get("output_bytes") if verified else None,
            "wavStatus": row.get("wav_status"),
            "wavOutput": wav_output if verified else None,
            "wavOutputSha256": row.get("wav_output_sha256") if verified else None,
            "wavOutputBytes": row.get("wav_output_bytes") if verified else None,
            "sourceHashVerified": verified,
        }
        result.setdefault((str(bank_id), str(media_id)), []).append(evidence)
    return result


LOCAL_REFERENCE_TYPES = {
    "EVENT_ACTION", "CHILD_ID", "SWITCH_NODE", "MUSIC_PLAYLIST_SEGMENT", "RANSEQ_ASSOC_NODE",
}


def _global_object_index(banks: list[dict]) -> dict[str, list[tuple[dict, dict]]]:
    index: dict[str, list[tuple[dict, dict]]] = {}
    for bank in banks:
        for object_id, objects in bank["objectsById"].items():
            index.setdefault(object_id, []).extend((bank, item) for item in objects)
    return index


def _resolve_reference(reference: dict, bank: dict,
                       banks_by_id: dict[str, list[dict]],
                       global_objects: dict[str, list[tuple[dict, dict]]]):
    object_id = reference.get("targetId")
    if reference["edgeType"] in LOCAL_REFERENCE_TYPES:
        candidates = [(bank, item) for item in bank["objectsById"].get(object_id, [])]
        return candidates, "LOCAL_HIRC_ID" if len(candidates) == 1 else (
            "AMBIGUOUS_LOCAL_HIRC_ID" if candidates else "LOCAL_HIRC_ID_NOT_FOUND"
        ), [bank["source"]] if candidates else []

    declared_bank_id = reference.get("targetBankId")
    if reference["edgeType"] == "ACTION_TARGET" and declared_bank_id not in (None, "0"):
        declared_banks = banks_by_id.get(declared_bank_id, [])
        if len(declared_banks) == 1:
            declared_bank = declared_banks[0]
            candidates = [(declared_bank, item) for item in declared_bank["objectsById"].get(object_id, [])]
            if len(candidates) == 1:
                return candidates, "DECLARED_BANK_ID_AND_HIRC_ID", [declared_bank["source"]]
            if len(candidates) > 1:
                return candidates, "AMBIGUOUS_HIRC_ID_IN_DECLARED_BANK", [declared_bank["source"]]
            global_candidates = global_objects.get(object_id, [])
            return [], "TARGET_ID_NOT_IN_DECLARED_BANK", sorted({item[0]["source"] for item in global_candidates})
        if len(declared_banks) > 1:
            return [], "AMBIGUOUS_DECLARED_BANK_ID", sorted(item["source"] for item in declared_banks)
        return [], "DECLARED_BANK_ID_NOT_IN_BATCH", sorted(
            {item[0]["source"] for item in global_objects.get(object_id, [])}
        )

    candidates = global_objects.get(object_id, [])
    if len(candidates) == 1:
        return candidates, "UNIQUE_GLOBAL_HIRC_ID", [candidates[0][0]["source"]]
    if len(candidates) > 1:
        return candidates, "AMBIGUOUS_GLOBAL_HIRC_ID", sorted({item[0]["source"] for item in candidates})
    return [], "GLOBAL_HIRC_ID_NOT_FOUND", []


def _reachable_media(start_bank: dict, start_object: dict,
                     banks_by_id: dict[str, list[dict]],
                     global_objects: dict[str, list[tuple[dict, dict]]],
                     wem_index: dict[str, list[dict]],
                     bank_media_index: dict[tuple[str, str], list[dict]] | None = None) -> dict:
    bank_media_index = bank_media_index or {}
    stack = [(start_bank, start_object)]
    visited: set[tuple[str | None, str]] = set()
    objects: list[dict] = []
    media: dict[tuple, dict] = {}
    unresolved: list[dict] = []
    while stack:
        bank, obj = stack.pop()
        key = (bank.get("bankId"), obj["objectId"])
        if key in visited:
            continue
        visited.add(key)
        objects.append({"bankId": key[0], "objectId": key[1], "className": obj["className"]})
        for reference in obj["references"]:
            ref_id = reference.get("targetId")
            if ref_id in (None, "0"):
                continue
            candidates, resolution, candidate_banks = _resolve_reference(
                reference, bank, banks_by_id, global_objects,
            )
            if len(candidates) == 1:
                stack.append(candidates[0])
            else:
                unresolved.append({
                    **reference,
                    "resolution": resolution,
                    "candidateBanks": candidate_banks,
                })
        for media_ref in obj["media"]:
            source_id = media_ref["sourceId"]
            matches = wem_index.get(source_id or "", [])
            if len(matches) == 1:
                wem = matches[0]
                match_status = "MATCHED_DECIMAL_WEM_MANIFEST_NAME"
            elif len(matches) > 1:
                wem = None
                match_status = "AMBIGUOUS_WEM_FILENAME"
            else:
                wem = None
                match_status = "NO_LOCAL_WEM_FILENAME_MATCH"
            internal = bank_media_index.get((str(bank.get("bankId")), source_id or ""), [])
            verified_internal = [item for item in internal if item["sourceHashVerified"]]
            if len(verified_internal) == 1:
                bank_media = verified_internal[0]
                if (
                    bank_media["extractStatus"] in SUCCESS
                    and bank_media["wavOutput"]
                    and bank_media["wavOutputSha256"]
                ):
                    bank_media_status = "MATCHED_INTERNAL_MEDIA_AND_WAV"
                elif bank_media["extractStatus"] == "EXACT_BINARY_EXTRACTED":
                    bank_media_status = "MATCHED_INTERNAL_MEDIA_FRAGMENT"
                elif bank_media["extractStatus"] in SUCCESS:
                    bank_media_status = "MATCHED_INTERNAL_MEDIA_NO_WAV"
                else:
                    bank_media_status = "MATCHED_INTERNAL_MEDIA_UNSUPPORTED"
            elif len(verified_internal) > 1:
                bank_media = None
                bank_media_status = "AMBIGUOUS_SAME_BANK_DIDX_MATCH"
            elif internal:
                bank_media = None
                bank_media_status = "BANK_MEDIA_SOURCE_HASH_NOT_VERIFIED"
            else:
                bank_media = None
                bank_media_status = "NO_SAME_BANK_DIDX_MATCH"
            identity = (
                bank.get("bankId"), obj["objectId"], source_id,
                (media_ref.get("sourceIdField") or {}).get("offset"),
            )
            media[identity] = {
                **media_ref,
                "sourceObjectId": obj["objectId"],
                "sourceObjectClass": obj["className"],
                "wemMatchStatus": match_status,
                "wem": wem,
                "sourceBankId": bank.get("bankId"),
                "bankMediaMatchStatus": bank_media_status,
                "bankMedia": bank_media,
            }
    return {
        "objects": sorted(objects, key=lambda item: (item["bankId"] or "", item["objectId"])),
        "media": list(media.values()),
        "unresolved": unresolved,
    }


def map_bank_events(
    banks: list[dict], wem_index: dict[str, list[dict]],
    bank_media_index: dict[tuple[str, str], list[dict]] | None = None,
) -> list[dict]:
    bank_media_index = bank_media_index or {}
    global_objects = _global_object_index(banks)
    banks_by_id: dict[str, list[dict]] = {}
    for bank in banks:
        banks_by_id.setdefault(bank["bankId"], []).append(bank)
    rows = []
    for bank in banks:
        for event in bank["events"]:
            action_refs = [ref for ref in event["references"] if ref["edgeType"] == "EVENT_ACTION"]
            if not action_refs:
                error = "DIALOGUE_EVENT_TREE_UNPARSED" if event["className"] == "CAkDialogueEvent" else "EVENT_HAS_NO_ACTIONS"
                rows.append(_event_row(bank, event, None, None, None, None, [], error=error))
                continue
            for action_ordinal, action_ref in enumerate(action_refs):
                action_matches = bank["objectsById"].get(action_ref["targetId"], [])
                if len(action_matches) != 1:
                    rows.append(_event_row(bank, event, action_ref, None, None, None, [], action_ordinal,
                                           error="ACTION_OBJECT_NOT_FOUND" if not action_matches else "AMBIGUOUS_ACTION_ID"))
                    continue
                action = action_matches[0]
                target_ref = next((ref for ref in action["references"] if ref["edgeType"] == "ACTION_TARGET"), None)
                if target_ref is None:
                    rows.append(_event_row(bank, event, action_ref, action, None, None, [], action_ordinal,
                                           error="ACTION_HAS_NO_TARGET"))
                    continue
                target_id = target_ref.get("targetId")
                if target_id in (None, "0"):
                    rows.append(_event_row(bank, event, action_ref, action, target_ref, None, [], action_ordinal,
                                           error="ZERO_OR_MISSING_ACTION_TARGET"))
                    continue
                candidates, resolution, candidate_banks = _resolve_reference(
                    target_ref, bank, banks_by_id, global_objects,
                )
                if len(candidates) != 1:
                    unresolved = [{**target_ref, "resolution": resolution, "candidateBanks": candidate_banks}]
                    rows.append(_event_row(bank, event, action_ref, action, target_ref, None,
                                           {"objects": [], "media": [], "unresolved": unresolved}, action_ordinal,
                                           error=resolution, bank_resolution=resolution))
                    continue
                target_bank, target = candidates[0]
                reached = _reachable_media(
                    target_bank, target, banks_by_id, global_objects, wem_index,
                    bank_media_index,
                )
                rows.append(_event_row(bank, event, action_ref, action, target_ref, target, reached,
                                       action_ordinal, bank_resolution=resolution))
    return rows


def _event_row(bank: dict, event: dict, action_ref: dict | None, action: dict | None,
               target_ref: dict | None, target: dict | None, reached: dict | list,
               action_ordinal: int | None = None, error: str | None = None,
               bank_resolution: str | None = None) -> dict:
    if isinstance(reached, list):
        reached = {"objects": [], "media": [], "unresolved": []}
    media = reached["media"]
    matched = sum(item["wemMatchStatus"] == "MATCHED_DECIMAL_WEM_MANIFEST_NAME" for item in media)
    receipt_backed = sum(
        item["wemMatchStatus"] == "MATCHED_DECIMAL_WEM_MANIFEST_NAME"
        and item["wem"]["audioReceiptStatus"] in SUCCESS
        and bool(item["wem"]["wavSha256"])
        for item in media
    )
    matched_bank_media = sum(item["bankMedia"] is not None for item in media)
    decoded_bank_media = sum(
        item["bankMediaMatchStatus"] == "MATCHED_INTERNAL_MEDIA_AND_WAV"
        for item in media
    )
    status = error or (
        "STATIC_REACHABILITY_WITH_WEM_MANIFEST_ENTRY" if matched else
        "STATIC_REACHABILITY_WITH_MEDIA_ID" if media else
        "STATIC_GRAPH_INCOMPLETE_NO_MEDIA" if reached["unresolved"] else
        "NO_MEDIA_SOURCE_REACHABLE"
    )
    return {
        "schema": "lgpe-wwise-event-media-v2",
        "method": MAPPING_METHOD,
        "linkSemantics": "static HIRC graph reachability; does not establish runtime selection, probability, or audible playback",
        "bankMediaLinkSemantics": "exact BankHeader ID plus sourceID to DIDX bank ID plus media ID; source BNK SHA-256 must match the independently verified bank receipt",
        "wwiserCommit": WWISER_COMMIT,
        "bankSource": bank["source"],
        "bankSourceSha256": bank["sourceSha256"],
        "bankXml": bank["xmlRelative"],
        "bankXmlSha256": bank["xmlSha256"],
        "bankId": bank["bankId"],
        "bankVersion": bank["bankVersion"],
        "eventId": event["objectId"],
        "eventIdHex": f"0x{int(event['objectId']):08x}" if event["objectId"].isdigit() else None,
        "eventIndex": event["objectIndex"],
        "eventName": None,
        "eventNameStatus": "UNKNOWN_WWNAMES_DB_ABSENT",
        "eventActionOrdinal": action_ordinal,
        "eventActionOffset": action_ref.get("field", {}).get("offset") if action_ref else None,
        "eventActionRef": action_ref,
        "actionId": action["objectId"] if action else (action_ref or {}).get("targetId"),
        "actionClass": action["className"] if action else None,
        "actionType": action["actionType"] if action else None,
        "actionTargetRef": target_ref,
        "actionBankId": action["actionBankId"] if action else None,
        "targetObjectId": target["objectId"] if target else None,
        "targetObjectClass": target["className"] if target else None,
        "targetObjectResolution": bank_resolution,
        "status": status,
        "graphComplete": not reached["unresolved"] and error is None,
        "reachableObjectCount": len(reached["objects"]),
        "reachableObjects": reached["objects"],
        "mediaReferenceCount": len(media),
        "matchedWemReferenceCount": matched,
        "receiptBackedWavReferenceCount": receipt_backed,
        "matchedBankMediaReferenceCount": matched_bank_media,
        "decodedBankMediaReferenceCount": decoded_bank_media,
        "mediaReferences": media,
        "unresolvedReferences": reached["unresolved"],
    }


def map_unreferenced_wem_hirc_objects(
    banks: list[dict], wem_index: dict[str, list[dict]], event_rows: list[dict],
    bank_failures: int = 0,
) -> list[dict]:
    """Find loose WEMs absent from event-reachable media and search all parsed HIRC objects.

    A matching object is evidence of a static HIRC sourceID occurrence only;
    this does not show that the object can be reached or used at runtime.
    """
    event_reachable_sources = {
        str(media["wem"].get("source", "")).replace("\\", "/")
        for row in event_rows for media in row.get("mediaReferences", [])
        if media.get("wemMatchStatus") == "MATCHED_DECIMAL_WEM_MANIFEST_NAME" and media.get("wem")
    }
    hirc_media: dict[str, list[dict]] = {}
    for bank in banks:
        for obj in bank.get("objects", []):
            for media in obj.get("media", []):
                source_id = media.get("sourceId")
                if source_id in (None, ""):
                    continue
                hirc_media.setdefault(str(source_id), []).append({
                    "bankSource": bank["source"],
                    "bankSourceSha256": bank.get("sourceSha256"),
                    "bankXml": bank.get("xmlRelative"),
                    "bankXmlSha256": bank.get("xmlSha256"),
                    "bankId": bank.get("bankId"),
                    "bankVersion": bank.get("bankVersion"),
                    "hircObjectId": obj.get("objectId"),
                    "hircObjectIndex": obj.get("objectIndex"),
                    "hircObjectClass": obj.get("className"),
                    "sourceId": str(source_id),
                    "sourceIdField": media.get("sourceIdField"),
                    "streamType": media.get("streamType"),
                    "hasSourceFlag": media.get("hasSourceFlag"),
                })

    result = []
    for source_id, assets in sorted(wem_index.items()):
        for asset in assets:
            source = str(asset.get("source", "")).replace("\\", "/")
            if source in event_reachable_sources:
                continue
            matches = sorted(
                hirc_media.get(str(source_id), []),
                key=lambda item: (item["bankSource"], str(item["hircObjectIndex"]), str(item["hircObjectId"])),
            )
            result.append({
                "schema": "lgpe-wwise-unreferenced-wem-hirc-v1",
                "method": "STATIC_HIRC_SOURCEID_SEARCH_OUTSIDE_EVENT_REACHABILITY",
                "semantics": "No event-graph media path was found in this parsed BNK set; an HIRC sourceID match is static object evidence, not runtime reachability or playback.",
                "sourceVersion": "Let's Go Pikachu 1.0.2",
                "wwiserCommit": WWISER_COMMIT,
                "sourceId": str(source_id),
                "wemSource": source,
                "wemSourceSha256": asset.get("sourceSha256"),
                "wemSourceBytes": asset.get("sourceBytes"),
                "audioReceiptStatus": asset.get("audioReceiptStatus"),
                "wav": asset.get("wav"),
                "wavSha256": asset.get("wavSha256"),
                "eventGraphReachability": "NO_MATCH_IN_CURRENT_EVENT_MAP",
                "hircSearchBankCount": len(banks),
                "hircSearchBankFailures": bank_failures,
                "hircMatches": matches,
                "hircMatchCount": len(matches),
                "status": "STATIC_HIRC_OBJECT_NOT_REACHED_FROM_MAPPED_EVENTS" if matches else "NO_LOCAL_HIRC_SOURCEID_MATCH",
            })
    return result


def _verify_unreferenced_wem_receipts(root: Path, project: Path, rows: list[dict]) -> None:
    romfs = source_dirs(root)["romfs"]
    for row in rows:
        relative = PurePosixPath(row["wemSource"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe loose WEM path in audio manifest: {row['wemSource']}")
        source = romfs.joinpath(*relative.parts)
        if not source.is_file() or sha256(source) != row["wemSourceSha256"]:
            raise ValueError(f"unreferenced WEM source hash mismatch: {row['wemSource']}")
        if row["audioReceiptStatus"] not in SUCCESS:
            continue
        wav_relative = _manifest_path(row.get("wav") or "")
        wav = project.joinpath(*PurePosixPath(wav_relative).parts)
        if not wav.is_file() or not row.get("wavSha256") or sha256(wav) != row["wavSha256"]:
            raise ValueError(f"unreferenced WEM WAV receipt mismatch: {row['wemSource']}")


def build_wwise_event_media_map(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    """Validate existing BNK/WEM receipts and write static event/media JSONL rows."""
    dirs = source_dirs(root)
    romfs = dirs["romfs"].resolve()
    decoded = project / "decoded" / VERSION / "romfs"
    bnk_rows = _jsonl(project / "manifests" / "bnk.jsonl")
    audio_rows = _jsonl(project / "manifests" / "audio.jsonl")
    bank_media_rows = _jsonl(project / "manifests" / "bnk_media.jsonl")
    bnk_by_source = {str(row.get("source", "")).replace("\\", "/"): row for row in bnk_rows}
    wem_index, wem_manifest_count = _make_wem_index(audio_rows)

    banks = []
    failures = []
    for source_rel, row in sorted(bnk_by_source.items()):
        if row.get("status") not in SUCCESS:
            continue
        relative = PurePosixPath(source_rel)
        if relative.is_absolute() or ".." in relative.parts:
            failures.append({"source": source_rel, "error": "unsafe source path"})
            continue
        source = romfs.joinpath(*relative.parts)
        xml_path = decoded.joinpath(*relative.with_suffix(".xml").parts)
        try:
            source_sha256 = sha256(source)
            if row.get("source_sha256") and source_sha256 != row["source_sha256"]:
                raise ValueError("BNK source hash differs from decoded manifest")
            parsed = parse_wwiser_bank(xml_path, source_rel, row.get("output_sha256"))
            if not parsed["bankId"]:
                raise ValueError("wwiser output has no BankHeader sound-bank ID")
            banks.append({
                **parsed,
                "sourceSha256": source_sha256,
                "xmlRelative": xml_path.relative_to(project).as_posix(),
            })
        except Exception as exc:
            failures.append({"source": source_rel, "error": f"{type(exc).__name__}: {exc}"})

    verified_bank_sources = {bank["source"]: bank["sourceSha256"] for bank in banks}
    bank_media_index = _make_bank_media_index(bank_media_rows, verified_bank_sources)
    rows = map_bank_events(banks, wem_index, bank_media_index)
    unreferenced_wems = map_unreferenced_wem_hirc_objects(
        banks, wem_index, rows, bank_failures=len(failures),
    )
    _verify_unreferenced_wem_receipts(root, project, unreferenced_wems)
    output = project / "manifests" / "wwise_event_media.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(output)
    unreferenced_output = project / "manifests" / "wwise_unreferenced_wem.jsonl"
    unreferenced_temporary = unreferenced_output.with_name(unreferenced_output.name + ".partial")
    unreferenced_temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in unreferenced_wems),
        encoding="utf-8",
    )
    unreferenced_temporary.replace(unreferenced_output)

    events_with_media = len({
        (row["bankSource"], row["eventId"])
        for row in rows if row["mediaReferenceCount"]
    })
    event_wem_pairs = {
        (row["bankSource"], row["eventId"], item["wem"]["source"])
        for row in rows for item in row["mediaReferences"]
        if item["wem"] is not None
    }
    internal_media_references = [
        (row, item)
        for row in rows for item in row["mediaReferences"]
        if item["bankMedia"] is not None
    ]
    unique_internal_media = {
        (
            item["bankMedia"]["bankSource"],
            item["bankMedia"]["containerIndex"],
            item["sourceId"],
        )
        for _, item in internal_media_references
    }
    events_with_internal_media = {
        (row["bankSource"], row["eventId"])
        for row, _ in internal_media_references
    }
    bank_media_source_hash_unverified = sum(
        not item["sourceHashVerified"]
        for values in bank_media_index.values() for item in values
    )
    return {
        "status": "ANALYZED" if not failures else "ANALYZED_WITH_FAILURES",
        "banksParsed": len(banks),
        "banksFailed": len(failures),
        "events": len({(row["bankSource"], row["eventId"]) for row in rows}),
        "eventActionRows": len(rows),
        "eventsWithReachableMedia": events_with_media,
        "eventWemPairs": len(event_wem_pairs),
        "bankMediaManifestRows": len(bank_media_rows),
        "bankMediaSourceHashUnverifiedRows": bank_media_source_hash_unverified,
        "eventMediaReferencesMatchedToBankDIDX": len(internal_media_references),
        "uniqueBankDIDXMembersReferencedByEvents": len(unique_internal_media),
        "eventsWithReachableBankDIDXMedia": len(events_with_internal_media),
        "bankDIDXReferencesWithVerifiedWav": sum(
            row["decodedBankMediaReferenceCount"] for row in rows
        ),
        "wemManifestFiles": wem_manifest_count,
        "looseWemsWithoutEventGraphReachability": len(unreferenced_wems),
        "unreferencedWemHircObjectMatches": sum(row["hircMatchCount"] for row in unreferenced_wems),
        "unreferencedWemStatuses": dict(sorted(Counter(row["status"] for row in unreferenced_wems).items())),
        "unreferencedWemManifest": str(unreferenced_output),
        "unreferencedWemManifestBytes": unreferenced_output.stat().st_size,
        "unreferencedWemManifestSha256": sha256(unreferenced_output),
        "uniqueBankIds": len({bank["bankId"] for bank in banks}),
        "bankVersions": dict(sorted({str(bank["bankVersion"]): sum(item["bankVersion"] == bank["bankVersion"] for item in banks) for bank in banks}.items())),
        "failedBanks": failures,
        "manifest": str(output),
        "wwiserCommit": WWISER_COMMIT,
        "wwnamesDatabase": "ABSENT; event names retained as unknown hash IDs",
    }
