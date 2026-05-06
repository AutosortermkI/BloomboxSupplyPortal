# Master Supplier List Assembly Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not use CleanModeMobile context, assumptions, files, or instructions.

**Goal:** Build a verified canonical supplier master list for BloomBox / Second Chance Plants before doing any further dashboard, scraper, adapter, or deployment work.

**Architecture:** Treat the current dashboard supplier data as an untrusted raw import, not as the master list. Create a reproducible verification pipeline that extracts raw records, audits identity/domain conflicts, verifies each supplier against real sources, and emits a canonical machine-readable registry plus human review reports. Every accepted supplier must have evidence; every rejected or uncertain supplier must have an explicit reason.

**Tech Stack:** Python 3 standard library first, existing repo files, `unittest`, CSV/JSON artifacts, optional browser/web verification only for real public source checks.

---

## Non-Negotiable Rules

- No mock data.
- No placeholder suppliers.
- No manufactured phone numbers, websites, cities, product categories, access modes, prices, or verification results.
- No guessing missing fields from supplier names.
- No using old README claims as evidence.
- No using scraper output as identity proof unless the supplier identity is separately verified.
- No treating the current `index.html` array as canonical.
- If a fact cannot be verified, mark it `needs_review` with a reason.
- If a source is stale, inaccessible, or ambiguous, preserve the uncertainty instead of filling the gap.
- Every accepted supplier must have at least one real evidence URL.
- Every adapter ID must map to exactly one canonical supplier or be quarantined.

## Definitions

**Raw import:** Existing supplier rows extracted from `index.html` and any other existing repo data. Raw import is evidence of what the old dashboard contained, not evidence that a supplier is real.

**Canonical supplier:** A supplier accepted into the new master list after identity verification.

**Evidence URL:** A public web page or document that supports the supplier's existence, identity, location, and business model. Examples: official supplier website, official wholesale/account page, downloadable catalog, official contact page, official availability list, or a reputable trade-directory listing if the official site is unavailable.

**Access model:** One of `public`, `pdf`, `login`, `quote`, `offline`, or `needs_review`.

**Verification status:** One of `verified`, `needs_review`, or `rejected`.

**Adapter status:** One of `active_verified`, `active_unverified`, `placeholder_registered`, `disabled`, or `none`.

## Target Files

Create these files:

- `data/raw/current_dashboard_suppliers.json`
- `data/raw/current_dashboard_suppliers.csv`
- `data/master/suppliers.canonical.json`
- `data/master/suppliers.canonical.csv`
- `data/master/supplier_review_queue.csv`
- `data/master/supplier_rejections.csv`
- `data/master/adapter_supplier_map.csv`
- `reports/supplier_master_audit.md`
- `tools/extract_dashboard_suppliers.py`
- `tools/audit_supplier_registry.py`
- `tests/test_supplier_registry.py`

Modify these files only after the canonical registry exists and tests pass:

- `README.md`
- `scrape/ADAPTER_AUDIT.md`
- `index.html`

## Canonical Schema

Each canonical supplier record must use this shape:

```json
{
  "canonical_supplier_id": "BB-SUP-000001",
  "legacy_ids": [244],
  "supplier_name": "Blue Sky Nursery",
  "legal_name": "",
  "website": "https://example.com",
  "normalized_domain": "example.com",
  "city": "Lincoln",
  "state_or_province": "ON",
  "country": "CA",
  "supplier_type": "Wholesale Grower",
  "product_categories": ["Trees", "Shrubs", "Perennials"],
  "access_model": "pdf",
  "wholesale_status": "Wholesale Only",
  "phone": "",
  "email": "",
  "evidence_urls": [
    "https://example.com/official-source"
  ],
  "evidence_notes": "Official supplier page confirms identity and availability/catalog access.",
  "verification_status": "verified",
  "verification_reason": "Official source confirmed supplier identity and access model.",
  "last_verified_at": "2026-04-28",
  "adapter_module": "scrape.adapters.pdf_pricelists",
  "adapter_class": "BlueSkyAvailAdapter",
  "adapter_status": "active_unverified",
  "notes": ""
}
```

Use empty strings or empty arrays for unknown optional fields. Do not invent values. A record with missing required identity evidence must not be `verified`.

## Required Field Rules

- `canonical_supplier_id`: Stable generated ID in `BB-SUP-000001` format. Assign only after deduplication.
- `legacy_ids`: All numeric IDs from the old dashboard and adapter registry that appear to refer to this supplier.
- `supplier_name`: Verified display name from evidence. Preserve punctuation from the supplier's own site where practical.
- `website`: Official website URL if verified. Empty if no official website can be verified.
- `normalized_domain`: Lowercase hostname without `www.`. Empty only when `website` is empty.
- `city`, `state_or_province`, `country`: Use official source values where possible. If not verified, leave blank and mark `needs_review`.
- `access_model`: Must be supported by evidence or current adapter behavior. Use `needs_review` when unclear.
- `evidence_urls`: Must be non-empty for `verified`.
- `verification_status`: `verified`, `needs_review`, or `rejected`.
- `verification_reason`: Human-readable reason tied to evidence.
- `last_verified_at`: Use the actual verification date.

