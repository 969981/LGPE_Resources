"""Build per-source analysis coverage from the real scan and decoder manifests."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .core import PROJECT

SUCCESS = {
    "DECODED", "DECODED_EXISTING_VERIFIED", "CROSS_VALIDATED",
    "STRUCTURE_DECODED_RENDER_UNSUPPORTED",
}


def build_coverage(project: Path = PROJECT) -> dict:
    scan_path = project / "manifests" / "files.csv"
    if not scan_path.is_file():
        raise FileNotFoundError("run uv run lgpe scan before coverage")
    sources = {}
    with scan_path.open("r", encoding="utf-8-sig", newline="") as stream:
        for item in csv.DictReader(stream):
            key = (item["partition"].casefold(), item["relative_path"].casefold())
            sources[key] = {
                "partition": item["partition"],
                "relative_path": item["relative_path"],
                "extension": item["suffix"],
                "kind": item["kind"],
                "source_bytes": int(item["bytes"]),
                "signature": item["signature"],
                "header_hex": item["header_hex"],
                "scan_status": "SCANNED",
                "analysis_status": "UNKNOWN",
                "status_reason": "No verified decoder or structure result recorded for this source yet.",
                "decoded_outputs": 0,
                "domain": "",
            }

    def apply(partition: str, relative: str, status: str, reason: str, outputs: int, domain: str) -> None:
        key = (partition.casefold(), relative.replace("\\", "/").casefold())
        row = sources.get(key)
        if row is None:
            return
        current = row["analysis_status"]
        if current == "DECODED" and status != "DECODED":
            return
        if status in SUCCESS:
            row["analysis_status"] = "DECODED"
            row["status_reason"] = reason or status
            row["decoded_outputs"] = max(row["decoded_outputs"], outputs)
            row["domain"] = domain
        elif current != "DECODED" and status in {"FAILED", "UNSUPPORTED", "UNKNOWN", "PENDING"}:
            row["analysis_status"] = status
            row["status_reason"] = reason or status
            row["domain"] = domain

    manifests = [
        ("archive", "archives.jsonl"),
        ("gamedata", "gamedata.jsonl"),
        ("learnset", "learnsets.jsonl"),
        ("audio", "audio.jsonl"),
        ("wave", "waves.jsonl"),
        ("bseq", "bseq.jsonl"),
        ("bnk", "bnk.jsonl"),
        ("texture", "textures.jsonl"),
        ("model", "models.jsonl"),
        ("animation", "animations.jsonl"),
        ("particle", "particles.jsonl"),
        ("collision", "collisions.jsonl"),
        ("font", "fonts.jsonl"),
        ("font", "bffnt.jsonl"),
        ("amx", "amx_headers.jsonl"),
    ]
    for domain, name in manifests:
        path = project / "manifests" / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            source = record.get("source")
            if not source:
                continue
            status = record.get("status", "UNKNOWN")
            outputs = int(record.get("member_count", 0))
            if status in SUCCESS and not outputs:
                outputs = 1
            apply(
                record.get("partition", "romfs"), source, status,
                record.get("reason") or record.get("error") or status,
                outputs, domain,
            )
            if domain == "gamedata" and status in SUCCESS and record.get("companion"):
                apply(
                    "romfs", record["companion"], "DECODED",
                    "Consumed as the paired message label/index table.", 0, domain,
                )

    # Receipts are the authoritative output count when one source produces
    # multiple decoded layers, such as raw GFPAK members plus parsed JSON.
    receipt_outputs: dict[tuple[str, str], set[str]] = defaultdict(set)
    receipt_path = project / "manifests" / "outputs.jsonl"
    if receipt_path.is_file():
        for line in receipt_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            receipt = json.loads(line)
            key = (
                str(receipt.get("partition", "romfs")).casefold(),
                str(receipt.get("relative_source", "")).replace("\\", "/").casefold(),
            )
            if key in sources and receipt.get("output_file"):
                receipt_outputs[key].add(str(receipt["output_file"]).casefold())
    for key, outputs in receipt_outputs.items():
        sources[key]["decoded_outputs"] = len(outputs)

    status_counts = Counter(row["analysis_status"] for row in sources.values())
    extension_counts = defaultdict(Counter)
    for row in sources.values():
        extension_counts[row["extension"] or "<no extension>"][row["analysis_status"]] += 1
    result_rows = sorted(
        sources.values(),
        key=lambda row: (row["partition"].casefold(), row["relative_path"].casefold()),
    )
    fields = [
        "partition", "relative_path", "extension", "kind", "source_bytes",
        "signature", "header_hex", "scan_status", "analysis_status",
        "status_reason", "decoded_outputs", "domain",
    ]
    output_csv = project / "manifests" / "coverage.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_csv.with_name(output_csv.name + ".partial")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result_rows)
    temporary.replace(output_csv)
    summary = {
        "scanned": len(result_rows),
        "decoded_sources": status_counts["DECODED"],
        "failed_sources": status_counts["FAILED"],
        "unknown_sources": status_counts["UNKNOWN"],
        "unsupported_sources": status_counts["UNSUPPORTED"],
        "pending_sources": status_counts["PENDING"],
        "decoded_outputs": sum(row["decoded_outputs"] for row in result_rows),
        "by_status": dict(sorted(status_counts.items())),
        "by_extension": {
            extension: dict(sorted(counts.items()))
            for extension, counts in sorted(extension_counts.items())
        },
        "manifest": str(output_csv),
    }
    summary_path = project / "manifests" / "coverage.summary.json"
    summary_temp = summary_path.with_name(summary_path.name + ".partial")
    summary_temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_temp.replace(summary_path)
    return summary
