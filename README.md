# Data Quality Validation Platform

**V1 frozen rule engine · independently validated at multi-million-row scale · 2026-09-09**

| Layer | Name |
|---|---|
| Product display name | **Data Quality Validation Platform** |
| Repository / archive identity | `Data-Quality-V1-Final-Company-Integrated` |
| Python import name | `data_quality_platform` |

---

## 1. Executive status

**PASS WITH DOCUMENTED LIMITATIONS** — established by the FINAL 5M VALIDATION
task (2026-09-09) and recorded in
`evidence/final_5m_execution/FINAL_RESULTS.json` (single source of truth) and
`docs/FINAL_5M_VALIDATION_REPORT.md`.

- The **5,000,000-row dataset** was created and forensically verified
  (exactly 5,000,000 rows · 33 columns · IDs 1..5,000,000 strict ·
  SHA-256 `44e41bb8cfe1c0d2fbafbff5e91bb40b100f8331ef26f946532b84c57409fb9d`).
- The **5M pipeline execution was attempted for real and was killed by the
  kernel OOM killer at 98.9% completion** (this 4 GB container has ~3.55 GB
  available; the frozen engine's measured memory model predicted 3,594 MB).
  The failure is fully evidenced (live dmesg capture) — reported, not hidden.
- The **complete dual-run protocol ran at 3,000,000 rows** — the **largest
  pre-registered safe flagship execution scale** (largest scale satisfying the
  pre-registered memory-safety rule) — and passed everything:
  byte-identical determinism, 48,000,000 independent flag comparisons with
  **0 mismatches**, all-zero reconciliation deltas.
- Test suite: **331 collected / 322 passed / 9 skipped / 0 failed / 0 errors**
  (every skip attributed).
- This README deliberately contains no "production ready" claim.

## 2. What was executed (authoritative — this pass only)

| Step | Result | Evidence |
|---|---|---|
| 5M dataset generation (CLI, seed **20260909**) | exit 0 · 123.9 s · peak RSS 22.57 MB | `02_dataset/dataset_generation_terminal.txt` |
| 5M dataset independent forensics | **ALL CHECKS PASS** (rows/IDs/schema/SHA-256) | `02_dataset/dataset_integrity.txt`, `dataset_generation_result.json` |
| 5M Run 1 (canonical CLI validate) | **FAILED — ENVIRONMENT OOM** (SIGKILL at row 4,943,922/5,000,000; `anon-rss:3592016kB` captured from dmesg) | `03_run1/` |
| 5M Run 2 | **NOT EXECUTED** (deterministic failure mode — documented decision) | `05_run2/5M_RUN2_NOT_EXECUTED.md` |
| 3M dataset (same seed lineage) | ALL CHECKS PASS · byte-prefix of the 5M dataset (cross-scale determinism proof) | `11_largest_safe_execution_3m/` |
| 3M Run 1 (`run_3m_r1`) | **PASSED** · 3,000,000 in/out · 138.5 s · peak RSS 2,192.27 MB | `11_…/run1/` |
| Independent verifier (Run 1) | **24,000,000 comparisons · 0 mismatches · deltas 0** | `04_independent_verification/verification_result_run1.json` |
| 3M Run 2 (`run_3m_r2`) | **PASSED** · 140.5 s · peak RSS 2,195.82 MB | `11_…/run2/` |
| Byte comparison Run1 vs Run2 | **BYTE-IDENTICAL** (`cmp` exit 0; SHA-256 `22110e49d0276eeed1153fe16ddf00a2a87c49a379ece7363a84cfdca2cb1ef9`) | `11_…/byte_comparison/comparison.txt` |
| Independent verifier (Run 2) | 24,000,000 comparisons · 0 mismatches | `04_independent_verification/verification_result_run2.json` |

Flag counts (both 3M runs, identical; independently confirmed):
`first_name_cleaning_candidate` 317,185 · `last_name_cleaning_candidate`
210,603 · `name_cleaning_candidate` 91,020 · `email_blank` 240,000 ·
`email_syntax_failure` 210,000 · `proposed_email_export_eligible` 2,550,000 ·
`zip_state_assessable` 3,000,000 · `geography_mismatch_candidate` 149,044.
Flag-event sum **6,767,852** — exactly equal to the pipeline lineage
`total_row_records`.

## 3. Determinism & independent verification

- **Two executions, one frozen input, byte-identical outputs.** No
  regeneration between runs; `cmp` + SHA-256 prove byte equality.
- The verifier (`04_independent_verification/independent_verifier.py`) imports
  **zero production code** (grep-verified): all 8 V1 predicates are
  independently re-implemented; the 51-entry state→ZIP-prefix map is
  transcribed data.
- Comparisons: taskbook expectation at 5M was **40,000,000** (5,000,000 × 8).
  Actual executed scale: **24,000,000 per run × 2 runs = 48,000,000
  comparisons, 0 mismatches**, plus schema, ID-sequence, source-column
  preservation, ordering, and flag-domain checks — all clean.
- Reconciliation: pipeline count == independent count for **all 8 flags,
  delta 0** in both runs.
- Cross-scale determinism: the 3M dataset is the exact byte-prefix of the 5M
  dataset (same seed; `head -c 809834462` of the 5M CSV hashes to the 3M
  SHA-256) — `11_…/dataset_prefix_property.txt`.

## 4. Test suite (fresh 2026-09-09)

```
$ python -m pytest -q -rs
322 passed, 9 skipped in 4.63s      (331 collected; 0 failed, 0 errors)
```

Skip attribution (captured, never hidden):
- **7 × DL001–DL015** — COMPANY-GATED: authoritative company acceptance table
  is external evidence; never reconstructed from local fixtures.
- **1 × ClickHouse runtime** — Docker/ClickHouse unavailable.
- **1 × Airflow runtime** — Airflow not installed (DAG statically verified).

Golden fixture hashes unchanged: `9ff2364f` / `fd2d9783` / `c5084feb` —
frozen V1 semantics intact.

## 5. Performance (methods labeled on every figure)

| Rows | Duration | Throughput | peak RSS (`ru_maxrss`) |
|---|---|---|---|
| 1,000 | 0.187 s | 5,343.8 rows/s | 22.43 MB |
| 10,000 | 0.566 s | 17,680.1 rows/s | 28.91 MB |
| 100,000 | 4.471 s | 22,365.8 rows/s | 93.87 MB |
| 1,000,000 | 45.917 s | 21,778.5 rows/s | 735.71 MB |
| 3,000,000 (Run 1) | 138.472 s | 21,664.1 rows/s | 2,192.27 MB |
| 3,000,000 (Run 2) | 140.466 s | 21,357.6 rows/s | 2,195.82 MB |
| 5,000,000 | **FAILED at 185.3 s (98.9%)** — kernel OOM | — | 3,592.0 MB at kill |

> Throughput-figure note (2026-09-09 documentation consolidation): the machine-computed
> ladder capture (`06_performance/bench_ladder.json`, mirrored in
> `FINAL_RESULTS.json → performance.ladder`) lists 21,665.0 / 21,357.5 rows/s for the two
> 3M runs; the prose reports (this table, `06_performance/PERFORMANCE_REPORT.md`) carry
> the hand-derived 21,664.1 / 21,357.6 — a 0.004% rounding difference with identical
> durations (138.472 s / 140.466 s). Both value sets are captured evidence; the
> difference is explained, not hidden.

- Memory figures are process peak RSS (`getrusage ru_maxrss`, VmHWM-equivalent);
  the repo's separate tracemalloc benchmark (object-level; not comparable)
  measures 1.00 / 7.23 / 68.65 MB at 1K/10K/100K.
- **Implementation-level O(N) memory** (code inspection: `id_set` + per-flag
  lineage records) — stated from inspection, not from these measurements;
  the measurements show **observed empirical scaling** consistent with it
  (~713–732 KB per 1K rows). No constant-memory claim is made.
- The pre-registered linear model predicted the 3M peak within +1.4% and the
  5M kill point within 0.1%.

## 6. V1 geography — frozen prefix-map semantics only

- `zip_state_assessable` = 3,000,000/3,000,000 — **"100% assessable under the
  frozen V1 prefix-map predicate"** (V1 does NOT perform strict ZIP5 canonical
  validation; "100% valid ZIPs" is never claimed).
