"""Rehydrate per-source asset conversion metadata from authoritative output receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MANIFESTS = {"texture": "textures.jsonl", "model": "models.jsonl"}
STATUSES = {"DECODED", "DECODED_EXISTING_VERIFIED"}
FIELDS = {
    "source_sha256": "source_sha256",
    "output_sha256": "output_sha256",
    "output_size": "output_bytes",
    "validation": "validation",
    "conversion": "conversion",
    "tool_version": "tool_versions",
    "command": "commands",
}


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def restore_asset_manifest(project: Path, domain: str, pixel_format: str | None = None) -> dict:
    if domain not in MANIFESTS:
        raise ValueError(f"unsupported asset domain: {domain}")
    receipt_path = project / "manifests" / "outputs.jsonl"
    manifest_path = project / "manifests" / MANIFESTS[domain]
    if not receipt_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("asset manifest or output receipts are missing")

    methods = {f"lgpe_research.asset_batch/{domain}", f"lgpe_research.assets_decode/{domain}"}
    receipts = {}
    for line in receipt_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        receipt = json.loads(line)
        if receipt.get("method") not in methods or not receipt.get("relative_source"):
            continue
        if pixel_format and (receipt.get("conversion") or {}).get("pixel_format") != pixel_format:
            continue
        key = receipt["relative_source"].replace("\\", "/").casefold()
        if key in receipts:
            raise ValueError(f"multiple output receipts for one-to-one asset: {key}")
        receipts[key] = receipt

    original_bytes = manifest_path.read_bytes()
    rows = [json.loads(line) for line in original_bytes.decode("utf-8").splitlines() if line.strip()]
    updated = 0
    matched = 0
    for row in rows:
        if row.get("domain") != domain or row.get("status") not in STATUSES:
            continue
        key = str(row.get("source", "")).replace("\\", "/").casefold()
        receipt = receipts.get(key)
        if pixel_format and receipt is None:
            continue
        if receipt is None:
            raise ValueError(f"no output receipt for successful asset manifest row: {key}")
        for check in ("source_sha256", "output_sha256"):
            current = row.get(check)
            expected = receipt.get(check)
            if current and expected and current != expected:
                raise ValueError(f"{check} mismatch for {key}")
        matched += 1
        for receipt_field, manifest_field in FIELDS.items():
            value = receipt.get(receipt_field)
            if value is not None and row.get(manifest_field) != value:
                row[manifest_field] = value
                updated += 1

    rendered = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".partial")
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    temporary.replace(manifest_path)
    result = {
        "domain": domain,
        "matched_rows": matched,
        "restored_fields": updated,
        "manifest_sha256_before": hashlib.sha256(original_bytes).hexdigest(),
        "manifest_sha256_after": _sha256(manifest_path),
        "receipts_sha256": _sha256(receipt_path),
    }
    log_path = project / "logs" / f"{domain}-manifest-provenance-restore.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=sorted(MANIFESTS), required=True)
    parser.add_argument("--pixel-format", help="restore only rows whose receipt records this pixel format")
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    print(json.dumps(restore_asset_manifest(args.project.resolve(), args.domain, args.pixel_format), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
