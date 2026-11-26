"""Cross-reference exact-build main string literals with GFBCol candidates."""
from __future__ import annotations

import re
import hashlib
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path
import sys

from .core import NCA, PROJECT, source_dirs


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
IMAGE_BASE = "0x7100000000"
TOKEN_HANDLER = "main+0xb660"
EXPECTED_CALLSITE_OFFSETS = (
    "24f48c",
    "24f4e4",
    "24f534",
    "24f584",
    "24f5d4",
    "24f624",
)
EXPECTED_GFB_COL_TOKENS = (
    "col_wall",
    "col_water",
    "col_jump",
    "col_sky",
    "col_sekichiku",
    "col_safety",
)
STRING_CANDIDATE = "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE"


def summarize_gfbcol_token_handler_trace(
    trace_text: str,
    expected_main_sha256: str = MAIN_SHA256,
) -> dict:
    """Validate the saved read-only Ghidra trace for the six exact-build calls."""
    summary_matches = re.findall(
        r"SUMMARY\tmain_sha256=([0-9a-f]{64})"
        r"\thandler=(main\+0x[0-9a-f]+)"
        r"\tincoming_references=(\d+)"
        r"\texpected_call_sites=(\d+)/(\d+)"
        r"\tinstructions=(\d+)"
        r"\tdirect_calls=(\d+)"
        r"\tcontext_instructions=(\d+)"
        r"\tsourceHashUnchanged=(true|false)"
        r"\treadOnly=(true|false)"
        r"\tsemantics=([A-Z_]+)",
        trace_text,
    )
    if len(summary_matches) != 1:
        raise ValueError("Ghidra trace must contain exactly one token-handler summary")

    (
        main_sha256,
        handler,
        incoming_references,
        expected_seen,
        expected_total,
        instructions,
        direct_calls,
        context_instructions,
        source_unchanged,
        read_only,
        semantics,
    ) = summary_matches[0]
    if main_sha256 != expected_main_sha256:
        raise ValueError("Ghidra trace main SHA-256 differs from the exact build")
    if handler != TOKEN_HANDLER or semantics != "UNKNOWN":
        raise ValueError("Ghidra trace does not preserve the expected handler/UNKNOWN scope")
    if source_unchanged != "true" or read_only != "true":
        raise ValueError("Ghidra trace is not verified read-only against an unchanged main")
    if int(expected_seen) != len(EXPECTED_CALLSITE_OFFSETS) or int(expected_total) != len(
        EXPECTED_CALLSITE_OFFSETS
    ):
        raise ValueError("Ghidra trace did not confirm all six expected callsites")
    if int(context_instructions) <= 0:
        raise ValueError("Ghidra trace did not record callsite instruction contexts")

    observed = re.findall(
        r"TARGET_XREF\tfrom=main\+0x([0-9a-f]+)"
        r"\ttype=UNCONDITIONAL_CALL"
        r"\towner=NONE"
        r"\tinstruction=bl 0x710000b660",
        trace_text,
    )
    observed_expected = [offset for offset in EXPECTED_CALLSITE_OFFSETS if offset in observed]
    if observed_expected != list(EXPECTED_CALLSITE_OFFSETS):
        raise ValueError("Ghidra trace is missing one or more of the six expected callsites")

    contextual = re.findall(
        r"CALL_CONTEXT\tcallsite=main\+0x([0-9a-f]+)"
        r"\taddress=main\+0x([0-9a-f]+)\towner=NONE"
        r"\tflow=UNCONDITIONAL_CALL\tassembly=bl 0x710000b660",
        trace_text,
    )
    contextual_expected = [
        offset for offset in EXPECTED_CALLSITE_OFFSETS
        if (offset, offset) in contextual
    ]
    if contextual_expected != list(EXPECTED_CALLSITE_OFFSETS):
        raise ValueError("Ghidra trace lacks ownerless direct-call context for all six sites")

    return {
        "main_sha256": main_sha256,
        "handler": handler,
        "incoming_references": int(incoming_references),
        "expected_call_sites": int(expected_seen),
        "verified_callsite_offsets": observed_expected,
        "instructions": int(instructions),
        "direct_calls": int(direct_calls),
        "context_instructions": int(context_instructions),
        "read_only": True,
        "source_hash_unchanged": True,
        "semantics": "UNKNOWN",
    }