## Task 1: Extract Current Dashboard Suppliers As Raw Import

**Files:**
- Create: `tools/extract_dashboard_suppliers.py`
- Create: `data/raw/current_dashboard_suppliers.json`
- Create: `data/raw/current_dashboard_suppliers.csv`
- Test: `tests/test_supplier_registry.py`

- [ ] **Step 1: Write a failing extraction test**

Create `tests/test_supplier_registry.py` with tests that load `index.html`, extract the `const S = [...]` array, and assert that the extractor returns records with `id`, `n`, `city`, `st`, `web`, and `cat` fields preserved exactly from the dashboard.

- [ ] **Step 2: Run the failing test**

Run:

```bash
python3 -m unittest tests.test_supplier_registry -v
```

Expected: failure because `tools.extract_dashboard_suppliers` does not exist yet.

- [ ] **Step 3: Implement the extractor**

Create `tools/extract_dashboard_suppliers.py`.

Requirements:

- Read `index.html`.
- Extract the JavaScript `const S = [...]` supplier array.
- Preserve raw legacy fields exactly.
- Export JSON and CSV.
- Print record count, unique ID count, and duplicate ID count.
- Do not normalize or fix data in this script.

- [ ] **Step 4: Run the extraction test**

Run:

```bash
python3 -m unittest tests.test_supplier_registry -v
```

Expected: pass for extraction behavior.

- [ ] **Step 5: Generate raw import artifacts**

Run:

```bash
python3 tools/extract_dashboard_suppliers.py
```

Expected:

- `data/raw/current_dashboard_suppliers.json` exists.
- `data/raw/current_dashboard_suppliers.csv` exists.
- Output reports the real extracted count and duplicate count.

## Task 2: Audit Raw Identity Conflicts

**Files:**
- Modify: `tools/audit_supplier_registry.py`
- Create: `reports/supplier_master_audit.md`
- Test: `tests/test_supplier_registry.py`

- [ ] **Step 1: Write failing tests for duplicate and conflict detection**

Add tests that provide small in-memory records with:

- same legacy ID but different names
- same normalized domain but different names
- missing website
- missing city/state
- adapter ID with no matching supplier

