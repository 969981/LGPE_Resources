"""Compare GameManagerGG worker raw records with the existing mirrored decoder outputs."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(project: Path, run_dir: Path) -> dict:
    project = project.resolve()
    run_dir = run_dir.resolve()
    receipt = json.loads((run_dir / "receipt.json").read_text(encoding="utf-8"))
    before = {row["sourcePath"]: row["sha256"] for row in receipt["inputHashesBefore"]}
    after = {row["sourcePath"]: row["sha256"] for row in receipt["inputHashesAfter"]}
    check(receipt["sourceUnchanged"] is True and before == after, "source hashes changed during worker run")
    check(receipt["pknxCommit"] == "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a", "pkNX commit mismatch")
    decoded = project / "decoded/1.0.2/romfs"
    count_checks = {}

    def json_output(source: str) -> dict:
        path = decoded / Path(source).with_suffix(".json")
        return json.loads(path.read_text(encoding="utf-8"))

    personal = rows(run_dir / "personal.jsonl")
    personal_decoded = json_output(personal[0]["sourcePath"])
    check(len(personal) == len(personal_decoded["entries"]), "personal entry count mismatch")
    for row in personal:
        index = row["containerIndex"]
        check(row["rawHex"].lower() == personal_decoded["entries"][index]["raw_hex"], f"personal raw mismatch at {index}")
        check(row["sourceSha256"] == before[row["sourcePath"]], f"personal source hash mismatch at {index}")
    count_checks["personalRecords"] = len(personal)

    moves = rows(run_dir / "moves.jsonl")
    moves_decoded = json_output(moves[0]["sourcePath"])
    check(len(moves) == len(moves_decoded["entries"]), "move entry count mismatch")
    for row in moves:
        index = row["containerIndex"]
        check(row["rawHex"].lower() == moves_decoded["entries"][index]["raw_hex"], f"move raw mismatch at {index}")
        check(row["sourceSha256"] == before[row["sourcePath"]], f"move source hash mismatch at {index}")
    count_checks["moveRecords"] = len(moves)

    for name, file_count_key in (("evolution", "evolutionFiles"), ("mega-evolution", "megaEvolutionFiles")):
        items = rows(run_dir / f"{name}.jsonl")
        for row in items:
            decoded_file = json_output(row["sourcePath"])
            joined = "".join(entry["raw_hex"] for entry in decoded_file["entries"])
            check(row["rawHex"].lower() == joined, f"{name} raw mismatch: {row['sourcePath']}")
            check(row["sourceSha256"] == before[row["sourcePath"]], f"{name} source hash mismatch: {row['sourcePath']}")
        check(len(items) == receipt["outputCounts"][file_count_key], f"{name} file count mismatch")
        count_checks[file_count_key] = len(items)

    learnset_manifest = {
        row["container_index"]: row
        for row in rows(project / "manifests/learnsets.jsonl")
        if row.get("status") == "DECODED"
    }
    learnsets = rows(run_dir / "learnsets.jsonl")
    check(len(learnset_manifest) == len(learnsets), "learnset manifest count mismatch")
    for row in learnsets:
        index = row["containerIndex"]
        manifest_row = learnset_manifest[index]
        output_rel = Path(manifest_row["output"].replace("\\", "/"))
        decoded_member = json.loads((project / output_rel).read_text(encoding="utf-8"))
        check(row["rawHex"].lower() == decoded_member["raw_hex"], f"learnset raw mismatch at container index {index}")
        check(row["internalPathStatus"] == "UNKNOWN_HASH_ONLY" and row["internalPath"] is None,
              f"learnset internal path was incorrectly asserted at index {index}")
    count_checks["learnsetEntries"] = len(learnsets)
    return {
        "status": "CROSS_VALIDATED",
        "sourceFiles": len(before),
        "sourceHashesUnchanged": True,
        "rawComparisons": sum(count_checks.values()),
        "counts": count_checks,
        "pknxCommit": receipt["pknxCommit"],
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_gamemanagergg_worker.py <project-root> <worker-run-dir>")
    print(json.dumps(verify(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))
