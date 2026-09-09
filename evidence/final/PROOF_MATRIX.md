# PROOF MATRIX — FINAL DELIVERY EVIDENCE

**Report date:** 2026-09-05
**Revision history:** Revision 1 = commit `beefcaa8` (P-01…P-30, B-1…B-6); **Revision 2 = current** (SP1 contract delivered + pure implementation: P-31…P-38, B-1 reclassified)
**Purpose:** single-page, independently checkable proof table for the final delivery: every important claim is bound to a concrete artifact + hash + verification method. Evidence classes: **CURRENT VERIFIED** (recomputed this session), **HISTORICAL** (byte-preserved, hash-anchored), **BLOCKED** (input unavailable — never fabricated).

---

## 1. Baseline & integrity proofs

| # | Claim | Proof method | Value / Result | Class |
|---|---|---|---|---|
| P-01 | Baseline HEAD | `git log -1 --format='%H'` | `4065714c3c810c503020d60a8f726a485a5e09ac` | CURRENT VERIFIED |
| P-02 | Branch / upstream sync | `git rev-list --left-right --count HEAD...HEAD@{upstream}` | `main` / `0 0` / no stashes | CURRENT VERIFIED |
| P-03 | Historical verify-report evidence untouched | SHA-256 working tree vs `git cat-file blob HEAD:` | both `4c2ce2ed441ba86145409b9b4017c046ff28bb7bad1a80c17a5d4e117b5ca06d` | CURRENT VERIFIED |
| P-04 | Golden repaired fixture | `sha256sum tests/golden/golden_cases.csv` | `9ff2364f6b283ad26612677af99a39905ef9587654f1cef03206db994b2bc23e` | CURRENT VERIFIED |
| P-05 | Golden expected-results (repaired GC022) | `sha256sum tests/golden/expected_results.csv` | `fd2d9783718c7bd60ee89615309a3f5708c8e3fa0401c8fdbdcc4ed9db3a63b2` | CURRENT VERIFIED |
| P-06 | Geography edge cases unchanged | `sha256sum tests/golden/geography_edge_cases.csv` | `c5084feb4d8f2cee6dbe4bab67fc3f8fb15f39d2098f7ab8c6a5a5c9d6b8406f` | CURRENT VERIFIED |
| P-07 | Historical FINAL_VERIFICATION_REPORT preserved | `sha256sum FINAL_VERIFICATION_REPORT.md` | `c6d6c6873f9c306e7db7da8838d6d68457a93ef2b6d9589012514c8d969aee14` | HISTORICAL (anchored) |
| P-08 | Committed verification manifest | `sha256sum evidence/final_verification/manifest.json` | `d1d1fc4a993248f1555862fcfd01fe6421c6c6cb4c796185fc728af82237c3e4` | HISTORICAL (anchored) |
| P-09 | Q21 aggregator implementation hash | `sha256sum data_quality_platform/verification/scope_aggregator.py` | `3202eb179bdc9316c309848f70b05dd261653d198073ac6ff75c78e92b3960ef` | CURRENT VERIFIED |
| P-10 | Company MASTER REMEDIATION PROMPT | `sha256sum upload/Pasted Content_*.txt` (×2 identical) | `ccf9c3905b1cd1e77dec29442ab9c6cb4f0dd9e6057ec0e670caca39402f987c` | CURRENT VERIFIED (external artifact) |
| P-31 | SP1 contract provenance recorded (revision 2) | `docs/GEOGRAPHY_RULE_SP1_CONTRACT.md` §1 + `canonical.py` constants | document SHA `0cf6eb930149e975397b348709d8f7e83f96eb6eb70d2361cf66551ada311bc0`, source commit `ee7859e1ad521cb68ba32b604498d951c7690b19`, superseded `3297179ea3527f56091191c48e8f72606e000fc7b885da906a7e59b97e1aebc8` — **file not locally accessible; SHA is company-provided, recorded verbatim, not re-computable** | CURRENT RECORDED (company-supplied values) |
| P-32 | SP1 pure implementation exists and is isolated | `data_quality_platform/geography/canonical.py` + `references.py`; tripwire test `test_module_does_not_import_legacy_prefix_map` | module imports no `data_quality_platform.contracts`; registry untouched | CURRENT VERIFIED |
| P-33 | SP1 acceptance cases pass | `python -m pytest tests/unit/test_sp1_geography_contract.py -q` | **63 passed** incl. 7 authoritative cases (CA/90210 ✓; CA/00USA ✓; CA/0 ✓; CA/000CA ✓; CA/"015 8" ✓; WA/99501→AK mismatch ✓; GU/96910 cross-absent-NOT-conflict ✓) | CURRENT VERIFIED |
| P-34 | SP1 independent oracle agreement | `scripts/sp1_independent_oracle.py` (separate prose-derived implementation, no import of the module under test) | 7/7 CASE OK; golden hashes 3/3 OK; Q21 recompute OK | CURRENT VERIFIED |
| P-35 | UNASSESSABLE != MISMATCH invariant | 13-probe mismatch-implies-assessable sweep + 8-probe unassessable-never-mismatch sweep in the SP1 test file | all probes conform | CURRENT VERIFIED |
| P-36 | Old-vs-successor divergence pinned | divergence matrix tests using REAL V1 classes | WA/99501: V1-accept vs successor-exclude; GU/96910: V1-assessable=0 vs successor-eligible; CA/00USA: V1-mismatch vs successor-eligible | CURRENT VERIFIED |