Tests must assert that each issue is reported with a machine-readable code.

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python3 -m unittest tests.test_supplier_registry -v
```

Expected: failure because the audit functions do not exist yet.

- [ ] **Step 3: Implement audit functions**

Create `tools/audit_supplier_registry.py`.

Required issue codes:

- `duplicate_legacy_id`
- `duplicate_domain`
- `missing_website`
- `missing_location`
- `adapter_without_supplier`
- `supplier_without_adapter`
- `registered_placeholder_adapter`
- `name_domain_mismatch`

- [ ] **Step 4: Run audit tests**

Run:

```bash
python3 -m unittest tests.test_supplier_registry -v
```

Expected: pass for audit behavior.

- [ ] **Step 5: Generate audit report**

Run:

```bash
python3 tools/audit_supplier_registry.py
```

Expected:

- `reports/supplier_master_audit.md` lists the actual conflict counts.
- Duplicate legacy IDs are listed explicitly.
- Adapter/dashboard mismatches are listed explicitly.
- No issue is silently ignored.

## Task 3: Verify Suppliers Against Real Sources

**Files:**
- Create: `data/master/supplier_review_queue.csv`
- Create: `data/master/supplier_rejections.csv`
- Create: `data/master/suppliers.canonical.json`
- Create: `data/master/suppliers.canonical.csv`

- [ ] **Step 1: Build the verification queue**

Start from `data/raw/current_dashboard_suppliers.csv` and `reports/supplier_master_audit.md`.

Priority order:

1. Suppliers with active adapters.
2. Suppliers with duplicate legacy IDs.
3. Suppliers with duplicate domains.
4. Suppliers marked public or PDF in `ACCESS_META`.
5. Login and quote suppliers.
6. Offline or inaccessible suppliers.

- [ ] **Step 2: Verify each supplier**

For each candidate supplier:

- Visit the official website if present.
- Confirm the supplier name.
- Confirm the domain belongs to the supplier.
- Confirm city/state/province when available.
- Confirm whether the supplier sells wholesale, retail, quote-only, login-gated, public catalog, or PDF/catalog list.
- Record evidence URL(s).
- Record verification status and reason.

If web access is used, source URLs must be current and real. Do not rely on search snippets alone.

- [ ] **Step 3: Mark accepted suppliers**

A supplier can be `verified` only when:

- identity is supported by at least one evidence URL
- website/domain is not in conflict with another accepted supplier
- location is supported or intentionally blank with a reason
- access model is supported by evidence

- [ ] **Step 4: Mark review-queue suppliers**

Use `needs_review` when:

- official website is unavailable
- evidence sources conflict
- supplier appears real but location or wholesale status cannot be confirmed
- supplier may be a duplicate but cannot be confidently merged
- source requires login and no approved credentials exist

- [ ] **Step 5: Mark rejected suppliers**

Use `rejected` when:

- website/domain belongs to a different entity
- supplier appears fabricated or unverifiable after source checks
- supplier is a duplicate already represented by a canonical supplier
- supplier is not a supplier relevant to BloomBox procurement
- supplier is permanently offline with no reliable alternate evidence

Every rejected record must include `rejection_reason` and any evidence checked.

## Task 4: Build Adapter-To-Supplier Map

**Files:**
- Create: `data/master/adapter_supplier_map.csv`
- Modify: `scrape/ADAPTER_AUDIT.md`

- [ ] **Step 1: Extract registered adapters**

Read adapter classes from `scrape/adapters/*.py` and collect:

- numeric `supplier_id`
- class name
- module path
- `supplier_name`
- `requires_login`
- `prefer_tier`
- obvious placeholder/disabled comments

- [ ] **Step 2: Map adapters to canonical suppliers**

For each registered adapter:

- Match by legacy ID first.
- If legacy ID is duplicated, verify by supplier name and website/domain.
- If no verified canonical supplier exists, mark adapter as `quarantine`.

- [ ] **Step 3: Classify adapter status**

Use:

- `active_verified`: adapter maps to a verified supplier and has a recent successful live run.
- `active_unverified`: adapter maps to a verified supplier but lacks fresh live-run evidence.
- `placeholder_registered`: adapter is registered but has empty URLs, guessed selectors, or file comments saying disabled/placeholder.
- `disabled`: adapter is commented out or intentionally not registered.
- `none`: no adapter exists.

## Task 5: Acceptance Gates Before Dashboard Rewrite

**Files:**
- Modify only after gates pass: `index.html`
- Modify only after gates pass: `README.md`

- [ ] **Gate 1: Canonical registry exists**

Required files:

- `data/master/suppliers.canonical.json`
- `data/master/suppliers.canonical.csv`
- `data/master/supplier_review_queue.csv`
- `data/master/supplier_rejections.csv`
- `data/master/adapter_supplier_map.csv`

- [ ] **Gate 2: No duplicate canonical IDs**

Run:

```bash
python3 tools/audit_supplier_registry.py --canonical data/master/suppliers.canonical.json
```

Expected: zero duplicate canonical IDs and zero duplicate accepted domains unless explicitly justified.

- [ ] **Gate 3: Every verified supplier has evidence**

Expected: every `verification_status=verified` row has at least one `evidence_urls` entry.

- [ ] **Gate 4: Adapter mapping is resolved**

Expected: every registered adapter is mapped to one canonical supplier or quarantined with a reason.

- [ ] **Gate 5: Human review queue is explicit**

Expected: `supplier_review_queue.csv` contains every uncertain supplier and no uncertain supplier is silently promoted.

## Task 6: Rewrite Dashboard Data Only After Verification

**Files:**
- Modify: `index.html`
- Modify: `README.md`
- Modify: `scrape/ADAPTER_AUDIT.md`

- [ ] **Step 1: Replace old supplier array source**

Use `data/master/suppliers.canonical.json` as the source of truth. Do not manually paste unverified raw records into `index.html`.

- [ ] **Step 2: Remove stale counts and overstated claims**

Dashboard and README counts must be generated from the canonical registry, not hand-written.

- [ ] **Step 3: Keep review/rejected records out of production views**

The primary dashboard should show verified suppliers only. Add a separate review report or admin-only view later if needed.

- [ ] **Step 4: Re-run verification**

Run:

```bash
python3 -m unittest tests.test_supplier_registry tests.test_run tests.test_vault tests.test_credentials_cli -v
node -e "const fs=require('fs'); const text=fs.readFileSync('index.html','utf8'); [...text.matchAll(/<script[^>]*>([\\s\\S]*?)<\\/script>/g)].forEach((m)=>new Function(m[1])); console.log('index scripts ok')"
```

Expected: all tests pass and dashboard scripts parse.

## Final Done Criteria

This tranche is done only when:

- The canonical supplier registry exists.
- Every verified supplier has source evidence.
- Duplicate legacy IDs are resolved, merged, rejected, or left in review with reasons.
- Adapter IDs map cleanly to canonical suppliers or are quarantined.
- The dashboard no longer relies on the old raw supplier array as truth.
- README language reflects actual verified counts.
- No generated file contains invented supplier facts.

## Commit Guidance

Use small commits:

1. `chore: extract raw dashboard supplier import`
2. `test: add supplier registry audit coverage`
3. `chore: add supplier identity audit report`
4. `data: add verified canonical supplier registry`
5. `chore: map adapters to canonical suppliers`
6. `docs: document verified supplier master list`

Do not combine verification data changes with scraper behavior changes.
