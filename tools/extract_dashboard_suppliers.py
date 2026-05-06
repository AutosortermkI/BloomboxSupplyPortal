#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "index.html"
DEFAULT_JSON = ROOT / "data" / "raw" / "current_dashboard_suppliers.json"
DEFAULT_CSV = ROOT / "data" / "raw" / "current_dashboard_suppliers.csv"


class SupplierExtractionError(ValueError):
    pass


def extract_const_array(source: str, const_name: str = "S") -> str:
    match = re.search(rf"\bconst\s+{re.escape(const_name)}\s*=\s*\[", source)
    if not match:
        raise SupplierExtractionError(f"const {const_name} array was not found")

    start = match.end() - 1
    depth = 0
    in_string = False
    quote = ""
    escaped = False

    for index in range(start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            continue

        if char in ("'", '"'):
            in_string = True
            quote = char
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]

    raise SupplierExtractionError(f"const {const_name} array was not closed")


def _split_top_level_objects(array_text: str) -> list[str]:
    objects: list[str] = []
    depth = 0
    start: int | None = None
    in_string = False
    quote = ""
    escaped = False

    for index, char in enumerate(array_text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            continue

        if char in ("'", '"'):
            in_string = True
            quote = char
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(array_text[start : index + 1])
                start = None

    if depth != 0:
        raise SupplierExtractionError("supplier object braces are unbalanced")
    return objects


_KEY_PATTERN = re.compile(r'([,{]\s*)([A-Za-z_$][\w$]*)\s*:')
_TRAILING_COMMA_PATTERN = re.compile(r",(\s*[}\]])")


def _jsonify_js_object(object_text: str) -> str:
    quoted_keys = _KEY_PATTERN.sub(r'\1"\2":', object_text)
    return _TRAILING_COMMA_PATTERN.sub(r"\1", quoted_keys)


def parse_supplier_array(array_text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for object_text in _split_top_level_objects(array_text):
        try:
            record = json.loads(_jsonify_js_object(object_text))
        except json.JSONDecodeError as exc:
            raise SupplierExtractionError(
                f"failed to parse supplier object near: {object_text[:120]}"
            ) from exc
        records.append(record)
    return records


def _is_canonical_dashboard_source(source: str) -> bool:
    return "CANONICAL_SUPPLIERS" in source and "SUPPLIER_REGISTRY_SOURCE" in source


def load_dashboard_suppliers(
    index_path: Path = DEFAULT_INDEX,
    *,
    allow_canonical: bool = False,
) -> list[dict[str, Any]]:
    source = Path(index_path).read_text(encoding="utf-8")
    if _is_canonical_dashboard_source(source) and not allow_canonical:
        raise SupplierExtractionError(
            "index.html now contains the canonical supplier registry. "
            "Pass --index pointing at a pre-canonical dashboard snapshot to rebuild "
            "the raw import, or use --allow-canonical only when intentionally "
            "extracting the current verified dashboard rows."
        )
    return parse_supplier_array(extract_const_array(source, "S"))


def write_json(records: list[dict[str, Any]], output_path: Path = DEFAULT_JSON) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if value is None:
        return ""
    return str(value)


def write_csv(records: list[dict[str, Any]], output_path: Path = DEFAULT_CSV) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for record in records:
        for field in record:
            if field not in fieldnames:
                fieldnames.append(field)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: _csv_value(record.get(field, "")) for field in fieldnames})


def summarize_records(records: list[dict[str, Any]]) -> dict[str, int]:
    ids = [record.get("id") for record in records]
    id_counts = Counter(ids)
    duplicate_rows = sum(count - 1 for count in id_counts.values() if count > 1)
    return {
        "record_count": len(records),
        "unique_id_count": len(id_counts),
        "duplicate_id_count": duplicate_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract the raw dashboard supplier array from index.html."
    )
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument(
        "--allow-canonical",
        action="store_true",
        help="Allow extraction from the current canonical dashboard instead of a pre-canonical raw import source.",
    )
    args = parser.parse_args()

    records = load_dashboard_suppliers(args.index, allow_canonical=args.allow_canonical)
    write_json(records, args.json)
    write_csv(records, args.csv)

    summary = summarize_records(records)
    print(f"record_count={summary['record_count']}")
    print(f"unique_id_count={summary['unique_id_count']}")
    print(f"duplicate_id_count={summary['duplicate_id_count']}")
    print(f"json={args.json}")
    print(f"csv={args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
