# Adapter Quality Audit

Status as of May 8, 2026.

This audit is now tied to the canonical supplier registry in
`data/master/suppliers.canonical.json` and the machine-readable adapter map in
`data/master/adapter_supplier_map.csv`. The raw dashboard supplier array is not
canonical evidence.

## Current Totals

- Registered adapters: 17
- Adapters mapped to verified canonical suppliers: 15
- Adapters quarantined pending supplier review: 2
- `active_verified`: 7
- `active_unverified`: 4
- `placeholder_registered`: 6

## Production Bar

An adapter should not be treated as production-grade until it has all of:

- a verified canonical supplier ID
- real current source URLs, not commented placeholders
- all required runtime dependencies available in `python3 -m scrape.run --preflight`
- a recent live run that returns meaningful rows or a deliberate non-product result
- rows normalized with `supplier_id` and `supplier_name`
- no unresolved mismatch between adapter supplier ID and canonical supplier

## Active Verified

| Adapter ID | Canonical ID | Supplier | Evidence | Current classification |
| --- | --- | --- | --- | --- |
| 21 | BB-SUP-000002 | Ernst Conservation Seeds | `python3 -m scrape.run --id 21 389 201 312 381 43 244 --concurrency 1` on May 8, 2026 extracted 427 rows from the official 2026 Retail Price List PDF. | Keep enabled. PDF price-list parser returned normalized rows with `supplier_id` and `supplier_name`. |
| 43 | BB-SUP-000014 | American Native Plants | `python3 -m scrape.run --id 43 --concurrency 1` on May 8, 2026 extracted 522 rows from the official May 6, 2026 XLSX availability workbook. | Keep enabled, availability-only feed, no prices. Runtime credential and manual Playwright session are present locally; checked logged-in account/download/catalog pages did not expose account-gated prices. |
| 201 | BB-SUP-000007 | Nolt's Greenhouse Supplies | `python3 -m scrape.run --id 21 389 201 312 381 43 244 --concurrency 1` on May 8, 2026 extracted 995 rows from official `NGScatalog.pdf`. | Keep enabled. Legacy ID is duplicated in raw data; mapping is by verified Nolt name/domain. |
| 244 | BB-SUP-000010 | Blue Sky Nursery | `python3 -m scrape.run --id 21 389 201 312 381 43 244 --concurrency 1` on May 8, 2026 extracted 2387 XLSX availability rows. | Keep enabled, availability-only feed, no prices. |
| 312 | BB-SUP-000011 | The Cactus King | `python3 -m scrape.run --id 21 389 201 312 381 43 244 --concurrency 1` on May 8, 2026 extracted 247 rows from the verified `thecactusking.com` public catalog. | Keep enabled. Canonical domain differs from the rejected raw dashboard domain. |
| 381 | BB-SUP-000013 | American Meadows | `python3 -m scrape.run --id 21 389 201 312 381 43 244 --concurrency 1` on May 8, 2026 extracted 2877 rows from the public Shopify JSON catalog. | Keep enabled. City remains blank in canonical data because checked official evidence did not publish one. |
| 389 | BB-SUP-000002 | Ernst Conservation Seeds | `python3 -m scrape.run --id 21 389 201 312 381 43 244 --concurrency 1` on May 8, 2026 extracted 266 rows from the official shrub/tree material price sheet. | Keep enabled. Maps to the same canonical Ernst supplier as ID 21. |

Latest combined verified-adapter run: `python3 -m scrape.run --id 21 389 201
312 381 43 244 --concurrency 1` published 7721 rows from 7 suppliers with 0
adapter errors at `2026-05-08T18:06:04+00:00`.

## Active But Needs Fresh Live Verification

These adapters map to verified canonical suppliers but should not be called
production-grade until the listed blocker is resolved and a fresh live run is
captured on this machine.

| Adapter ID | Canonical ID | Supplier | Adapter | Notes |
| --- | --- | --- | --- | --- |
| 16 | BB-SUP-000001 | Quality Greenhouses & Perennial Farm | `QualityGreenhousesAdapter` | Requires Playwright. |
| 207 | BB-SUP-000008 | SiteOne Landscape Supply | `SiteOneAdapter` | Requires undetected browser dependencies. Raw ID also appears on Eppley Nursery. |
| 210 | BB-SUP-000009 | ARBICO Organics | `ARBICOAdapter` | May 8, 2026 smoke run produced only 1 priced row after mixed 403/browser escalation; crawl needs tuning before promotion. Raw ID also appears on Adams County Greenhouse & Nursery. |
| 379 | BB-SUP-000012 | Prairie Moon Nursery | `PrairieMoonAdapter` | May 8, 2026 smoke run returned 404 for configured start URLs; refresh URLs before promotion. |

## Registered Placeholders Or Scaffolds

These adapters are registered in code, but should not be promoted without
additional verification or credentials.

| Adapter ID | Canonical ID | Supplier | Adapter | Reason |
| --- | --- | --- | --- | --- |
| 110 | BB-SUP-000003 | Walters Gardens | `WaltersAdapter` | Login scaffold with guessed selectors; needs approved credentials and DOM verification. |
| 111 | BB-SUP-000004 | Hoffman Nursery | `HoffmannNurseryAdapter` | Empty `pdf_urls`; official site has availability downloads, but direct adapter URLs are not verified. |
| 121 | BB-SUP-000005 | Mountain Spring Nursery | `MountainSpringNurseryAdapter` | Empty `pdf_urls`; official catalog/availability page is password-gated. |
| 129 |  | Schroeder Gardens | `SchroederAdapter` | Quarantined. Adapter comments say disabled/password-protected, while current public source evidence needs a separate supplier review. |
| 130 | BB-SUP-000006 | Go Native Trees | `GoNativeTreesAdapter` | Empty `pdf_urls`; official price-list page is verified, but direct adapter download URL still needs implementation. |
| 367 |  | Growella | `GrowellaAdapter` | Quarantined. Official source evidence points to Growell/growellshop.com while raw and adapter identity use Growella. |

## Quarantined Adapter IDs

| Adapter ID | Adapter | Quarantine reason |
| --- | --- | --- |
| 129 | `SchroederAdapter` | Canonical supplier left in review because adapter source comments say disabled/password-protected and current source evidence conflicts with adapter assumptions. |
| 367 | `GrowellaAdapter` | Official site evidence points to Growell/growellshop.com while raw and adapter use Growella; location and procurement model need review before canonical acceptance. |

## Raw Dashboard ID Risks Still Open

- `data/raw/current_dashboard_suppliers.json` contains 127 raw rows and 114 unique legacy IDs.
- Duplicate legacy IDs remain raw-import conflicts, not canonical supplier facts.
- The current canonical tranche accepts 14 verified suppliers, sends 111 raw rows to review, and rejects 1 duplicate raw row.
- Every registered adapter is either mapped to one canonical supplier or quarantined in `data/master/adapter_supplier_map.csv`.

## Next Adapter Cleanup Steps

1. Run `python3 -m scrape.run --preflight --id ...` for mapped adapters and separate missing browser dependencies from adapter defects.
2. Disable or finish registered placeholders before exposing them in production views.
3. Resolve quarantined IDs `129` and `367` with supplier-level review before changing scraper behavior.
4. Keep future adapter status changes in `data/master/adapter_supplier_map.csv` first, then update this audit.