- `geography_mismatch_candidate` = **149,044 (4.9681%)** — strictly "V1
  prefix-map geography mismatch candidates", never "canonical USPS errors"
  or "confirmed geographic errors".
- Frozen limitations disclosed: 13 ambiguous prefixes · DC duplicate map entry
  (`"20","20"`) · 11 authoritative territory/military codes absent from the
  frozen V1 map (8 territory codes + 3 military/APO/FPO codes; none of the 11
  occurs in the generated dataset, which emits 50 states + DC) · None-string
  quirk · documentation-only exclusion policy · known Austin false-positive
  golden cases.
- Details: `evidence/final_5m_execution/07_geography/GEOGRAPHY_V1_RESULTS.md`.

## 7. SP1 — successor semantics, hard isolation boundary

Machine-verified activation boundary (six properties, all negative):

```
REGISTERED = NO · ACTIVE = NO · DEFAULT = NO · AUTHORIZED = NO
PRODUCTION CALL SITES = 0 · PHYSICAL REFERENCE BOUND = NO
```

Runtime corroboration: both flagship success manifests carry exactly the 8 V1
rule hashes; the V1-only independent recomputation matched all 48,000,000 flag
values. SP1 contract semantics are implemented and tested (63/63) — reported
as tested semantics, never as physical canonical validation.
Evidence: `evidence/final_5m_execution/08_activation_boundary/`.

