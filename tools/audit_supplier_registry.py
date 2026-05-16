#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RAW_JSON = ROOT / "data" / "raw" / "current_dashboard_suppliers.json"
REPORT_MD = ROOT / "reports" / "supplier_master_audit.md"
ADAPTERS_DIR = ROOT / "scrape" / "adapters"
CANONICAL_JSON = ROOT / "data" / "master" / "suppliers.canonical.json"
ADAPTER_MAP_CSV = ROOT / "data" / "master" / "adapter_supplier_map.csv"


ISSUE_CODES = {
    "duplicate_legacy_id",
    "duplicate_domain",
    "missing_website",
    "missing_location",
    "adapter_without_supplier",
    "supplier_without_adapter",
    "registered_placeholder_adapter",
    "name_domain_mismatch",
}

COMMON_NAME_WORDS = {
    "and",
    "botanical",
    "co",
    "company",
    "farm",
    "farms",
    "garden",
    "gardens",
    "greenhouse",
    "greenhouses",
    "grower",
    "growers",
    "inc",
    "llc",
    "nursery",
    "nurseries",
    "organic",
    "organics",
    "plant",
    "plants",
    "supply",
    "supplies",
    "the",
    "wholesale",
}


@dataclass(frozen=True)
class AdapterInfo:
    supplier_id: int
    supplier_name: str
    class_name: str
    module_path: str
    requires_login: bool
    prefer_tier: str
    placeholder: bool
    disabled: bool = False


def normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    candidate = str(value).strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"//{candidate}"
    parsed = urlparse(candidate)
    host = parsed.netloc or parsed.path.split("/", 1)[0]
    host = host.split("@")[-1].split(":", 1)[0].strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _name_tokens(value: str | None) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (value or "").lower())
    return {word for word in words if word not in COMMON_NAME_WORDS and len(word) > 1}


def _machine_issue(code: str, **fields: Any) -> dict[str, Any]:
    if code not in ISSUE_CODES:
        raise ValueError(f"unknown issue code: {code}")
    return {"code": code, **fields}


def _legacy_id(record: dict[str, Any]) -> int | None:
    value = record.get("id", record.get("legacy_id"))
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def audit_raw_suppliers(
    records: list[dict[str, Any]],
    adapters: list[dict[str, Any] | AdapterInfo] | None = None,
) -> list[dict[str, Any]]:
    adapters = adapters or []
    adapter_dicts = [
        asdict(adapter) if isinstance(adapter, AdapterInfo) else dict(adapter)
        for adapter in adapters
    ]
    issues: list[dict[str, Any]] = []

    records_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    records_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, record in enumerate(records, start=1):
        record_id = _legacy_id(record)
        if record_id is not None:
            records_by_id[record_id].append(record)

        domain = normalize_domain(record.get("web") or record.get("website"))
        if domain:
            records_by_domain[domain].append(record)
        else:
            issues.append(
                _machine_issue(
                    "missing_website",
                    legacy_id=record_id,
                    supplier_name=record.get("n") or record.get("supplier_name") or "",
                    raw_row=index,
                )
            )

        if not (record.get("city") or "").strip() or not (record.get("st") or "").strip():
            issues.append(
                _machine_issue(
                    "missing_location",
                    legacy_id=record_id,
                    supplier_name=record.get("n") or record.get("supplier_name") or "",
                    raw_row=index,
                )
            )

    for legacy_id, grouped in sorted(records_by_id.items()):
        if len(grouped) <= 1:
            continue
        issues.append(
            _machine_issue(
                "duplicate_legacy_id",
                legacy_id=legacy_id,
                record_count=len(grouped),
                supplier_names=sorted({record.get("n", "") for record in grouped}),
                domains=sorted({normalize_domain(record.get("web")) for record in grouped if record.get("web")}),
            )
        )

    for domain, grouped in sorted(records_by_domain.items()):
        distinct_names = sorted({record.get("n", "") for record in grouped})
        distinct_ids = sorted({_legacy_id(record) for record in grouped if _legacy_id(record) is not None})
        if len(grouped) > 1 and (len(distinct_names) > 1 or len(distinct_ids) > 1):
            issues.append(
                _machine_issue(
                    "duplicate_domain",
                    normalized_domain=domain,
                    record_count=len(grouped),
                    legacy_ids=distinct_ids,
                    supplier_names=distinct_names,
                )
            )

    record_ids = set(records_by_id)
    adapter_ids: set[int] = set()
    adapters_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for adapter in adapter_dicts:
        try:
            adapter_id = int(adapter.get("supplier_id"))
        except (TypeError, ValueError):
            continue
        adapter_ids.add(adapter_id)
        adapters_by_id[adapter_id].append(adapter)
        if adapter_id not in record_ids:
            issues.append(
                _machine_issue(
                    "adapter_without_supplier",
                    legacy_id=adapter_id,
                    adapter_class=adapter.get("class_name", ""),
                    adapter_supplier_name=adapter.get("supplier_name", ""),
                )
            )
        if adapter.get("placeholder"):
            issues.append(
                _machine_issue(
                    "registered_placeholder_adapter",
                    legacy_id=adapter_id,
                    adapter_class=adapter.get("class_name", ""),
                    adapter_supplier_name=adapter.get("supplier_name", ""),
                )
            )

    for legacy_id, grouped in sorted(records_by_id.items()):
        if legacy_id not in adapter_ids:
            issues.append(
                _machine_issue(
                    "supplier_without_adapter",
                    legacy_id=legacy_id,
                    supplier_names=sorted({record.get("n", "") for record in grouped}),
                )
            )

    for legacy_id, grouped_adapters in sorted(adapters_by_id.items()):
        grouped_records = records_by_id.get(legacy_id, [])
        if not grouped_records:
            continue
        raw_tokens = set().union(*(_name_tokens(record.get("n")) for record in grouped_records))
        for adapter in grouped_adapters:
            adapter_tokens = _name_tokens(adapter.get("supplier_name"))
            if adapter_tokens and raw_tokens and not (adapter_tokens & raw_tokens):
                issues.append(
                    _machine_issue(
                        "name_domain_mismatch",
                        legacy_id=legacy_id,
                        adapter_class=adapter.get("class_name", ""),
                        adapter_supplier_name=adapter.get("supplier_name", ""),
                        supplier_names=sorted({record.get("n", "") for record in grouped_records}),
                    )
                )

    return issues


