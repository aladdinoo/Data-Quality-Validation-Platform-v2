# SP1 NEGATIVE ACTIVATION PROOF
Task: FINAL 5M VALIDATION + PROFESSIONAL REPORTING REBUILD
Check artifact: `sp1_activation_check.json` (this directory), produced by
`scripts/five_m/phase9_sp1.py` on 2026-09-09. Overall result: **PASS — SP1 is
fully isolated; every activation property is negative.**

## Verified boundary properties

| Property | Value | Evidence (machine-checked) |
|---|---|---|
| REGISTERED | **NO** | `RuleRegistry.create_default()` contains exactly the 8 V1 rule ids; `sp1_in_default_registry = false` |
| ACTIVE | **NO** | Both flagship-run success manifests (`11_largest_safe_execution_3m/run1/manifest.json`, `run2/manifest.json`) carry exactly the 8 V1 `rule_hashes`; no SP1 hash present. The 3M validation physically executed V1 rules only |
| DEFAULT | **NO** | 0 config files reference SP1/canonical routing (`configs/` scanned) |
| AUTHORIZED | **NO** | 0 activation-authorization artifacts found anywhere in the repository (regex sweep over md/yaml/json/toml) |
| PRODUCTION CALL SITES | **0** | grep for `compute_zip5` / `evaluate_geography` / `sp1_eligibility` / `resolve_reference` across `data_quality_platform/`, `runner/`, `scripts/`: zero references in the validation path. References exist only inside SP1's home package: `geography/canonical.py` (definitions), `geography/references.py`, `geography/__init__.py` (package re-exports — the documented isolation topology, identical to `fresh_execution_probe.py` output since FINAL-CONSOLIDATION) |
| PHYSICAL REFERENCE BOUND | **NO** | `validation/engine.py` contains no SP1/canonical import or call (regex-verified); engine geography = V1 prefix-map rules |

## What MAY be claimed about SP1 (contract scope only)

- SP1 canonical/reference semantics are IMPLEMENTED and TESTED:
  63/63 SP1 contract tests pass in the fresh 2026-09-09 suite run
  (322 passed / 9 skipped / 0 failed / 0 errors).
- The SP1 contract decision record and pinned constants remain
  COMPANY-SUPPLIED documents (verified by hash only, not re-derived).

## What may NOT be claimed

- SP1 is NOT a physical canonical validator in this delivery: no validation
  decision anywhere in the 3M flagship run (or any other run in this pass)
  used SP1.
- Any wording that could read as "SP1 active/default/authorized/production"
  is false for this repository state and must not appear in any current
  document (checked again in 09_consistency/DOCUMENT_CONSISTENCY_REPORT.md).

## Runtime corroboration (strongest form of the proof)

The 3,000,000-row flagship execution produced its success manifest with
`rule_hashes` = exactly the 8 frozen V1 rule ids and `reconciliation.passed =
true`. The independent verifier recomputed all 24,000,000 flag values with
independently implemented V1 predicates and found 0 mismatches. If SP1 had
participated in the run, the V1-only recomputation could not have matched the
pipeline output byte-for-byte in every flag cell.
