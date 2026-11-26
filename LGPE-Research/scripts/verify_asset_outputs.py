"""Revalidate decoded asset hashes/structures and register verified asset receipts."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path, PurePosixPath

from lgpe_research import assets_decode
from lgpe_research.batch import _receipt
from lgpe_research.core import VERSION, add_receipts, ensure_inside, sha256, source_dirs


DOMAINS = {
    "texture": ("textures.jsonl", ".png"),
    "model": ("models.jsonl", ".glb"),
}
SUCCESS = {"DECODED", "DECODED_EXISTING_VERIFIED"}


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    romfs = source_dirs(project.parent)["romfs"]
    results = []
    receipts = []
    totals = Counter()
    for domain, (manifest_name, output_suffix) in DOMAINS.items():
        path = project / "manifests" / manifest_name
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            status = row.get("status", "UNKNOWN")
            totals[f"{domain}:{status}"] += 1
            if status not in SUCCESS:
                continue
            record = {"domain": domain, "source": row["source"], "status": "VERIFIED"}
            try:
                source_rel = PurePosixPath(row["source"])
                if source_rel.is_absolute() or ".." in source_rel.parts or not source_rel.parts:
                    raise ValueError("unsafe source path in manifest")
                source = ensure_inside(romfs.joinpath(*source_rel.parts), romfs)
                expected_rel = Path(*source_rel.parts).with_suffix(output_suffix)
                expected = project / "decoded" / VERSION / "romfs" / expected_rel
                output = ensure_inside(project / Path(row["output"]), project / "decoded")
                if output != expected.resolve():
                    raise ValueError(f"output path does not mirror source: {output}")
                source_hash = sha256(source)
                output_hash = sha256(output)
                if source_hash != row.get("source_sha256"):
                    raise ValueError("source SHA256 differs from manifest")
                if output_hash != row.get("output_sha256"):
                    raise ValueError("output SHA256 differs from manifest")
                validation = assets_decode.validate_output(output)
                record.update({
                    "source_sha256": source_hash,
                    "output_sha256": output_hash,
                    "output_bytes": output.stat().st_size,
                    "validation": validation,
                })
                if status == "DECODED":
                    tool_versions = row.get("tool_versions", {})
                    receipts.append(_receipt(
                        project, project.parent, row["source"], source, output,
                        "lgpe_research.asset_batch/" + domain,
                        tool_versions,
                        source_sha256=source_hash,
                        output_sha256=output_hash,
                        status=status,
                        validation=validation,
                        conversion=row.get("conversion"),
                        command=row.get("commands", []),
                    ))
                totals[f"{domain}:verified"] += 1
            except Exception as exc:
                record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
                totals[f"{domain}:verification_failed"] += 1
            results.append(record)

    if receipts:
        add_receipts(project, receipts, trusted_outputs=True)
    summary = {"checks": dict(sorted(totals.items())), "verified_outputs": len([r for r in results if r["status"] == "VERIFIED"]), "failed_outputs": len([r for r in results if r["status"] == "FAILED"]), "receipts_registered": len(receipts), "results": results}
    log = project / "logs" / "asset-output-validation.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False, sort_keys=True))
    return int(summary["failed_outputs"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
