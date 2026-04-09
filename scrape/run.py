#!/usr/bin/env python3
"""
BloomBox scraper runner.

Usage:
    python -m scrape.run                 # run all registered adapters
    python -m scrape.run --id 207 178    # run specific suppliers
    python -m scrape.run --public        # only public-access suppliers
    python -m scrape.run --logged-in     # only suppliers with vault creds
    python -m scrape.run --dry-run       # resolve + print targets, no fetch

Outputs:
    scrape/output/prices.json             latest prices (all suppliers merged)
    scrape/output/history/<YYYYMMDD>.json archived snapshots
    scrape/output/run_summary.json        metadata for the dashboard badge
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so `scrape` is importable when run as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrape.core.adapter import Adapter, all_adapters, get_adapter, load_registered_adapters
from scrape.core.vault import load_vault

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
HISTORY_DIR = OUTPUT_DIR / "history"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    try:
        from rich.logging import RichHandler  # type: ignore
        logging.basicConfig(level=level, format="%(message)s",
                            datefmt="[%X]", handlers=[RichHandler(show_path=False)])
    except Exception:
        logging.basicConfig(level=level,
                            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def run_one(adapter_cls: type[Adapter], creds: dict) -> dict:
    sid = adapter_cls.supplier_id
    cred = creds.get(sid)
    try:
        adapter = adapter_cls(credential=cred)
        result = adapter.run()
        return result.as_dict()
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
    creds = load_vault()
    if args.logged_in:
        adapters = [a for a in adapters
                    if a.requires_login and a.supplier_id in creds]

    if not adapters:
        log.error("no adapters match filters")
        return 1

    log.info("running %d adapter(s)", len(adapters))
    for a in adapters:
        kind = "login" if a.requires_login else "public"
        has_cred = "\u2713" if a.supplier_id in creds else "\u2717"
        log.info("  #%d %-30s [%s] cred=%s", a.supplier_id,
                 a.supplier_name, kind, has_cred)

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
    prices_path = OUTPUT_DIR / "prices.json"
    prices_path.write_text(json.dumps(payload, indent=2))

    # Also emit a JS version the dashboard can load via <script> (file://
    # friendly; avoids fetch/CORS issues when the dashboard is opened
    # locally). The dashboard looks for window.LIVE_PRICES on load.
    js_payload = "window.LIVE_PRICES = " + json.dumps(payload) + ";\n"
    (OUTPUT_DIR / "prices.js").write_text(js_payload)
    # Drop a copy next to index.html so a plain <script src="prices.js">
    # works with no path gymnastics.
    try:
        (ROOT / "prices.js").write_text(js_payload)
    except Exception:
        pass

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
    }
    for r in results:
        t = r["tier_used"] or "none"
        summary["tier_breakdown"][t] = summary["tier_breakdown"].get(t, 0) + 1
    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2))

    log.info("\nwrote %s (%d products, %d suppliers)",
             prices_path, len(all_products),
             summary["suppliers_with_products"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
