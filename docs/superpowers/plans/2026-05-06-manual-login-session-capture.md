# Manual Login Session Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe headed-browser login handoff that lets the human complete CAPTCHA/login once, then saves reusable supplier session state for Playwright fetches.

**Architecture:** Keep CAPTCHA handling manual. Add a focused `scrape.manual_login` module for browser handoff, form prefill, success detection, and storage-state persistence. Extend `scrape.core.stealth` and the Playwright fetch tier to reuse saved storage state when present.

**Tech Stack:** Python 3 standard library, Playwright optional runtime dependency, existing macOS Keychain credential loader, unittest.

---

### Task 1: Session State Storage Helpers

**Files:**
- Modify: `scrape/core/stealth.py`
- Test: `tests/test_manual_login.py`

- [ ] Write failing tests for `storage_state_path`, `has_storage_state`, and private parent directory creation.
- [ ] Run `python3 -m unittest tests.test_manual_login -v` and verify failure.
- [ ] Implement storage-state helpers in `scrape/core/stealth.py`.
- [ ] Run `python3 -m unittest tests.test_manual_login -v` and verify pass for this task.

### Task 2: Manual Login Utility

**Files:**
- Create: `scrape/manual_login.py`
- Modify: `scrape/credentials.py`
- Test: `tests/test_manual_login.py`, `tests/test_credentials_cli.py`

- [ ] Write failing tests for login success detection and credential prefill without any submit/CAPTCHA click.
- [ ] Run targeted tests and verify failure.
- [ ] Implement `evaluate_login_success`, `prefill_login_fields`, and `capture_manual_login_session`.
- [ ] Add `python3 -m scrape.credentials login-session --id ...` CLI wiring.
- [ ] Run targeted tests and verify pass.

### Task 3: Playwright Session Reuse

**Files:**
- Modify: `scrape/core/fetcher.py`
- Test: `tests/test_manual_login.py`

- [ ] Write failing unit test proving `_fetch_playwright` uses saved storage state when present.
- [ ] Implement storage-state reuse in the Playwright context creation path.
- [ ] Run scraper/runtime tests.

### Task 4: Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `scrape/README.md`

- [ ] Document manual CAPTCHA handoff command for American Native Plants.
- [ ] Run full unit test command.
- [ ] Run canonical audit.
- [ ] Run dashboard script parse check.
- [ ] Commit the finished change.