def summarize_gfbcol_token_owner_trace(
    trace_text: str,
    expected_main_sha256: str = MAIN_SHA256,
) -> dict:
    """Validate the temporary exact-build caller boundary without naming fields."""
    summary_matches = re.findall(
        r"SUMMARY\tmain_sha256=([0-9a-f]{64})"
        r"\tentry=(main\+0x[0-9a-f]+)"
        r"\tcall_sites=(\d+)/(\d+)"
        r"\tinstructions=(\d+)"
        r"\tentry_xrefs=(\d+)"
        r"\ttemporary_boundary=(true|false)"
        r"\tsourceHashUnchanged=(true|false)"
        r"\treadOnly=(true|false)"
        r"\tsemantics=([A-Z_]+)",
        trace_text,
    )
    if len(summary_matches) != 1:
        raise ValueError("Ghidra trace must contain exactly one owner-candidate summary")
    (
        main_sha256,
        entry,
        call_sites,
        call_sites_total,
        instructions,
        entry_xrefs,
        temporary_boundary,
        source_unchanged,
        read_only,
        semantics,
    ) = summary_matches[0]
    if main_sha256 != expected_main_sha256 or entry != "main+0x24f460":
        raise ValueError("Ghidra trace is not for the pinned main+0x24f460 candidate")
    if (call_sites, call_sites_total) != ("6", "6"):
        raise ValueError("Ghidra trace must confirm all six direct callsites")
    if temporary_boundary != "true" or source_unchanged != "true" or read_only != "true":
        raise ValueError("Ghidra candidate boundary was not temporary/read-only/hash-verified")
    if semantics != "UNKNOWN":
        raise ValueError("Ghidra trace assigns unsupported candidate semantics")

    candidate_match = re.search(
        r"CANDIDATE_FUNCTION\tentry=main\+0x24f460"
        r"\tbytes=(\d+)\tmin=(main\+0x[0-9a-f]+)"
        r"\tmax=(main\+0x[0-9a-f]+)\ttemporary_boundary=true",
        trace_text,
    )
    if not candidate_match:
        raise ValueError("Ghidra trace lacks the temporary candidate function range")
    function_bytes, function_min, function_max = candidate_match.groups()
    if (function_min, function_max) != ("main+0x24f460", "main+0x24f693"):
        raise ValueError("Ghidra candidate function range differs from the observed range")

    observed_calls = re.findall(
        r"INS\tmain\+0x([0-9a-f]+)\t[0-9a-f]+\tbl 0x710000b660",
        trace_text,
    )
    if [offset for offset in EXPECTED_CALLSITE_OFFSETS if offset in observed_calls] != list(
        EXPECTED_CALLSITE_OFFSETS
    ):
        raise ValueError("Ghidra trace lacks all six direct call instructions in the candidate")

    entry_ref_lines = []
    for line in trace_text.splitlines():
        if "ENTRY_XREF\t" not in line:
            continue
        payload = line.split("ENTRY_XREF\t", 1)[1]
        if payload.endswith(" (GhidraScript)  "):
            payload = payload[: -len(" (GhidraScript)  ")]
        entry_ref_lines.append(payload.rstrip())
    if len(entry_ref_lines) != int(entry_xrefs):
        raise ValueError("Ghidra entry reference line count differs from its summary")
    entry_refs = []
    for line in entry_ref_lines:
        reference_match = re.fullmatch(
            r"from=([^\t\r\n]+)\ttype=([^\t\r\n]+)"
            r"\towner=([^\t\r\n]+)\tinstruction=([^\t\r\n]+)",
            line,
        )
        if not reference_match:
            raise ValueError("Ghidra entry reference record is malformed")
        entry_refs.append(reference_match.groups())
    if entry_refs != [("main+0x15437d8", "DATA", "NONE", "NONE")]:
        raise ValueError("Ghidra trace entry reference differs from the recorded single data xref")
    data_value_match = re.search(
        r"ENTRY_DATA_WINDOW\tcell=main\+0x15437d8"
        r"\tvalue=(0x[0-9a-f]+)\tblock=(\.data)"
        r"\twritable=true\texecutable=false",
        trace_text,
    )
    if not data_value_match or data_value_match.group(1) != "0x710024f460":
        raise ValueError("Ghidra trace lacks the matching writable-data pointer observation")

    begin = re.search(r"DECOMPILED_BEGIN\tmain\+0x24f460[^\r\n]*\r?\n", trace_text)
    end = re.search(r"DECOMPILED_END\tmain\+0x24f460", trace_text)
    if not begin or not end or end.start() <= begin.end():
        raise ValueError("Ghidra trace lacks the bounded candidate decompilation")
    decompiled = trace_text[begin.end():end.start()]
    observed_tokens = re.findall(
        r'FUN_710000b660\([^,\r\n]+,\s*\(byte \*\)"([^"]+)"\)',
        decompiled,
    )
    if observed_tokens != list(EXPECTED_GFB_COL_TOKENS):
        raise ValueError("Ghidra candidate does not contain the six expected literal calls in order")
    if decompiled.count("lVar3 == param_5") != 6:
        raise ValueError("Ghidra candidate comparison expression count differs from six")
    if "+ 0x58" not in decompiled or "+ 0x48) + 0x18" not in decompiled:
        raise ValueError("Ghidra candidate does not show both observed object/vtable offsets")

    counter_writes = re.findall(
        r"\*\(int \*\)\(param_1 \+ (0x[0-9a-f]+)\)\s*=", decompiled
    )
    expected_counter_offsets = [
        "0x30", "0x34", "0x38", "0x3c", "0x40", "0x44", "0x48", "0x4c"
    ]
    if counter_writes != expected_counter_offsets:
        raise ValueError("Ghidra candidate counter-write offsets differ from the recorded sequence")

    return {
        "entry": entry,
        "function_bytes": int(function_bytes),
        "function_min": function_min,
        "function_max": function_max,
        "instruction_count": int(instructions),
        "call_sites": int(call_sites),
        "tokens": list(observed_tokens),
        "entry_xrefs": int(entry_xrefs),
        "entry_data_cell": entry_refs[0][0],
        "entry_data_value": data_value_match.group(1),
        "entry_data_block": data_value_match.group(2),
        "entry_data_writable": True,
        "entry_data_executable": False,
        "comparison_expression": "lVar3 == param_5",
        "object_value_offset": "0x58",
        "virtual_dispatch_offsets": ["0x48", "0x18"],
        "token_counter_offsets": dict(zip(EXPECTED_GFB_COL_TOKENS, expected_counter_offsets[:6])),
        "fallback_counter_offset": expected_counter_offsets[6],
        "total_counter_offset": expected_counter_offsets[7],
        "temporary_boundary": True,
        "read_only": True,
        "source_hash_unchanged": True,
        "semantics": "UNKNOWN",
    }


