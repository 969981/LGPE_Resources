"""Cross-reference parsed LGPE sequence literals with verified Wwise events.

This is a static name/ShortID join only. The pinned BSEQ command dictionary's
gameplay semantics are not verified, so the output does not assert that a bank
was loaded, an event was invoked, or that audio played at runtime.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath

from .core import PROJECT, VERSION, sha256, source_dirs
from .wwise_map import SUCCESS as BANK_SUCCESS
from .wwise_orphan_audit import write_unreferenced_wem_id_audit

WWISER_COMMIT = "08e937b649bc7007c234bbd59e34a41d5eef3b38"
BSEQ_SUCCESS = {"DECODED", "DECODED_EXISTING_VERIFIED"}
SCHEMA = "lgpe-research.bseq-wwise-events.v1"
MAPPING_METHOD = "STATIC_BSEQ_LITERAL_TO_WWISE_FNV1_32_SHORTID"
SEMANTICS = (
    "Static parser-field and Wwise event-ID cross-reference only; does not establish "
    "sequence command semantics, bank loading, event invocation, runtime selection, "
    "probability, or audible playback."
)
LABEL_CANDIDATE_SCHEMA = "lgpe-research.wwise-sequence-event-label-candidates.v1"
LABEL_CANDIDATE_SEMANTICS = (
    "A decoded BSEQ parser field named event has the same pinned FNV-1 32-bit value as a local Wwise event ID. "
    "This is a sequence-literal label candidate only; it does not establish command meaning, bank loading, event "
    "invocation, runtime selection, or playback, and does not assign the Wwise eventName field."
)
PBSEQTOOL_COMMIT = "6f122d1b7945797cae472960b798bf28523f8acd"


def fnv1_32(value: str) -> int:
    """Return Wwise's lowercase UTF-8 FNV-1 32-bit ShortID candidate."""
    result = 2166136261
    for byte in value.lower().encode("utf-8"):
        result = (result * 16777619) & 0xFFFFFFFF
        result ^= byte
    return result


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _safe_source(value: str) -> PurePosixPath:
    relative = PurePosixPath(value.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"unsafe source manifest path: {value}")
    return relative