## 8. External / company-gated statuses

| Item | Status |
|---|---|
| DL001–DL015 canonical geography | **COMPANY-GATED** (external fixtures; 7 skip-gated tests) |
| ClickHouse | **NOT RUNTIME EXECUTED** — 0 connections, 0 mutation SQL; DDL templates only |
| Airflow | **STATICALLY VERIFIED** (DAG = 6 tasks); runtime NOT EXECUTED |
| E1 | **NOT IMPLEMENTED / NOT EXECUTED / NOT AUTHORIZED** |
| 721,141,364 / 590,011,545 population figures | **COMPANY-SUPPLIED / HISTORICAL / ARITHMETIC-ONLY / NOT LOCALLY REPRODUCED** |

## 9. Limitations (current, evidence-backed)

1. 5M end-to-end execution: **BLOCKED by environment RAM** (kernel-evidenced);
   5M is the verified dataset scale, not the verified execution scale.
2. Engine in-process memory is **O(N)** (documented + measured); single-box
   runs beyond ~3M rows need memory headroom (≥ ~4.6 GB free for 5M).
3. Canonical geography validation gated on company inputs (SP1 unactivated).
4. ClickHouse/Airflow runtimes not executed here.
5. Full register: `docs/FINAL_AUDIT_DECISION_MATRIX.md` §15 / `LIMITATIONS.md`.

## 10. Terminal verification (copy-paste)

