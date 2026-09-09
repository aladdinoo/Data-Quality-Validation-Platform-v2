# GEOGRAPHY V1 RESULTS — FROZEN V1 PREFIX-MAP SEMANTICS ONLY
Task: FINAL 5M VALIDATION + PROFESSIONAL REPORTING REBUILD
Data basis: 3,000,000-row flagship execution, Run 1 output
(`11_largest_safe_execution_3m/run1/`, independently verified with 0 mismatches;
per-state aggregation in `geography_per_state_3m.json`, this directory).

## 1. Which geography semantics are reported here — and only these

Everything in this report describes the **frozen V1 prefix-map predicate**
(`data_quality_platform/rules/v1_rules.py`: `zip_state_assessable`,
`geography_mismatch_candidate` over the 51-entry `STATE_ZIP_PREFIXES` map in
`data_quality_platform/contracts.py`). This is a **2-3 digit ZIP-prefix
consistency check**, NOT canonical ZIP validation.

Explicitly NOT claimed in this report:
- NOT "canonical USPS errors" — the counts below are "V1 prefix-map geography
  mismatch candidates".
- NOT "confirmed geographic errors" — no canonical/reference validation ran.
- NOT "100% of ZIPs are valid" — V1 does not perform strict ZIP5 canonical
  validation and never has.

## 2. Headline results (3,000,000 rows, Run 1 = Run 2 byte-identical)

| Metric | Value |
|---|---|
| Rows processed | 3,000,000 |
| `zip_state_assessable` = 1 | 3,000,000 (**100% assessable under the frozen V1 prefix-map predicate**) |
| `geography_mismatch_candidate` = 1 | **149,044** |
| Mismatch-candidate rate | 4.9681% |

The "100%" statement is scoped exactly as required: every row had a non-empty
ZIP and a state present in the V1 51-entry map, so the V1 assessable predicate
fired on 100% of rows. It says nothing about ZIP5 validity.

## 3. Why the observed mismatch rate is slightly below the injected 5%

The frozen generator injects deliberate ZIP/state mismatches on 5 of every 100
rows (`defect_modes` weighting: 5 × `zip_state_mismatch` per 100), so the
naive expectation is 150,000 mismatch candidates at 3M rows. Observed:
**149,044 — i.e. 956 fewer**. The mechanism is V1's own semantics: the
generator builds a deliberate mismatch by taking a prefix from *another*
state's list; when that prefix is also owned by the row's own state (V1 map
contains ambiguous prefixes shared by two or three states), the V1 predicate
correctly reports a prefix match, and no mismatch candidate is raised.
Statistical-inference label: the 150,000 injected count is generator-design
arithmetic (D-class); the 956 delta is an observed consequence consistent with
the 13 ambiguous prefixes documented in §4 (not independently proven per-row —
per-row intent is not recorded in the output).

## 4. Frozen V1 limitation accounting (all still present, verified today)

| Limitation | Status in this dataset/map |
|---|---|
| DC duplicate prefix entry `"20", "20"` in the map | PRESENT (harmless duplicate, preserved frozen) |
| Ambiguous prefixes (one prefix, multiple owner states) | **13 prefixes**: 02 (MA/RI), 03 (ME/NH/RI), 19 (DE/PA), 22 (MD/VA), 24 (VA/WV), 38 (MS/TN), 71 (AR/LA), 83 (ID/WY), 84 (ID/UT), 88 (NM/NV), 96 (CA/HI), 97 (HI/OR), 99 (AK/WA) |
| Territory/military codes absent from the map | AS, GU, MP, PR, VI, AA, AE, AP (8 codes) — a row with such a state is NOT assessable under V1 |
| 1xx/7xx first-digit families | none fully uncovered (map covers both 0-9 first digits) |
| `str(None)`-style None ZIP/state quirk | documented in RULE_VALIDATION_REPORT / LIMITATIONS (V1 reads string fields; None becomes "None" text) — unchanged, not exercised by this synthetic dataset (generator never emits None) |
| Documentation-only exclusion policy | unchanged (no code exclusion exists; policy lives in docs) |
| Austin false-positive cases | documented in docs/FALSE_POSITIVE_REVIEW.md and golden cases — unchanged, still reproducible via tests/golden |

## 5. Per-state results (51 states, all assessable-100%)

Full machine-readable table: `geography_per_state_3m.json`. Summary:
rows per state are uniform (~58,6-59,1K, mean 58,824 = 3,000,000/51);
mismatch-candidate rates cluster at ~5.0-5.2% per state (the deliberate
injection), with the exact per-state value depending on which alternate-state
prefixes were drawn and how many landed on ambiguous prefixes.

Top-5 states by mismatch-candidate count:

| State | Rows | Mismatch candidates | Rate |
|---|---|---|---|
| IA | 59,031 | 3,077 | 5.213% |
| SD | 58,909 | 3,071 | 5.213% |
| NC | 58,868 | 3,000 | 5.096% |
| OK | 58,902 | 2,999 | 5.092% |
| PA | 59,058 | 2,998 | 5.085% |

## 6. SP1 contrast (boundary only — see 08_activation_boundary/)

- V1 (this report): prefix-map candidates, frozen, registered, executed.
- SP1: canonical/reference semantics fully implemented + contract-tested
  (63/63) but REGISTERED=no, ACTIVE=no, DEFAULT=no, AUTHORIZED=no,
  PRODUCTION CALL SITES=0, PHYSICAL REFERENCE BOUND=no. The flagship run
  manifests carry exactly the 8 V1 rule hashes — runtime proof that SP1 did
  not participate.
- Company-authoritative canonical validation: COMPANY-GATED / NOT AVAILABLE
  (DL001–DL015 fixtures external; ClickHouse never connected).

## 7. Traceability

- Counts: `04_independent_verification/verification_result_run1.json`
  (independent counts == pipeline counts, delta 0).
- Runtime execution: `11_largest_safe_execution_3m/run1/manifest.json`,
  `run1/terminal_output.txt`.
- Per-state aggregation: `07_geography/geography_per_state_3m.json`
  (generated from the actual Run 1 output by `scripts/five_m/phase8_geography.py`).
- Map/predicate source: `data_quality_platform/contracts.py`,
  `data_quality_platform/rules/v1_rules.py` (unchanged; golden hashes
  9ff2364f / fd2d9783 / c5084feb re-verified 2026-09-09).

## 8. Consolidation note (2026-09-09 documentation consolidation — appended; no prior content modified)

The §4 table enumerates the 8 commonly-cited territory/military codes (AS, GU, MP,
PR, VI, AA, AE, AP). For completeness: measured against the 62-code SP1
`STATE_ALLOWLIST`, the full set of authoritative territory/military codes absent
from the frozen V1 map is **11 codes** — 8 territory codes (AS, FM, GU, MH, MP,
PR, PW, VI) + 3 military/APO/FPO codes (AA, AE, AP). None of the 11 occurs in the
generated dataset (the generator emits 50 states + DC only; `per_state` covers
exactly those 51), so the 3M per-state results and all flag counts are unaffected.
Verified from `data_quality_platform/contracts.py` (`STATE_ZIP_PREFIXES`, 51 keys)
and `data_quality_platform/geography/canonical.py` (`STATE_ALLOWLIST`, 62 codes).