def cross_reference_slot0_candidates(main_report: dict, slot0_report: dict) -> dict:
    """Join byte-verified main literals to strict GFBCol string-shape candidates.

    The relation is exact UTF-8 value equality only. It does not assign a
    GFBCol field name, type, or application meaning.
    """
    if not main_report.get("checks_passed"):
        raise ValueError("exact main byte-link checks did not pass")
    if main_report.get("source", {}).get("sha256") != MAIN_SHA256:
        raise ValueError("main report is not for the exact Pikachu 1.0.2 build")
    if main_report.get("image_base") != IMAGE_BASE:
        raise ValueError("main report image base differs from the exact build")

    links = main_report.get("exact_instruction_links")
    if not isinstance(links, list) or not links:
        raise ValueError("main report has no exact instruction links")
    tokens: list[str] = []
    for link in links:
        if (
            not isinstance(link, dict)
            or link.get("status") != "ADDRESS_BYTES_MATCH"
            or link.get("bl_target_address") != "0x710000b660"
            or not isinstance(link.get("token"), str)
            or not link["token"]
        ):
            raise ValueError("main report contains non-exact byte links")
        tokens.append(link["token"])
    if len(tokens) != len(set(tokens)):
        raise ValueError("main report contains duplicate exact token links")

    inventory = slot0_report.get("inventory", {})
    selection = slot0_report.get("selection", {})
    entries = slot0_report.get("entries")
    if (
        slot0_report.get("source_version") != "Pokemon Let's Go Pikachu 1.0.2"
        or slot0_report.get("analysis_status") != "HYPOTHESIS_ONLY"
        or slot0_report.get("schema_status") != "UNKNOWN"
        or slot0_report.get("field_names_assigned") is not False
        or slot0_report.get("field_types_assigned") is not False
    ):
        raise ValueError("GFBCol probe does not preserve its 1.0.2 hypothesis-only scope")
    if slot0_report.get("source_failures"):
        raise ValueError("GFBCol probe contains source failures")
    if not isinstance(entries, list) or slot0_report.get("sources_read") != len(entries):
        raise ValueError("GFBCol probe source count differs from its entries")
    if (
        selection.get("limit") != 0
        or selection.get("selected_sources") != inventory.get("gfbcol_sources")
        or selection.get("selected_sources") != len(entries)
    ):
        raise ValueError("GFBCol probe did not read the full inventory")

    actual_counts: Counter[str] = Counter()
    source_occurrences: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    child_table_count = 0
    seen_sources: set[str] = set()
    source_hashes = []
    candidate_observations = []
    for entry in entries:
        source = entry.get("source")
        source_sha256 = entry.get("source_sha256")
        if not isinstance(source, str) or not source or source in seen_sources:
            raise ValueError("GFBCol probe has a missing or duplicate source path")
        if not isinstance(source_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", source_sha256
        ):
            raise ValueError("GFBCol probe has an invalid source SHA-256")
        seen_sources.add(source)
        source_hashes.append({"source": source, "source_sha256": source_sha256})
        elements = entry.get("elements", [])
        if not isinstance(elements, list):
            raise ValueError("GFBCol child-table elements are malformed")
        child_table_count += len(elements)
        for element in elements:
            candidate = element.get("string_candidate", {})
            if candidate.get("classification") != STRING_CANDIDATE:
                continue
            text = candidate.get("decoded_text")
            raw_hex = candidate.get("raw_bytes_hex")
            if not isinstance(text, str) or not isinstance(raw_hex, str):
                raise ValueError("GFBCol string-shape candidate lacks raw text bytes")
            try:
                raw = bytes.fromhex(raw_hex)
                decoded = raw.decode("utf-8", errors="strict")
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("GFBCol candidate raw bytes are not strict UTF-8") from exc
            if decoded != text or candidate.get("length") != len(raw):
                raise ValueError("GFBCol candidate text/length differs from raw bytes")
            actual_counts[text] += 1
            candidate_observations.append(
                {
                    "source": source,
                    "source_sha256": source_sha256,
                    "element_index": element.get("element_index"),
                    "table_offset": element.get("table_offset"),
                    "target_offset": candidate.get("target_offset"),
                    "length": candidate["length"],
                    "decoded_text": text,
                    "raw_bytes_hex": raw_hex,
                }
            )
            source_occurrences[text][source].append(
                {
                    "source_sha256": source_sha256,
                    "element_index": element.get("element_index"),
                    "table_offset": element.get("table_offset"),
                    "target_offset": candidate.get("target_offset"),
                    "length": candidate["length"],
                    "raw_bytes_hex": raw_hex,
                }
            )

    if child_table_count != slot0_report.get("slot0_child_table_count"):
        raise ValueError("GFBCol child-table count differs from the probe summary")
    if sum(actual_counts.values()) != slot0_report.get("valid_string_shape_candidates"):
        raise ValueError("GFBCol candidate count differs from the probe entries")
    if slot0_report.get("unresolved_child_fields") != 0:
        raise ValueError("GFBCol probe contains unresolved child fields")
    reported_counts = slot0_report.get("candidate_text_counts")
    if reported_counts != dict(sorted(actual_counts.items())):
        raise ValueError("GFBCol candidate text counts differ from source entries")
    if len(source_hashes) != slot0_report.get("sources_read"):
        raise ValueError("GFBCol source hash count differs from the full source scan")
    if len(candidate_observations) != slot0_report.get("valid_string_shape_candidates"):
        raise ValueError("GFBCol candidate observation count differs from the full probe")

    token_rows = []
    matched_tokens = 0
    matched_occurrences = 0
    for link in links:
        token = link["token"]
        occurrences = source_occurrences.get(token, {})
        occurrence_count = sum(len(items) for items in occurrences.values())
        if occurrence_count:
            matched_tokens += 1
            matched_occurrences += occurrence_count
        token_rows.append(
            {
                "token": token,
                "string_address": link["string_address"],
                "bl_address": link["bl_address"],
                "bl_target_address": link["bl_target_address"],
                "candidate_occurrences": occurrence_count,
                "sources": [
                    {
                        "source": source,
                        "source_sha256": items[0]["source_sha256"],
                        "elements": items,
                    }
                    for source, items in sorted(occurrences.items())
                ],
            }
        )

    return {
        "schema": "lgpe-gfbcol-main-token-crossref-v1",
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "analysis_status": "EXACT_LITERAL_VALUE_CROSS_REFERENCE",
        "schema_status": "UNKNOWN",
        "field_names_assigned": False,
        "field_types_assigned": False,
        "interpretation_limit": (
            "Exact main string bytes and exact GFBCol candidate text values are joined by "
            "literal UTF-8 equality. This does not prove a runtime load, field name, field "
            "type, token role, or collision semantics."
        ),
        "main": {
            "path": main_report["source"].get("path"),
            "bytes": main_report["source"].get("bytes"),
            "sha256": MAIN_SHA256,
            "image_base": IMAGE_BASE,
            "segments": main_report.get("segments", []),
            "exact_instruction_links": links,
        },
        "inventory": inventory,
        "gfbcol_probe": {
            "sources_read": len(entries),
            "source_failures": 0,
            "slot0_child_table_count": child_table_count,
            "valid_string_shape_candidates": sum(actual_counts.values()),
            "unresolved_child_fields": 0,
            "distinct_candidate_strings": len(actual_counts),
            "source_hashes": sorted(source_hashes, key=lambda item: item["source"]),
            "candidate_observations": sorted(
                candidate_observations,
                key=lambda item: (item["source"], item["element_index"]),
            ),
        },
        "summary": {
            "exact_main_tokens": len(links),
            "tokens_matching_candidate_strings": matched_tokens,
            "matched_candidate_occurrences": matched_occurrences,
        },
        "exact_main_token_candidates": token_rows,
    }