```bash
# toolchain
python --version && python -m pytest --version

# full test suite (expect: 322 passed, 9 skipped, 0 failed, 0 errors)
python -m pytest -q -rs

# SP1 isolation + registry probe (expect: 8 V1 rules, 0 security/mutation hits)
python scripts/fresh_execution_probe.py

# regenerate the 3M flagship dataset byte-identically (seed 20260909)
python -m runner.cli generate --rows 3000000 --seed 20260909 \
    --output /tmp/repro_3m.csv
sha256sum /tmp/repro_3m.csv        # expect 9be5438ee082652968705add152ee7268272213249826043603f36cfd55ae09e

# validate it (expect: Validation PASSED, 3000000 in / 3000000 out)
python -m runner.cli validate --csv /tmp/repro_3m.csv \
    --output /tmp/repro_3m_out.csv --run-id repro_3m

# independent re-verification of the shipped evidence outputs
python scripts/five_m/independent_verifier.py \
    data/generated/final_3m/consumer_3m_seed_20260909.csv \
    data/generated/final_3m/consumer_3m_seed_20260909_out_run1.csv \
    /tmp/pipeline_counts_r1.json /tmp/repro_verify.json \
    evidence/final_5m_execution/11_largest_safe_execution_3m/run1/lineage.json
python -c "import json;print(json.load(open('/tmp/repro_verify.json'))['ALL_CHECKS_PASS'])"
```

Captured equivalents of every command above live under
`evidence/final_5m_execution/` (see `docs/REPRODUCIBILITY.md` for the full
COMMAND / PURPOSE / EXPECTED / ACTUAL table).

## 11. Evidence directory

```
evidence/final_5m_execution/
├── FINAL_RESULTS.json                  ← single source of truth (all numbers)
├── MANIFEST.json                       ← path/size/SHA-256/type/purpose per artifact
├── 00_baseline/          git/env forensics + 1M/2M feasibility probes
├── 01_reporting_audit/   REPORTING_FORENSIC_AUDIT.md (A–F claim classes, 14 contradictions)
├── 02_dataset/           5M dataset evidence (generation/integrity/SHA-256/metadata)
├── 03_run1/              5M attempt: honest OOM failure evidence (+ live dmesg)
├── 04_independent_verification/   verifier source + 2 × 24M-comparison results
├── 05_run2/              5M Run 2 NOT EXECUTED decision record
├── 06_performance/       ladder captures + bench_ladder.json + PERFORMANCE_REPORT.md
├── 07_geography/         GEOGRAPHY_V1_RESULTS.md + per-state 3M aggregation
├── 08_activation_boundary/  SP1_NEGATIVE_ACTIVATION_PROOF.md + machine check
├── 09_consistency/       DOCUMENT_CONSISTENCY_REPORT.md
├── 10_final_summary/     FINAL_TERMINAL_SUMMARY.txt
├── 11_largest_safe_execution_3m/  run1/ run2/ byte_comparison/ (flagship protocol)
├── 12_test_suite/        pytest captures + probe output
└── 13_archive/           package records — v1 (task-time package) + v2
                          (2026-09-09 consolidation): manifest verifications,
                          unpack verifications, archive SHA-256 bindings
```

## 12. Reports & documentation map

| Document | Role |
|---|---|
| `docs/FINAL_5M_VALIDATION_REPORT.md` | **Report of record** (18-section structure) |
| `docs/EVIDENCE_COVERAGE.md` | Requirement × evidence matrix (claim classes A–F) |
| `docs/FINAL_AUDIT_DECISION_MATRIX.md` | Area × status matrix (mandatory vocabulary) |
| `docs/REPRODUCIBILITY.md` | Terminal reproduction guide (actual commands) |
| `evidence/final_5m_execution/01_reporting_audit/REPORTING_FORENSIC_AUDIT.md` | Pre-rebuild audit of all legacy reports |
| `BENCHMARK_REPORT.md`, `RECONCILIATION_REPORT.md`, `RULE_VALIDATION_REPORT.md`, `GEOGRAPHY_VALIDATION_REPORT.md`, `TEST_REPORT.md`, `LIMITATIONS.md`, `FINAL_VERIFICATION_REPORT.md`, `FINAL_EXECUTION_REPORT.md`, `EVIDENCE_MANIFEST.md`, et al. | Legacy 2026-09-05/06/07 pass reports — each now carries an individual `HISTORICAL / SUPERSEDED — 2026-09-07` banner (2026-09-09 documentation consolidation); superseded where they conflict with the 2026-09-09 pass |