def _literal_value(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (TypeError, ValueError, SyntaxError):
        return None


def _module_path(path: Path) -> str:
    relative = path.relative_to(ROOT).with_suffix("")
    return ".".join(relative.parts)


def _decorated_with_register(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "register":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "register":
            return True
    return False


def _class_source(source_lines: list[str], node: ast.ClassDef) -> str:
    start = max(node.lineno - 8, 0)
    end = getattr(node, "end_lineno", node.lineno)
    return "\n".join(source_lines[start:end])


def _class_assignments(node: ast.ClassDef) -> dict[str, Any]:
    assignments: dict[str, Any] = {}
    for child in node.body:
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = _literal_value(child.value)
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            assignments[child.target.id] = _literal_value(child.value)
    return assignments


def _is_placeholder(class_source: str, assignments: dict[str, Any]) -> bool:
    lowered = class_source.lower()
    if "placeholder" in lowered or "disabled" in lowered:
        return True
    for key in ("pdf_urls", "urls", "start_urls"):
        if key in assignments and assignments[key] == []:
            return True
    return False


def _collect_simple_adapter_calls(tree: ast.Module, path: Path) -> list[AdapterInfo]:
    adapters: list[AdapterInfo] = []
    module_path = _module_path(path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id not in {"_simple", "_crawling"}:
            continue
        if len(node.args) < 2:
            continue
        supplier_id = _literal_value(node.args[0])
        supplier_name = _literal_value(node.args[1])
        if not isinstance(supplier_id, int) or not isinstance(supplier_name, str):
            continue
        keywords = {keyword.arg: _literal_value(keyword.value) for keyword in node.keywords}
        adapters.append(
            AdapterInfo(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                class_name=f"Adapter_{supplier_id}",
                module_path=module_path,
                requires_login=bool(keywords.get("login", False)),
                prefer_tier=str(keywords.get("tier") or ""),
                placeholder=False,
            )
        )
    return adapters


def collect_registered_adapters(adapters_dir: Path = ADAPTERS_DIR) -> list[AdapterInfo]:
    adapters: list[AdapterInfo] = []
    for path in sorted(Path(adapters_dir).glob("*.py")):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))
        module_path = _module_path(path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not _decorated_with_register(node):
                continue
            assignments = _class_assignments(node)
            supplier_id = assignments.get("supplier_id")
            supplier_name = assignments.get("supplier_name", "")
            if not isinstance(supplier_id, int):
                continue
            if not isinstance(supplier_name, str):
                supplier_name = ""
            adapters.append(
                AdapterInfo(
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    class_name=node.name,
                    module_path=module_path,
                    requires_login=bool(assignments.get("requires_login", False)),
                    prefer_tier=str(assignments.get("prefer_tier") or ""),
                    placeholder=_is_placeholder(_class_source(source_lines, node), assignments),
                )
            )

        adapters.extend(_collect_simple_adapter_calls(tree, path))

    return sorted(adapters, key=lambda adapter: (adapter.supplier_id, adapter.module_path, adapter.class_name))


def load_raw_records(path: Path = RAW_JSON) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _issue_sort_key(issue: dict[str, Any]) -> tuple[str, int, str]:
    legacy_id = issue.get("legacy_id")
    try:
        legacy_sort = int(legacy_id)
    except (TypeError, ValueError):
        legacy_sort = 0
    return (str(issue.get("code", "")), legacy_sort, json.dumps(issue, sort_keys=True))


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = [str(value).replace("\n", " ").replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_audit_report(
    records: list[dict[str, Any]],
    adapters: list[AdapterInfo],
    issues: list[dict[str, Any]],
) -> str:
    counts = Counter(issue["code"] for issue in issues)
    id_counts = Counter(_legacy_id(record) for record in records)
    duplicate_ids = sorted((legacy_id, count) for legacy_id, count in id_counts.items() if count > 1)

    lines: list[str] = [
        "# Supplier Master Audit",
        "",
        "This report is generated from the raw `index.html` supplier import and registered adapter source code. It is not evidence that any supplier is real or verified.",
        "",
        "## Raw Import Summary",
        "",
        f"- Raw supplier records: {len(records)}",
        f"- Unique legacy IDs: {len(id_counts)}",
        f"- Duplicate legacy ID rows: {sum(count - 1 for _, count in duplicate_ids)}",
        f"- Registered adapters: {len(adapters)}",
        "",
        "## Issue Counts",
        "",
    ]
    lines.extend(_markdown_table(["Issue code", "Count"], [[code, counts.get(code, 0)] for code in sorted(ISSUE_CODES)]))
    lines.extend(["", "## Duplicate Legacy IDs", ""])
    if duplicate_ids:
        rows = []
        for legacy_id, count in duplicate_ids:
            grouped = [record for record in records if _legacy_id(record) == legacy_id]
            rows.append(
                [
                    legacy_id,
                    count,
                    "; ".join(record.get("n", "") for record in grouped),
                    "; ".join(record.get("web", "") for record in grouped),
                ]
            )
        lines.extend(_markdown_table(["Legacy ID", "Rows", "Raw names", "Raw websites"], rows))
    else:
        lines.append("No duplicate legacy IDs found.")

    mismatch_codes = {
        "adapter_without_supplier",
        "supplier_without_adapter",
        "registered_placeholder_adapter",
        "name_domain_mismatch",
    }
    lines.extend(["", "## Adapter/Dashboard Mismatches", ""])
    mismatch_rows = [
        [
            issue.get("code", ""),
            issue.get("legacy_id", ""),
            issue.get("adapter_class", ""),
            issue.get("adapter_supplier_name", ""),
            "; ".join(issue.get("supplier_names", [])) if isinstance(issue.get("supplier_names"), list) else issue.get("supplier_names", ""),
        ]
        for issue in sorted(issues, key=_issue_sort_key)
        if issue.get("code") in mismatch_codes
    ]
    if mismatch_rows:
        lines.extend(
            _markdown_table(
                ["Code", "Legacy ID", "Adapter class", "Adapter name", "Dashboard name(s)"],
                mismatch_rows,
            )
        )
    else:
        lines.append("No adapter/dashboard mismatches found.")

    lines.extend(["", "## All Machine-Readable Issues", ""])
    for issue in sorted(issues, key=_issue_sort_key):
        lines.append(f"- `{issue['code']}` `{json.dumps(issue, sort_keys=True, ensure_ascii=False)}`")

    lines.append("")
    return "\n".join(lines)


def write_audit_report(
    records: list[dict[str, Any]],
    adapters: list[AdapterInfo],
    issues: list[dict[str, Any]],
    path: Path = REPORT_MD,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_audit_report(records, adapters, issues), encoding="utf-8")


def validate_canonical_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    ids = Counter(record.get("canonical_supplier_id") for record in records)
    for canonical_id, count in ids.items():
        if canonical_id and count > 1:
            issues.append({"code": "duplicate_canonical_id", "canonical_supplier_id": canonical_id, "count": count})

    accepted_domains: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.get("verification_status") != "verified":
            continue
        domain = normalize_domain(record.get("website"))
        if domain:
            accepted_domains[domain].append(record.get("canonical_supplier_id", ""))
        if not record.get("evidence_urls"):
            issues.append(
                {
                    "code": "verified_supplier_missing_evidence",
                    "canonical_supplier_id": record.get("canonical_supplier_id", ""),
                    "supplier_name": record.get("supplier_name", ""),
                }
            )
    for domain, canonical_ids in accepted_domains.items():
        if len(set(canonical_ids)) > 1:
            issues.append(
                {
                    "code": "duplicate_verified_domain",
                    "normalized_domain": domain,
                    "canonical_supplier_ids": sorted(set(canonical_ids)),
                }
            )
    return issues


def print_canonical_audit(path: Path) -> int:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    issues = validate_canonical_records(records)
    print(f"canonical_record_count={len(records)}")
    print(f"canonical_issue_count={len(issues)}")
    for issue in issues:
        print(json.dumps(issue, sort_keys=True))
    return 1 if issues else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit supplier registry identity conflicts.")
    parser.add_argument("--raw", type=Path, default=RAW_JSON)
    parser.add_argument("--report", type=Path, default=REPORT_MD)
    parser.add_argument("--canonical", type=Path)
    args = parser.parse_args()

    if args.canonical:
        return print_canonical_audit(args.canonical)

    records = load_raw_records(args.raw)
    adapters = collect_registered_adapters()
    issues = audit_raw_suppliers(records, adapters)
    write_audit_report(records, adapters, issues, args.report)

    counts = Counter(issue["code"] for issue in issues)
    print(f"raw_record_count={len(records)}")
    print(f"registered_adapter_count={len(adapters)}")
    print(f"issue_count={len(issues)}")
    for code in sorted(ISSUE_CODES):
        print(f"{code}={counts.get(code, 0)}")
    print(f"report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