## 2. Test & verification proofs

| # | Claim | Proof method | Result | Class |
|---|---|---|---|---|
| P-11 | Full suite green | `python -m pytest tests/ -q` (2026-09-05, revision 2) | **291 passed / 9 skipped / 0 failed** (rev-1 baseline 228 + 63 SP1; zero regressions) | HISTORICAL (2026-09-05 state; superseded 2026-09-07: **322 passed / 9 skipped / 0 failed**, 331 collected — see README Fresh Test Results) |
| P-12 | All skips justified | `pytest -rs` | 1× ClickHouse unavailable · 1× Airflow not installed · 7× DL table absent (gate) | CURRENT VERIFIED |
| P-13 | CLI verify honest | `runner.cli verify` → scratch (side effect restored to HEAD bytes, P-03) | **20 PASS / 2 PARTIAL / 0 FAIL**; Q18+Q21 PARTIAL with verbatim evidence strings | CURRENT VERIFIED |
| P-14 | Q21 not hardcoded | `scripts/verify_q21_recompute.py` (independent recompute + source audit) | ALL CHECKS PASSED; recorded == recomputed; consumes `aggregate_scope` | CURRENT VERIFIED |
| P-15 | Golden integrity | `scripts/phase3_step8_6_recompute.py` (independent) | ALL INTEGRITY CHECKS PASS (50×43; IDs; 1:1 expected; carried conflicts pinned; 20/20 edge; deterministic) | CURRENT VERIFIED |
| P-16 | Geography V1 equivalence | `scripts/repro_prefix_map.py` (AST-extract + independent restatement) | 25 probes, 0 mismatches; DL comparison standing by (no fabrication) | CURRENT VERIFIED |
| P-17 | Flag Preview 41-column contract | `tests/contract/test_flag_preview_contract.py` green + committed flag_contract evidence (100/1000 rows) | PASS | CURRENT VERIFIED |
| P-18 | Reconciliation exact | committed `reconciliation/results.json` + fresh 1K run | per-flag expected==observed (100, 1000, fresh 1000) | CURRENT VERIFIED |

## 3. Safety proofs

| # | Claim | Proof method | Result | Class |
|---|---|---|---|---|
| P-19 | Zero ClickHouse mutation | full-session audit: only `GET /ping` (exit 7); no driver/Docker/credentials; skip-gated runtime test | production unchanged | CURRENT VERIFIED |
| P-20 | E1 never executed | no execution path added; safety conditions untouched; repo-wide sweep | NOT AUTHORIZED — not executed | CURRENT VERIFIED |
| P-21 | No secrets in tree | recursive scan (all code/config/doc extensions) + `.env*` check (`scripts/final_security_scan.py`, revision 2: 216 files) | zero secret-pattern hits; only empty defaults + env-var indirection; typed None-default declarations excluded by classification | CURRENT VERIFIED |
| P-22 | No raw PII in evidence | classified scan (`scripts/final_security_scan.py`) | 0 non-synthetic hits after classification: synthetic-domain emails (generator `DOMAINS` list + malformed list) and JSON timing floats excluded with recorded reasons; 22 CSVs synthetic-by-design | CURRENT VERIFIED |
| P-23 | Historical evidence never rewritten | P-03 + Phase-3 hash battery (`git cat-file` comparisons) | byte-identical to baseline | CURRENT VERIFIED |