def _safe_decoded(project: Path, value: str) -> Path:
    relative = PurePosixPath(value.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "decoded":
        raise ValueError(f"unsafe decoded manifest path: {value}")
    return project.joinpath(*relative.parts)


def _load_bank_references(sequence: dict) -> list[dict]:
    references = []
    for group_index, group in enumerate(sequence.get("Data", [])):
        for command_index, command in enumerate(group.get("Commands", [])):
            if command.get("Name") != "BelugaSoundLoadBank":
                continue
            parameters = command.get("Parameters") or {}
            literal = parameters.get("name")
            if isinstance(literal, str):
                references.append({
                    "groupIndex": group_index,
                    "commandIndex": command_index,
                    "literal": literal,
                })
    return references


def _play_commands(sequence: dict) -> list[dict]:
    events = []
    for group_index, group in enumerate(sequence.get("Data", [])):
        for command_index, command in enumerate(group.get("Commands", [])):
            if command.get("Name") != "BelugaSoundPlaySe":
                continue
            parameters = command.get("Parameters") or {}
            literal = parameters.get("event")
            if not isinstance(literal, str):
                continue
            events.append({
                "groupIndex": group_index,
                "commandIndex": command_index,
                "startFrame": command.get("StartFrame"),
                "endFrame": command.get("EndFrame"),
                "eventLiteral": literal,
                "parserParameters": parameters,
                "eventIdFNV1_32": fnv1_32(literal),
            })
    return events


def _candidate_status(candidates: list[dict], referenced_sources: set[str]) -> tuple[str, list[dict]]:
    referenced = [item for item in candidates if item["bankSource"] in referenced_sources]
    if len(referenced) == 1:
        return "STATIC_ID_MATCH_IN_SEQUENCE_REFERENCED_BANK", referenced
    if len(referenced) > 1:
        return "AMBIGUOUS_STATIC_ID_MATCH_IN_SEQUENCE_BANKS", referenced
    if candidates:
        return "STATIC_ID_MATCH_ONLY_OUTSIDE_SEQUENCE_BANKS", []
    return "NO_STATIC_ID_MATCH", []


def _bank_manifest_index(root: Path, project: Path) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    romfs = source_dirs(root)["romfs"]
    rows = _jsonl(project / "manifests" / "bnk.jsonl")
    by_source: dict[str, dict] = {}
    by_stem: dict[str, list[dict]] = {}
    for row in rows:
        source_rel = _safe_source(str(row.get("source", ""))).as_posix()
        if row.get("status") not in BANK_SUCCESS:
            continue
        if source_rel in by_source:
            raise ValueError(f"duplicate BNK manifest source: {source_rel}")
        source = romfs.joinpath(*PurePosixPath(source_rel).parts)
        output = _safe_decoded(project, str(row.get("output", "")))
        if not source.is_file() or not output.is_file():
            raise FileNotFoundError(f"missing verified BNK or XML output: {source_rel}")
        source_hash = sha256(source)
        output_hash = sha256(output)
        if row.get("source_sha256") != source_hash:
            raise ValueError(f"BNK source hash mismatch: {source_rel}")
        if row.get("output_sha256") != output_hash:
            raise ValueError(f"BNK XML hash mismatch: {source_rel}")
        expected_relative = PurePosixPath("decoded") / VERSION / "romfs" / PurePosixPath(source_rel).with_suffix(".xml")
        if PurePosixPath(output.relative_to(project).as_posix()) != expected_relative:
            raise ValueError(f"BNK XML path is not mirrored: {source_rel}")
        item = {
            "bankSource": source_rel,
            "bankSourceSha256": source_hash,
            "bankXml": output.relative_to(project).as_posix(),
            "bankXmlSha256": output_hash,
            "bankStem": PurePosixPath(source_rel).stem,
        }
        by_source[source_rel] = item
        by_stem.setdefault(item["bankStem"], []).append(item)
    return by_source, by_stem


def _event_index(rows: list[dict], banks: dict[str, dict]) -> dict[str, list[dict]]:
    """Collapse event-action rows to unique source-bank/event-index records."""
    events: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        source = _safe_source(str(row.get("bankSource", ""))).as_posix()
        bank = banks.get(source)
        if bank is None:
            raise ValueError(f"Wwise event map references an unverified BNK: {source}")
        if row.get("bankSourceSha256") != bank["bankSourceSha256"]:
            raise ValueError(f"stale Wwise event map source hash: {source}")
        if row.get("bankXmlSha256") != bank["bankXmlSha256"]:
            raise ValueError(f"stale Wwise event map XML hash: {source}")
        event_id = str(row.get("eventId", ""))
        event_index = str(row.get("eventIndex", ""))
        if not event_id.isdecimal() or not event_index:
            continue
        key = (source, event_id, event_index)
        record = events.get(key)
        if record is None:
            record = {
                **bank,
                "bankId": row.get("bankId"),
                "eventId": event_id,
                "eventIdHex": row.get("eventIdHex"),
                "eventIndex": event_index,
                "eventName": row.get("eventName"),
                "eventNameStatus": row.get("eventNameStatus", "UNKNOWN"),
                "eventActionRowCount": 0,
                "eventActionStatuses": [],
                "mediaReferences": {},
            }
            events[key] = record
        record["eventActionRowCount"] += 1
        record["eventActionStatuses"].append(row.get("status"))
        for media in row.get("mediaReferences", []):
            media_id = str(media.get("sourceId", ""))
            identity = (
                media_id,
                str(media.get("sourceObjectId", "")),
                str((media.get("sourceIdField") or {}).get("offset", "")),
            )
            record["mediaReferences"][identity] = {
                "sourceId": media.get("sourceId"),
                "sourceIdField": media.get("sourceIdField"),
                "sourceObjectId": media.get("sourceObjectId"),
                "sourceObjectClass": media.get("sourceObjectClass"),
                "wemMatchStatus": media.get("wemMatchStatus"),
                "wemSource": (media.get("wem") or {}).get("source"),
                "wav": (media.get("wem") or {}).get("wav"),
                "wavSha256": (media.get("wem") or {}).get("wavSha256"),
                "bankMediaMatchStatus": media.get("bankMediaMatchStatus"),
                "bankMediaOutput": (media.get("bankMedia") or {}).get("output"),
                "bankMediaWavOutput": (media.get("bankMedia") or {}).get("wavOutput"),
            }

    by_id: dict[str, list[dict]] = {}
    for record in events.values():
        record["eventActionStatuses"].sort(key=lambda value: str(value))
        record["mediaReferences"] = [
            record["mediaReferences"][key]
            for key in sorted(record["mediaReferences"])
        ]
        record["mediaReferenceCount"] = len(record["mediaReferences"])
        by_id.setdefault(record["eventId"], []).append(record)
    for values in by_id.values():
        values.sort(key=lambda item: (item["bankSource"], item["eventIndex"]))
    return by_id


def _sequence_rows(root: Path, project: Path, bank_stems: dict[str, list[dict]], events_by_id: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    romfs = source_dirs(root)["romfs"]
    rows = _jsonl(project / "manifests" / "bseq.jsonl")
    output_rows = []
    status_counts = Counter()
    decoded_sequences = 0
    unsupported = 0
    failed = 0
    pending = 0
    bank_name_reference_occurrences = 0
    exact_bank_name_reference_occurrences = 0
    bank_name_literals: set[str] = set()

    for manifest_row in rows:
        source_rel = _safe_source(str(manifest_row.get("source", "")))
        source_name = source_rel.as_posix()
        source = romfs.joinpath(*source_rel.parts)
        if not source.is_file():
            raise FileNotFoundError(f"missing BSEQ source: {source_name}")
        source_hash = sha256(source)
        if manifest_row.get("source_sha256") != source_hash:
            raise ValueError(f"BSEQ source hash mismatch: {source_name}")
        status = manifest_row.get("status")
        status_counts[str(status)] += 1
        if status in {"UNSUPPORTED"}:
            unsupported += 1
            continue
        if status == "FAILED":
            failed += 1
            continue
        if status not in BSEQ_SUCCESS:
            pending += 1
            continue

        output = _safe_decoded(project, str(manifest_row.get("output", "")))
        expected_relative = PurePosixPath("decoded") / VERSION / "romfs" / source_rel.with_suffix(".json")
        if PurePosixPath(output.relative_to(project).as_posix()) != expected_relative:
            raise ValueError(f"BSEQ JSON path is not mirrored: {source_name}")
        if not output.is_file():
            raise FileNotFoundError(f"missing BSEQ JSON output: {output}")
        output_hash = sha256(output)
        if manifest_row.get("output_sha256") != output_hash:
            raise ValueError(f"BSEQ JSON hash mismatch: {source_name}")
        source_bytes = source.read_bytes()
        if manifest_row.get("source_bytes") != len(source_bytes):
            raise ValueError(f"BSEQ source size mismatch: {source_name}")
        if hashlib.sha256(source_bytes).hexdigest() != source_hash:
            raise ValueError(f"BSEQ source changed during read: {source_name}")
        decoded = json.loads(output.read_text(encoding="utf-8"))
        if decoded.get("source", {}).get("sha256") != source_hash:
            raise ValueError(f"BSEQ JSON source hash mismatch: {source_name}")
        if decoded.get("source", {}).get("raw_hex") != source_bytes.hex():
            raise ValueError(f"BSEQ raw_hex does not match source bytes: {source_name}")

        sequence = decoded.get("sequence") or {}
        bank_references = _load_bank_references(sequence)
        bank_name_reference_occurrences += len(bank_references)
        bank_name_literals.update(reference["literal"] for reference in bank_references)
        exact_bank_name_reference_occurrences += sum(
            bool(bank_stems.get(reference["literal"])) for reference in bank_references
        )
        referenced_bank_sources = {
            bank["bankSource"]
            for reference in bank_references
            for bank in bank_stems.get(reference["literal"], [])
        }
        exact_bank_refs = [
            {
                **reference,
                "matchingBanks": [
                    {
                        "bankSource": bank["bankSource"],
                        "bankSourceSha256": bank["bankSourceSha256"],
                        "bankXml": bank["bankXml"],
                        "bankXmlSha256": bank["bankXmlSha256"],
                    }
                    for bank in bank_stems.get(reference["literal"], [])
                ],
            }
            for reference in bank_references
        ]
        decoded_sequences += 1
        for play in _play_commands(sequence):
            event_id = str(play["eventIdFNV1_32"])
            candidates = events_by_id.get(event_id, [])
            status_value, referenced_candidates = _candidate_status(candidates, referenced_bank_sources)
            output_rows.append({
                "schema": SCHEMA,
                "method": MAPPING_METHOD,
                "semanticsStatus": SEMANTICS,
                "sourceVersion": "Let's Go Pikachu 1.0.2",
                "sequenceSource": source_name,
                "sequenceSourceSha256": source_hash,
                "sequenceOutput": output.relative_to(project).as_posix(),
                "sequenceOutputSha256": output_hash,
                "sequenceParserCommit": decoded.get("decoder", {}).get("commit"),
                "commandDictionarySha256": decoded.get("decoder", {}).get("command_dictionary_sha256"),
                "groupIndex": play["groupIndex"],
                "commandIndex": play["commandIndex"],
                "startFrame": play["startFrame"],
                "endFrame": play["endFrame"],
                "eventLiteral": play["eventLiteral"],
                "parserParameters": play["parserParameters"],
                "eventIdFNV1_32": play["eventIdFNV1_32"],
                "eventIdHex": f"0x{play['eventIdFNV1_32']:08x}",
                "hashBasis": {
                    "algorithm": "FNV-1 32-bit",
                    "input": "lowercase eventLiteral encoded as UTF-8",
                    "implementationSource": "pinned wwiser wfnv.py",
                    "wwiserCommit": WWISER_COMMIT,
                },
                "sequenceBankNameReferences": exact_bank_refs,
                "matchingSequenceBankSources": sorted(referenced_bank_sources),
                "staticMatchStatus": status_value,
                "sequenceBankCandidateCount": len(referenced_candidates),
                "globalCandidateCount": len(candidates),
                "sequenceBankCandidates": referenced_candidates,
                "globalCandidates": candidates,
            })

    return output_rows, {
        "bseqManifestRows": len(rows),
        "bseqStatusCounts": dict(sorted(status_counts.items())),
        "decodedSequencesVerified": decoded_sequences,
        "unsupportedSequences": unsupported,
        "failedSequences": failed,
        "pendingSequences": pending,
        "bankNameReferenceOccurrences": bank_name_reference_occurrences,
        "exactBankNameReferenceOccurrences": exact_bank_name_reference_occurrences,
        "distinctBankNameLiterals": len(bank_name_literals),
    }


def _candidate_identity(candidate: dict) -> tuple[str, str, str, str]:
    source = _safe_source(str(candidate.get("bankSource", ""))).as_posix()
    bank_id = str(candidate.get("bankId", ""))
    event_id = str(candidate.get("eventId", ""))
    event_index = str(candidate.get("eventIndex", ""))
    if not bank_id.isdecimal() or not event_id.isdecimal() or not event_index.isdecimal():
        raise ValueError("Wwise event candidate has a non-decimal bank/event/index value")
    return source, bank_id, event_id, event_index


def _validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} is not a lowercase SHA-256")
    return value


def build_sequence_event_literal_candidates(rows: list[dict]) -> tuple[list[dict], dict]:
    """Build a separate, non-semantic label-candidate view from verified map rows."""
    grouped: dict[tuple[str, str, str, str], dict] = {}
    link_count = 0
    referenced_link_count = 0
    outside_link_count = 0
    no_candidate_rows = 0
    distinct_literals: set[str] = set()
    distinct_event_ids: set[str] = set()

    for row in rows:
        if (
            row.get("schema") != SCHEMA
            or row.get("method") != MAPPING_METHOD
            or row.get("semanticsStatus") != SEMANTICS
            or row.get("sourceVersion") != "Let's Go Pikachu 1.0.2"
        ):
            raise ValueError("BSEQ-to-Wwise row does not have the expected exact-build scope")
        literal = row.get("eventLiteral")
        event_id_raw = row.get("eventIdFNV1_32")
        if not isinstance(literal, str) or not literal:
            raise ValueError("BSEQ event literal is missing")
        if isinstance(event_id_raw, bool) or not isinstance(event_id_raw, int) or not 0 <= event_id_raw <= 0xFFFFFFFF:
            raise ValueError("BSEQ event ID is not a u32 FNV value")
        expected_event_id = str(event_id_raw)
        expected_hex = f"0x{event_id_raw:08x}"
        if fnv1_32(literal) != event_id_raw:
            raise ValueError("BSEQ event literal does not match its pinned FNV-1 32-bit value")
        if row.get("eventIdHex") != expected_hex:
            raise ValueError("BSEQ event literal hexadecimal ID differs from its FNV value")

        hash_basis = row.get("hashBasis")
        if (
            not isinstance(hash_basis, dict)
            or hash_basis.get("algorithm") != "FNV-1 32-bit"
            or hash_basis.get("input") != "lowercase eventLiteral encoded as UTF-8"
            or hash_basis.get("implementationSource") != "pinned wwiser wfnv.py"
            or hash_basis.get("wwiserCommit") != WWISER_COMMIT
        ):
            raise ValueError("BSEQ event literal lacks the expected pinned hash provenance")
        if row.get("sequenceParserCommit") != PBSEQTOOL_COMMIT:
            raise ValueError("BSEQ event literal does not come from the pinned parser revision")
        _validate_sha256(row.get("sequenceSourceSha256"), "BSEQ source hash")
        _validate_sha256(row.get("sequenceOutputSha256"), "BSEQ JSON hash")
        _validate_sha256(row.get("commandDictionarySha256"), "BSEQ command dictionary hash")
        sequence_source = _safe_source(str(row.get("sequenceSource", ""))).as_posix()
        sequence_output = PurePosixPath(str(row.get("sequenceOutput", "")).replace("\\", "/"))
        _safe_decoded(Path("/"), sequence_output.as_posix())

        raw_candidates = row.get("globalCandidates")
        if not isinstance(raw_candidates, list):
            raise ValueError("BSEQ-to-Wwise global candidate list is malformed")
        if row.get("globalCandidateCount") != len(raw_candidates):
            raise ValueError("BSEQ-to-Wwise global candidate count differs from its list")
        raw_referenced = row.get("sequenceBankCandidates")
        if not isinstance(raw_referenced, list):
            raise ValueError("BSEQ-to-Wwise sequence-bank candidate list is malformed")
        if row.get("sequenceBankCandidateCount") != len(raw_referenced):
            raise ValueError("BSEQ-to-Wwise sequence-bank candidate count differs from its list")
        referenced_sources = row.get("matchingSequenceBankSources")
        if not isinstance(referenced_sources, list) or any(not isinstance(item, str) for item in referenced_sources):
            raise ValueError("BSEQ-to-Wwise referenced-bank source list is malformed")
        referenced_source_set = {
            _safe_source(source).as_posix() for source in referenced_sources
        }

        global_by_identity: dict[tuple[str, str, str, str], dict] = {}
        for candidate in raw_candidates:
            if not isinstance(candidate, dict):
                raise ValueError("Wwise event candidate is not an object")
            identity = _candidate_identity(candidate)
            if identity in global_by_identity:
                raise ValueError("BSEQ row repeats a Wwise bank/event candidate")
            if identity[2] != expected_event_id or candidate.get("eventIdHex") != expected_hex:
                raise ValueError("Wwise event candidate ID differs from the BSEQ FNV value")
            _validate_sha256(candidate.get("bankSourceSha256"), "BNK source hash")
            _validate_sha256(candidate.get("bankXmlSha256"), "BNK XML hash")
            bank_xml = PurePosixPath(str(candidate.get("bankXml", "")).replace("\\", "/"))
            _safe_decoded(Path("/"), bank_xml.as_posix())
            global_by_identity[identity] = {**candidate, "bankXml": bank_xml.as_posix()}

        referenced_by_identity: dict[tuple[str, str, str, str], dict] = {}
        for candidate in raw_referenced:
            if not isinstance(candidate, dict):
                raise ValueError("Wwise sequence-bank candidate is not an object")
            identity = _candidate_identity(candidate)
            if identity in referenced_by_identity:
                raise ValueError("BSEQ row repeats a sequence-bank event candidate")
            referenced_by_identity[identity] = candidate
        expected_referenced = {
            identity: candidate
            for identity, candidate in global_by_identity.items()
            if identity[0] in referenced_source_set
        }
        if set(referenced_by_identity) != set(expected_referenced):
            raise ValueError("sequence-bank candidates do not match the referenced-bank source list")

        if not global_by_identity:
            no_candidate_rows += 1
            continue
        distinct_literals.add(literal)
        distinct_event_ids.add(expected_event_id)
        for identity, candidate in global_by_identity.items():
            link_count += 1
            is_sequence_referenced = identity[0] in referenced_source_set
            referenced_link_count += int(is_sequence_referenced)
            outside_link_count += int(not is_sequence_referenced)
            source_hash = _validate_sha256(candidate.get("bankSourceSha256"), "BNK source hash")
            xml_hash = _validate_sha256(candidate.get("bankXmlSha256"), "BNK XML hash")
            event_key = identity
            event_row = grouped.get(event_key)
            if event_row is None:
                event_row = {
                    "schema": LABEL_CANDIDATE_SCHEMA,
                    "method": "STATIC_BSEQ_LITERAL_TO_WWISE_FNV1_32_EVENT_ID_CANDIDATE",
                    "semanticsStatus": LABEL_CANDIDATE_SEMANTICS,
                    "sourceVersion": "Let's Go Pikachu 1.0.2",
                    "bankSource": identity[0],
                    "bankId": identity[1],
                    "bankSourceSha256": source_hash,
                    "bankXml": candidate["bankXml"],
                    "bankXmlSha256": xml_hash,
                    "eventId": identity[2],
                    "eventIdHex": expected_hex,
                    "eventIndex": identity[3],
                    "eventName": candidate.get("eventName"),
                    "eventNameStatus": candidate.get("eventNameStatus", "UNKNOWN"),
                    "eventNameWasUpdated": False,
                    "sequenceLiteralCandidates": {},
                }
                grouped[event_key] = event_row
            elif (
                event_row["bankSourceSha256"] != source_hash
                or event_row["bankXml"] != candidate["bankXml"]
                or event_row["bankXmlSha256"] != xml_hash
                or event_row["eventName"] != candidate.get("eventName")
                or event_row["eventNameStatus"] != candidate.get("eventNameStatus", "UNKNOWN")
            ):
                raise ValueError("Wwise event candidate provenance differs across BSEQ observations")

            literal_row = event_row["sequenceLiteralCandidates"].setdefault(
                literal,
                {
                    "literal": literal,
                    "status": "STATIC_FNV_EVENT_ID_CANDIDATE",
                    "hashBasis": hash_basis,
                    "observations": [],
                },
            )
            if literal_row["hashBasis"] != hash_basis:
                raise ValueError("sequence literal hash basis differs across observations")
            literal_row["observations"].append({
                "sequenceSource": sequence_source,
                "sequenceSourceSha256": row["sequenceSourceSha256"],
                "sequenceOutput": sequence_output.as_posix(),
                "sequenceOutputSha256": row["sequenceOutputSha256"],
                "sequenceParserCommit": row["sequenceParserCommit"],
                "commandDictionarySha256": row["commandDictionarySha256"],
                "groupIndex": row.get("groupIndex"),
                "commandIndex": row.get("commandIndex"),
                "startFrame": row.get("startFrame"),
                "endFrame": row.get("endFrame"),
                "parserParameters": row.get("parserParameters"),
                "candidateScope": (
                    "SEQUENCE_REFERENCED_BANK_ID_CANDIDATE"
                    if is_sequence_referenced
                    else "OUTSIDE_SEQUENCE_BANKS_ID_CANDIDATE"
                ),
                "matchingSequenceBankSources": sorted(referenced_source_set),
            })

    output_rows = []
    label_conflicts = 0
    for identity, event_row in sorted(grouped.items()):
        literal_rows = []
        for literal, literal_row in sorted(event_row["sequenceLiteralCandidates"].items()):
            literal_row["observations"].sort(
                key=lambda item: (
                    item["sequenceSource"], item["groupIndex"], item["commandIndex"],
                )
            )
            literal_rows.append(literal_row)
        event_row["sequenceLiteralCandidates"] = literal_rows
        event_row["candidateLiteralConflict"] = len(literal_rows) > 1
        label_conflicts += int(event_row["candidateLiteralConflict"])
        output_rows.append(event_row)

    return output_rows, {
        "status": "ANALYZED",
        "schema": LABEL_CANDIDATE_SCHEMA,
        "method": "STATIC_BSEQ_LITERAL_TO_WWISE_FNV1_32_EVENT_ID_CANDIDATE",
        "sourceVersion": "Let's Go Pikachu 1.0.2",
        "semanticsStatus": LABEL_CANDIDATE_SEMANTICS,
        "wwiserCommit": WWISER_COMMIT,
        "sequenceParserCommit": PBSEQTOOL_COMMIT,
        "sequenceRows": len(rows),
        "globalCandidateLinks": link_count,
        "sequenceReferencedBankLinks": referenced_link_count,
        "outsideSequenceBankLinks": outside_link_count,
        "sequenceRowsWithoutEventIdCandidates": no_candidate_rows,
        "candidateBankEventPairs": len(output_rows),
        "distinctWwiseEventIdsWithLiteralCandidates": len(distinct_event_ids),
        "distinctSequenceLiterals": len(distinct_literals),
        "bankEventPairsWithMultipleLiteralCandidates": label_conflicts,
        "eventNameFieldsUpdated": 0,
    }


def write_sequence_event_literal_candidates(
    project: Path,
    rows: list[dict],
    input_manifest: Path | None = None,
) -> dict:
    """Atomically write the candidate-label sidecar and its hash summary."""
    project = Path(project)
    output_rows, summary = build_sequence_event_literal_candidates(rows)
    output = project / "manifests" / "wwise_sequence_event_label_candidates.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in output_rows
    )
    temporary.write_bytes(payload.encode("utf-8"))
    temporary.replace(output)
    summary["manifest"] = output.relative_to(project).as_posix()
    summary["manifestBytes"] = output.stat().st_size
    summary["manifestSha256"] = sha256(output)
    if input_manifest is not None:
        input_manifest = Path(input_manifest)
        summary["inputManifest"] = input_manifest.relative_to(project).as_posix()
        summary["inputManifestBytes"] = input_manifest.stat().st_size
        summary["inputManifestSha256"] = sha256(input_manifest)
    summary_path = project / "manifests" / "wwise_sequence_event_label_candidates.summary.json"
    summary_temporary = summary_path.with_name(summary_path.name + ".partial")
    summary_payload = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    summary_temporary.write_bytes(summary_payload.encode("utf-8"))
    summary_temporary.replace(summary_path)
    return summary


