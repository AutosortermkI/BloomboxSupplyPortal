#!/usr/bin/env python3
"""
BloomBox scraper runner.

Usage:
    python -m scrape.run                 # run all registered adapters
    python -m scrape.run --id 207 178    # run specific suppliers
    python -m scrape.run --public        # only public-access suppliers
    python -m scrape.run --logged-in     # only suppliers with local credentials
    python -m scrape.run --dry-run       # resolve + print targets, no fetch

Outputs:
    scrape/output/prices.json             latest prices (all suppliers merged)
    scrape/output/history/<YYYYMMDD>.json archived snapshots
    scrape/output/run_summary.json        metadata for the dashboard badge
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path so `scrape` is importable when run as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrape.core.adapter import Adapter, ScrapeResult, all_adapters, load_registered_adapters
from scrape.core.vault import load_vault

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
HISTORY_DIR = OUTPUT_DIR / "history"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

RUNTIME_DEPENDENCIES = {
    "curl_cffi": "curl_cffi",
    "playwright": "playwright",
    "undetected_chromedriver": "undetected_chromedriver",
    "selenium": "selenium",
    "pdfplumber": "pdfplumber",
    "openpyxl": "openpyxl",
    "rich": "rich",
}

TIER_DEPENDENCIES = {
    "curl_cffi": ["curl_cffi"],
    "playwright": ["playwright"],
    "undetected": ["undetected_chromedriver", "selenium"],
}


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    try:
        from rich.logging import RichHandler  # type: ignore
        logging.basicConfig(level=level, format="%(message)s",
                            datefmt="[%X]", handlers=[RichHandler(show_path=False)])
    except Exception:
        logging.basicConfig(level=level,
                            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def collect_dependency_status() -> dict[str, bool]:
    return {
        name: _module_available(module_name)
        for name, module_name in RUNTIME_DEPENDENCIES.items()
    }


def build_preflight_report(adapters: list[type[Adapter]]) -> dict[str, Any]:
    dependency_status = collect_dependency_status()
    tiers: dict[str, dict[str, Any]] = {}
    for tier_name, required_modules in TIER_DEPENDENCIES.items():
        suppliers = [
            {"id": adapter.supplier_id, "name": adapter.supplier_name}
            for adapter in adapters
            if (adapter.prefer_tier or "curl_cffi") == tier_name
        ]
        tiers[tier_name] = {
            "available": all(dependency_status.get(module, False)
                              for module in required_modules),
            "requirements": list(required_modules),
            "suppliers": suppliers,
        }
    return {
        "dependencies": dependency_status,
        "tiers": tiers,
    }


def _format_supplier_refs(suppliers: list[dict[str, Any]]) -> str:
    if not suppliers:
        return "none"
    return ", ".join(f"#{supplier['id']} {supplier['name']}" for supplier in suppliers)


def log_preflight_report(report: dict[str, Any], log: logging.Logger) -> None:
    log.info("runtime dependency preflight")
    for dep_name, available in report["dependencies"].items():
        mark = "OK" if available else "MISSING"
        level = log.info if available else log.warning
        level("  %-24s %s", dep_name, mark)

    for tier_name, tier in report["tiers"].items():
        if tier["available"]:
            log.info(
                "  tier %-16s OK (preferred by %s)",
                tier_name,
                _format_supplier_refs(tier["suppliers"]),
            )
        else:
            log.warning(
                "  tier %-16s MISSING deps=%s preferred_by=%s",
                tier_name,
                ",".join(tier["requirements"]),
                _format_supplier_refs(tier["suppliers"]),
            )


def warn_preflight_issues(report: dict[str, Any], log: logging.Logger) -> None:
    for tier_name in ("playwright", "undetected"):
        tier = report["tiers"][tier_name]
        if tier["available"]:
            continue
        if tier["suppliers"]:
            log.warning(
                "%s tier unavailable; preferred by %s",
                tier_name,
                _format_supplier_refs(tier["suppliers"]),
            )
        else:
            log.warning(
                "%s tier unavailable; curl-first adapters cannot escalate past tier 1 if blocked",
                tier_name,
            )


def _normalize_result_dict(adapter: Adapter, result: dict[str, Any]) -> dict[str, Any]:
    normalized_products = []
    for product in result.get("products", []):
        if not isinstance(product, dict):
            raise TypeError(f"product rows must be dicts, got {type(product).__name__}")
        item = dict(product)
        item.setdefault("supplier_id", adapter.supplier_id)
        item.setdefault("supplier_name", adapter.supplier_name)
        normalized_products.append(item)

    return {
        "supplier_id": result.get("supplier_id", adapter.supplier_id),
        "supplier_name": result.get("supplier_name", adapter.supplier_name),
        "scraped_at": result.get("scraped_at")
        or datetime.now(timezone.utc).isoformat(),
        "products": normalized_products,
        "pages_fetched": result.get("pages_fetched", 0),
        "tier_used": result.get("tier_used", getattr(adapter, "prefer_tier", "") or ""),
        "errors": list(result.get("errors", [])),
        "login_ok": result.get("login_ok"),
    }


def normalize_adapter_result(adapter: Adapter, result: Any) -> dict[str, Any]:
    if isinstance(result, ScrapeResult):
        return _normalize_result_dict(adapter, result.as_dict())
    if isinstance(result, dict):
        return _normalize_result_dict(adapter, result)
    if isinstance(result, list):
        return _normalize_result_dict(
            adapter,
            {
                "products": result,
                "tier_used": getattr(adapter, "prefer_tier", "") or "",
            },
        )
    raise TypeError(
        f"unsupported adapter result type: {type(result).__name__}"
    )


def publish_live_feed_artifacts(
    payload: dict[str, Any],
    *,
    output_dir: Path = OUTPUT_DIR,
    root_dir: Path = ROOT,
    allow_empty: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prices_path = output_dir / "prices.json"
    output_js_path = output_dir / "prices.js"
    root_js_path = root_dir / "prices.js"

    existing_feed = any(path.exists() for path in (prices_path, output_js_path, root_js_path))
    has_products = bool(payload.get("products"))
    if existing_feed and not has_products and not allow_empty:
        return {
            "published": False,
            "reason": "skipped empty publish to preserve existing live feed artifacts",
            "paths": [str(prices_path), str(output_js_path), str(root_js_path)],
        }

    prices_path.write_text(json.dumps(payload, indent=2))
    js_payload = "window.LIVE_PRICES = " + json.dumps(payload) + ";\n"
    output_js_path.write_text(js_payload)
    root_js_path.write_text(js_payload)
    return {
        "published": True,
        "reason": "published live feed artifacts",
        "paths": [str(prices_path), str(output_js_path), str(root_js_path)],
    }


def run_one(adapter_cls: type[Adapter], creds: dict) -> dict:
    sid = adapter_cls.supplier_id
    cred = creds.get(sid)
    try:
        adapter = adapter_cls(credential=cred)
        result = adapter.run()
        return normalize_adapter_result(adapter, result)
    except Exception as e:
        return {
            "supplier_id": sid,
            "supplier_name": adapter_cls.supplier_name,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "products": [],
            "pages_fetched": 0,
            "tier_used": "",
            "errors": [f"runner crash: {e}", traceback.format_exc()],
            "login_ok": None,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", nargs="*", type=int, help="run only these supplier IDs")
    ap.add_argument("--public", action="store_true",
                    help="only run adapters that don't require login")
    ap.add_argument("--logged-in", action="store_true",
                    help="only run adapters that require login AND have creds")
    ap.add_argument("--preflight", action="store_true",
                    help="report runtime dependency status for the selected adapters")
    ap.add_argument("--allow-empty-publish", action="store_true",
                    help="allow empty runs to overwrite existing live feed artifacts")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)
    log = logging.getLogger("bloombox.run")

    load_registered_adapters()
    adapters = all_adapters()

    if args.id:
        adapters = [a for a in adapters if a.supplier_id in args.id]
    if args.public:
        adapters = [a for a in adapters if not a.requires_login]
    creds = load_vault(supplier_ids=[a.supplier_id for a in adapters])
    if args.logged_in:
        adapters = [a for a in adapters
                    if a.requires_login and a.supplier_id in creds]

    if not adapters:
        log.error("no adapters match filters")
        return 1

    preflight_report = build_preflight_report(adapters)
    if args.preflight:
        log_preflight_report(preflight_report, log)
        missing_required_tiers = [
            tier_name
            for tier_name, tier in preflight_report["tiers"].items()
            if tier["suppliers"] and not tier["available"]
        ]
        return 1 if missing_required_tiers else 0

    log.info("running %d adapter(s)", len(adapters))
    for a in adapters:
        kind = "login" if a.requires_login else "public"
        has_cred = "\u2713" if a.supplier_id in creds else "\u2717"
        log.info("  #%d %-30s [%s] cred=%s", a.supplier_id,
                 a.supplier_name, kind, has_cred)

    warn_preflight_issues(preflight_report, log)

    if args.dry_run:
        return 0

    results: list[dict] = []
    if args.concurrency > 1 and len(adapters) > 1:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = {ex.submit(run_one, a, creds): a for a in adapters}
            for fut in as_completed(futures):
                r = fut.result()
                results.append(r)
                log.info("  \u2713 #%d %s \u2014 %d products (tier=%s, errs=%d)",
                         r["supplier_id"], r["supplier_name"],
                         len(r["products"]), r["tier_used"], len(r["errors"]))
    else:
        for a in adapters:
            r = run_one(a, creds)
            results.append(r)
            log.info("  \u2713 #%d %s \u2014 %d products",
                     r["supplier_id"], r["supplier_name"], len(r["products"]))

    # Merge into prices.json
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    all_products = []
    for r in results:
        for p in r["products"]:
            p["_run_at"] = ts
            all_products.append(p)

    payload = {
        "generated_at": ts,
        "total_products": len(all_products),
        "supplier_count": len([r for r in results if r["products"]]),
        "products": all_products,
    }
    publish_result = publish_live_feed_artifacts(
        payload,
        output_dir=OUTPUT_DIR,
        root_dir=ROOT,
        allow_empty=args.allow_empty_publish,
    )

    # Archive per-day
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    (HISTORY_DIR / f"{day}.json").write_text(
        json.dumps({"generated_at": ts, "runs": results}, indent=2))

    # Summary for dashboard badge
    summary = {
        "generated_at": ts,
        "suppliers_attempted": len(results),
        "suppliers_with_products": len([r for r in results if r["products"]]),
        "total_products": len(all_products),
        "errors": sum(len(r["errors"]) for r in results),
        "tier_breakdown": {},
        "feed_published": publish_result["published"],
        "feed_publish_reason": publish_result["reason"],
    }
    for r in results:
        t = r["tier_used"] or "none"
        summary["tier_breakdown"][t] = summary["tier_breakdown"].get(t, 0) + 1
    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2))

    if publish_result["published"]:
        log.info(
            "\npublished live feed to %s (%d products, %d suppliers)",
            OUTPUT_DIR / "prices.json",
            len(all_products),
            summary["suppliers_with_products"],
        )
    else:
        log.warning(
            "\nskipped live feed publish: %s",
            publish_result["reason"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