## 4. Blocked items (never fabricated)

| # | Missing input | Consequence | Class |
|---|---|---|---|
| B-1 | `tips_data.tblZipStCtyIB` access OR company-approved snapshot | SP1 canonical **production validation** BLOCKED (pure implementation COMPLETE per sanctioned injectable-provider path); production activation deferred; no fabrication | BLOCKED (scope narrowed by revision 2) |
| B-2 | Exact DL001–DL015 table (15 rows, inputs+expected, provenance; DL013 definition; authoritative disagreement count) | 7 acceptance tests skip; DL gate BLOCKED; 5/15 partial prose descriptions exist in company MASTER PROMPT §10 | BLOCKED |
| B-3 | ClickHouse execution environment | SQL/Python parity BLOCKED; ClickHouse-scale tests BLOCKED | BLOCKED |
| B-4 | Airflow runtime | DAG runtime verification BLOCKED (static only) | BLOCKED |
| B-5 | Production-scale authorization + infrastructure | 721M-row verification NOT VERIFIED (0%) | BLOCKED |
| B-6 | E1 authorization | E1 remains NOT AUTHORIZED (by policy, not by accident) | NOT AUTHORIZED |

## 5. Delivery packaging proofs

| # | Claim | Proof method | Result |
|---|---|---|---|
| P-24 | ZIP exists, named per actual status | filesystem | `data-quality-platformV2-review-blocked-<FINAL_COMMIT>.zip` (see DELIVERY_MANIFEST.json) |
| P-25 | ZIP integrity | SHA-256 + size + file count | recorded in DELIVERY_MANIFEST.json |
| P-26 | ZIP extracts cleanly | extraction into clean temp dir | success (structure verified) |
| P-27 | ZIP == final working tree | recursive byte comparison (excl. `.git/`) | identical |
| P-28 | Exclusions honored | archive listing checks | no `.git/`, no `__pycache__/`, no `.pytest_cache/`, no `.env*`, no `*.db/*.sqlite*`, no runtime-only dirs (`data/generated/`, `evidence/q20_cli/`, `evidence/rt_1k/`, `evidence/test_q9/`) |
| P-29 | Required files present | archive listing checks | all source/tests/SQL/config/Airflow/docs/evidence + new remediation files + final reports |
| P-30 | Final commit recorded | `git log -1` after final commit | FINAL_COMMIT recorded in DELIVERY_MANIFEST.json |
| P-37 | SP1 contract doc committed | `git ls-files docs/GEOGRAPHY_RULE_SP1_CONTRACT.md` + hash at packaging | provenance-preserving transcription artifact tracked in the final commit | CURRENT VERIFIED |
| P-38 | ZIP reflects revision-2 state | archive listing | includes `data_quality_platform/geography/`, `tests/unit/test_sp1_geography_contract.py`, `docs/GEOGRAPHY_RULE_SP1_CONTRACT.md`, updated report set | CURRENT VERIFIED |

## 6. Verification commands (reproducibility)

```bash
# integrity
sha256sum tests/golden/*.csv FINAL_VERIFICATION_REPORT.md
git cat-file blob HEAD:evidence/verification/verification_report.json | sha256sum

# tests
python -m pytest tests/ -q            # expect: 322 passed, 9 skipped (current tree, 331 collected)
                                      # 2026-09-05 revision-2 state was: 291 passed, 9 skipped
python -m pytest tests/ -q -rs        # expect: 9 justified skips
python -m pytest tests/unit/test_sp1_geography_contract.py -q   # expect: 63 passed

# verification harness (writes OUTSIDE repo to avoid side effect)
python -m runner.cli verify --evidence-dir <scratch_dir>   # expect: 20 PASS / 2 PARTIAL / 0 FAIL

# independent recomputes (repo-external scripts)
python scripts/verify_q21_recompute.py
python scripts/phase3_step8_6_recompute.py
python scripts/repro_prefix_map.py
python scripts/sp1_independent_oracle.py    # revision 2: expect ALL CHECKS PASSED
python scripts/final_security_scan.py       # revision 2: expect 0 secret hits, 0 non-synthetic PII

# reachability (READ-ONLY)
curl -s -m 3 http://localhost:8123/ping   # expect: exit 7 (unreachable)
```