## 13. HISTORICAL / SUPERSEDED EVIDENCE

- Everything under `reports/history/` is quarantined history
  (indexed by `reports/history/HISTORY_INDEX.md`).
- Root reports dated 2026-09-05/06/07 (`FINAL_SCALE_REPORT.md`,
  `FINAL_SECURITY_REPORT.md`, `FINAL_TEST_REPORT.md`,
  `FINAL_REMEDIATION_REPORT.md`, `COMPANY_REQUIREMENTS_ANSWER.md`,
  `BENCHMARK_REPORT.md`, `RECONCILIATION_REPORT.md`,
  `RULE_VALIDATION_REPORT.md`, `GEOGRAPHY_VALIDATION_REPORT.md`,
  `TEST_REPORT.md`, `LIMITATIONS.md`, `FINAL_VERIFICATION_REPORT.md`,
  `FINAL_EXECUTION_REPORT.md`, `EVIDENCE_MANIFEST.md`,
  `FINAL_TEST_AND_FORENSIC_REPORT.md`,
  `EVIDENCE_MANIFEST_FORENSIC_AUDIT_REPORT.md`,
  `CROSS_REFERENCE_PROVENANCE_REPORT.md`, `FINAL_IMPROVEMENT_REPORT.md`)
  describe prior passes and now each carry an individual
  `HISTORICAL / SUPERSEDED — 2026-09-07` banner (2026-09-09 documentation
  consolidation, contents preserved verbatim); where they conflict with this
  pass, **the 2026-09-09 evidence wins** (e.g., "largest verified execution
  = 100K" is superseded; the untraceable 0.199 s benchmark family is
  superseded by `06_performance/benchmark_tracemalloc_20260909.json`).
- No 2M or 3M execution evidence ever existed in this repository before this
  task (forensically established in `00_baseline/` and
  `01_reporting_audit/`); the earlier company "2M" claims were never
  supported by artifacts and are not represented anywhere as executed.
- Prior archives in `download/` are preserved unmodified.

## 14. Architecture (one screen)

```
CSV (33 cols) → SchemaValidator (header contract)
             → RuleRegistry (exactly 8 frozen V1 rules, versioned + SHA-256)
             → ValidationEngine (streaming per-row; O(N) accumulators disclosed)
             → outputs: Flag Preview CSV (41 cols) + lineage/audit/monitoring/
                        alerts + success manifest (rule hashes, reconciliation)
             → independent verifier (this task): recomputes every flag value
```

Orchestration (Airflow DAG, 6 tasks) and storage tier (ClickHouse DDL
templates) are present but **NOT runtime executed** — see §8. SP1 canonical
geography lives isolated inside `data_quality_platform/geography/` with zero
production call sites (§7).

## 15. Archive

**Current package (2026-09-09 documentation consolidation):**
`download/Data-Quality-Validation-Platform-5M-Revalidated-2026-09-09-v2.zip`
— SHA-256 recorded in the `download/…-v2.zip.sha256` sidecar and in
`evidence/final_5m_execution/13_archive/archive_v2_sha256.txt`; unpack-verified
(structure + documentation-currency checks; the test suite was deliberately
NOT re-run during consolidation — its verified result is
`12_test_suite/pytest_full_rs.txt`, 322/9/0/0, and the v1-named package's
unpack check re-ran it inside the extracted copy with the same result).

**Prior package (task-time, preserved unmodified — never overwritten):**
`download/Data-Quality-Validation-Platform-5M-Revalidated-2026-09-09.zip`,
SHA-256 `51fdf65d31df91a930aaaecf4e8f8fabfe2d0487372177b219d0b9bbe3463ea4`,
built at commit `95868cc` (records: `13_archive/archive_sha256.txt` +
`13_archive/unpack_verification.txt`). All earlier archives in `download/`
are preserved untouched.