def build_sequence_wwise_map(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    """Verify all inputs and write an auditable BSEQ literal-to-Wwise map."""
    banks, bank_stems = _bank_manifest_index(root, project)
    wwise_rows = _jsonl(project / "manifests" / "wwise_event_media.jsonl")
    events_by_id = _event_index(wwise_rows, banks)
    rows, sequence_summary = _sequence_rows(root, project, bank_stems, events_by_id)

    counts = Counter(row["staticMatchStatus"] for row in rows)
    output = project / "manifests" / "bseq_wwise_events.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(output)
    label_candidate_summary = write_sequence_event_literal_candidates(
        project, rows, input_manifest=output,
    )
    orphan_wem_audit_summary = write_unreferenced_wem_id_audit(root, project)
    manifest_sha256 = sha256(output)
    summary = {
        "status": "ANALYZED" if not sequence_summary["failedSequences"] and not sequence_summary["pendingSequences"] else "ANALYZED_WITH_INCOMPLETE_BSEQ_COVERAGE",
        "schema": SCHEMA,
        "method": MAPPING_METHOD,
        "sourceVersion": "Let's Go Pikachu 1.0.2",
        "semanticsStatus": SEMANTICS,
        "wwiserCommit": WWISER_COMMIT,
        "verifiedBanks": len(banks),
        "wwiseEventActionRows": len(wwise_rows),
        "uniqueWwiseEventObjects": sum(len(values) for values in events_by_id.values()),
        "uniqueWwiseEventIds": len(events_by_id),
        **sequence_summary,
        "playEventCommandsMapped": len(rows),
        "staticMatchStatusCounts": dict(sorted(counts.items())),
        "distinctEventLiterals": len({row["eventLiteral"] for row in rows}),
        "distinctFNVEventIds": len({row["eventIdFNV1_32"] for row in rows}),
        "manifestBytes": output.stat().st_size,
        "manifestSha256": manifest_sha256,
        "manifest": str(output),
        "sequenceEventLiteralCandidates": label_candidate_summary,
        "unreferencedWemIdAudit": orphan_wem_audit_summary,
    }
    summary_path = project / "manifests" / "bseq_wwise_events.summary.json"
    summary_temporary = summary_path.with_name(summary_path.name + ".partial")
    summary_temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_temporary.replace(summary_path)
    return summary