def _load_research_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load research script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_relative(path: Path, project: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def build_gfbcol_main_crossref_report(
    project: Path = PROJECT,
    root: Path | None = None,
) -> dict:
    """Re-scan exact local sources and join them to the guarded main/Ghidra trace."""
    project = Path(project).expanduser().resolve()
    game_root = Path(root or project.parent).expanduser().resolve()
    exefs = source_dirs(game_root)["exefs"]
    main_path = exefs / "main"
    main_hash_before = _sha256_file(main_path)

    main_script = project / "scripts" / "research" / "check_gfbcol_main_references.py"
    slot0_script = project / "scripts" / "research" / "probe_gfbcol_slot0_strings.py"
    main_module = _load_research_script(
        main_script, "_lgpe_check_gfbcol_main_references"
    )
    slot0_module = _load_research_script(
        slot0_script, "_lgpe_probe_gfbcol_slot0_strings"
    )
    main_report = main_module.inspect_main(main_path)
    slot0_report = slot0_module.run(project, game_root, limit=0, sources_file=None)
    report = cross_reference_slot0_candidates(main_report, slot0_report)
    report["main"]["path"] = main_path.relative_to(game_root).as_posix()
    report["main"]["path_base"] = "game_root"

    trace_script = project / "scripts" / "ghidra" / "InspectGfbcolTokenHandler.java"
    trace_wrapper = project / "scripts" / "ghidra" / "Run-InspectGfbcolTokenHandler.ps1"
    trace_log = project / "logs" / "ghidra-gfbcol-token-handler-v2-script.log"
    decompiler_log = project / "logs" / "ghidra-gfbcol-token-handler-v2.stdout.log"
    trace_summary = summarize_gfbcol_token_handler_trace(
        trace_log.read_text(encoding="utf-8"), main_report["source"]["sha256"]
    )
    decompiler_text = decompiler_log.read_text(encoding="utf-8")
    if (
        "DECOMPILED_BEGIN\tmain+0xb660" not in decompiler_text
        or "DECOMPILED_END\tmain+0xb660" not in decompiler_text
    ):
        raise ValueError("saved Ghidra stdout lacks the bounded main+0xb660 decompilation")

    main_hash_after = _sha256_file(main_path)
    if main_hash_before != main_hash_after or main_hash_after != main_report["source"]["sha256"]:
        raise ValueError("original exact-build main changed during the cross-reference scan")

    report["source_integrity"] = {
        "main_sha256_before": main_hash_before,
        "main_sha256_after": main_hash_after,
        "main_unchanged": True,
    }
    report["ghidra_trace"] = {
        "version": "12.2",
        "program": "Let's Go Pikachu 1.0.2 main",
        "trace_script": _project_relative(trace_script, project),
        "trace_script_sha256": _sha256_file(trace_script),
        "trace_wrapper": _project_relative(trace_wrapper, project),
        "trace_wrapper_sha256": _sha256_file(trace_wrapper),
        "script_log": _project_relative(trace_log, project),
        "script_log_sha256": _sha256_file(trace_log),
        "decompiler_log": _project_relative(decompiler_log, project),
        "decompiler_log_sha256": _sha256_file(decompiler_log),
        "summary": trace_summary,
    }

    owner_script = project / "scripts" / "ghidra" / "InspectGfbcolTokenOwner.java"
    owner_wrapper = project / "scripts" / "ghidra" / "Run-InspectGfbcolTokenOwner.ps1"
    owner_script_log = project / "logs" / "ghidra-gfbcol-token-owner-v1-script.log"
    owner_output_log = project / "logs" / "ghidra-gfbcol-token-owner-v1.stdout.log"
    owner_trace_summary = summarize_gfbcol_token_owner_trace(
        owner_output_log.read_text(encoding="utf-8"), main_report["source"]["sha256"]
    )
    report["ghidra_owner_candidate_trace"] = {
        "version": "12.2",
        "program": "Let's Go Pikachu 1.0.2 main",
        "trace_script": _project_relative(owner_script, project),
        "trace_script_sha256": _sha256_file(owner_script),
        "trace_wrapper": _project_relative(owner_wrapper, project),
        "trace_wrapper_sha256": _sha256_file(owner_wrapper),
        "script_log": _project_relative(owner_script_log, project),
        "script_log_sha256": _sha256_file(owner_script_log),
        "decompiler_log": _project_relative(owner_output_log, project),
        "decompiler_log_sha256": _sha256_file(owner_output_log),
        "summary": owner_trace_summary,
    }
    report["tool_provenance"] = {
        "main_byte_scanner": {
            "path": _project_relative(main_script, project),
            "sha256": _sha256_file(main_script),
        },
        "gfbcol_slot0_probe": {
            "path": _project_relative(slot0_script, project),
            "sha256": _sha256_file(slot0_script),
        },
    }
    return report
