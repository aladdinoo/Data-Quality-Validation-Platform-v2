# REPORTING FORENSIC AUDIT — FINAL 5M VALIDATION
Evidence class legend used throughout:
- **A — INDEPENDENTLY VERIFIED**: re-derived in this audit from raw artifacts/hashes by independent tooling.
- **B — LOCALLY REPRODUCED**: re-executed locally in this pass with captured terminal output.
- **C — CONTRACT/TEST VERIFIED**: backed by the repository's test suite / contract tests.
- **D — STATICALLY VERIFIED**: verified by code/inspection only (no runtime).
- **E — COMPANY-SUPPLIED**: originates from company documents; not locally reproducible.
- **F — NOT VERIFIED**: no evidence exists anywhere in the repository.

## 1. Scope and method

Audited: 22 root `*.md` reports + `docs/*.md` (6) + `reports/history/*.md` (11) +
`DELIVERY_MANIFEST.json`, using a full read of every in-scope file with
file:line claim extraction (2026-09-09). Claims were then classified against
raw evidence on disk (git history, evidence/ artifacts, code). The historical
2026-08-25/2026-09-05/2026-09-06 reports are quarantined by README:448 and
`reports/history/HISTORY_INDEX.md`; they were audited but are not rebuild
targets.

Result: **14 cross-document contradictions** and **6 stale-as-current clusters**
were identified (§3, §4). No fabricated company reference data, no SP1
activation claim, no ClickHouse execution claim, and no 2M/3M execution claim
was found anywhere in the current documents (the phantom "2M evidence chain"
from the earlier forensic closure audit never existed in this repo and no
document claims it did).

## 2. Major-claim classification (current documents, pre-rebuild state)

| # | Claim (where) | Class | Basis |
|---|---|---|---|
| 1 | Test suite 331 collected / 322 passed / 9 skipped / 0 failed / 0 errors (TEST_REPORT, README, EVIDENCE_MANIFEST.md, FINAL_EXECUTION_REPORT) | C | backed by committed logs; re-run scheduled in this task (will become B) |
| 2 | Benchmark 1K/10K/100K: 0.207/1.494/15.325 s; 1.01/7.23/68.65 MB "Peak memory (tracemalloc)" (BENCHMARK_REPORT, README, FINAL_EXECUTION_REPORT, DELIVERY_MANIFEST.json) | B | matches committed `evidence/benchmarks/benchmark.json` artifact; metric basis is labeled tracemalloc |
| 3 | Benchmark "0.199/1.438/14.607 s; 5,017/6,953/6,846 rows/s" (FINAL_TEST_AND_FORENSIC §28, FINAL_IMPROVEMENT §H) | **F** | contradicts the cited artifact; untraceable to any committed evidence (Contradiction 1) |
| 4 | "Largest verified execution scale = 100,000 rows … any earlier recorded pass" (README:24, BENCHMARK_REPORT:47-55) | **stale-as-current** | 2026-09-09 probes (00_baseline/feasibility_probe.txt) already executed 1M and 2M rows successfully; 5M run will supersede |
| 5 | Engine memory is O(N); no O(1) claim (engine docstring, README:135, BENCHMARK_REPORT, FINAL_SCALE_REPORT) | D | code inspection + measured probes; correct and mutually consistent |
| 6 | V1 geography = frozen prefix-map semantics; "PARTIAL by design"; 51-key STATE_ZIP_PREFIXES (GEOGRAPHY_VALIDATION_REPORT, RULE_VALIDATION_REPORT) | C/D | contract tests + code; correct framing |
| 7 | SP1: semantics implemented/tested; REGISTERED=no, ACTIVE=no, DEFAULT=no, AUTHORIZED=no, EXECUTED=no; 63/63 tests (GEOGRAPHY_VALIDATION_REPORT, README, COMPANY_ALIGNMENT) | C/D | suite + code; all activation wording is negated — no activation implication found |
| 8 | E1: NOT IMPLEMENTED / NOT EXECUTED / NOT AUTHORIZED | D | zero code identifiers; consistent everywhere |
| 9 | ClickHouse: never connected, 0 mutations; runtime NOT EXECUTED | D | consistent everywhere; no connection evidence exists |
| 10 | Airflow: DAG static-only (6 tasks); runtime NOT EXECUTED | D | DAG file inspection; consistent |
| 11 | Company 721,141,364 / 590,011,545 population figures | E | consistently labeled COMPANY-SUPPLIED / HISTORICAL / NOT EXECUTED / arithmetic-only (5/5 identities) |
| 12 | DELIVERY_MANIFEST 34/34 artifacts hash-verified; EVIDENCE_MANIFEST 127/127 | A | re-verified in FINAL-FORENSIC-CLOSURE-AUDIT (2026-09-09); will be re-verified again at packaging |
| 13 | Golden hashes 9ff2364f… / fd2d9783… / c5084feb… | A | recomputed independently in prior audits; unchanged in git |
| 14 | "final archive commit 5abca22a" (COMPANY_ALIGNMENT:11, CROSS_REFERENCE:14, DELIVERY_MANIFEST.json:11) | **stale-as-current** | actual HEAD is 0282e67b (5 commits later); Contradiction 5 |
| 15 | HEAD 71a303e2 (FINAL_EXECUTION, TEST_REPORT, LIMITATIONS, EVIDENCE_MANIFEST.md) | **stale-as-current** | those reports describe the 2026-09-07 pass truthfully but read as current without a supersession pointer |
| 16 | R3 = R1 OR R2 "contract-exact" (docs/DATA_FLOW_MAP:23, COMPANY_REQUIREMENTS_ANSWER:48) | **F (as a description of code)** | code implements an independent predicate (first==last OR both len ≤1); live counterexamples exist; company decision recorded as required |
| 17 | RBAC "3 roles" (README:315, FINAL_TEST_AND_FORENSIC:28) vs 4 roles | **contradiction** | code has 4 (admin, operator, viewer, pii_exporter); SECURITY.md is right |
| 18 | Seed 20260821 for all fresh local runs | B | committed CLI evidence; the NEW 5M run uses seed 20260909 and becomes authoritative |
| 19 | docs/ARCHITECTURE_MAP "SP1 successor eligibility NOT IMPLEMENTED" | **stale/contradiction** | contradicts docs/DATA_FLOW_MAP (same date) and DELIVERY_MANIFEST "implemented": true; SP1 *semantics* are implemented, activation is not — wording defect |
| 20 | "100% assessable" wording | qualified-OK | current docs tie it to the V1 assessable predicate; rebuild must keep the exact qualifier "under the frozen V1 prefix-map predicate" |
| 21 | Memory "peak memory" unlabeled basis | **contradiction** | three bases silently mixed: tracemalloc (1.01/7.23/68.65), committed 0.98 MB@1K run, and 2026-09-09 ru_maxrss probes (731.41/1447.04) — rebuild must label every memory number with its measurement method |
| 22 | pytest 9.0.2 (current) vs pytest 9.1.1 (2026-08-25 historical) | benign-historical | environment metadata in a self-dated historical report |

## 3. Cross-document contradictions (complete register)

1. **Two irreconcilable "fresh 2026-09-07" benchmark result sets** —
   FINAL_TEST_AND_FORENSIC_REPORT.md:259 & FINAL_IMPROVEMENT_REPORT.md:101
   (0.199/1.438/14.607 s) vs the committed artifact `evidence/benchmarks/benchmark.json`
   (0.207/1.494/15.325 s) quoted by four other documents. The 0.199 family is
   F — untraceable. → Rebuild directive: the new performance report must cite
   only hash-anchored artifacts generated in this pass.
2. **R3 semantics** — DATA_FLOW_MAP "R3 = R1 OR R2 [contract-exact]" vs
   code (independent predicate) vs fresh reports documenting the gap.
   → Rebuild directive: describe R3 exactly as implemented; mark the
   "R3 = R1∨R2" text as a company-document position, not code behavior.
3. **RBAC role count** — 3 (README) vs 4 (SECURITY.md + code).
   → Rebuild directive: 4 roles, cite `security/auth.py`.
4. **README shape claims stale** — addenda describe "H1 # Data Quality /
   exactly 30 sections / 0 V1-naming occurrences"; actual README (after commit
   0282e67) has H1 "Data Quality Platform V1", 21 H2 sections, 4 naming
   occurrences. → Rebuild directive: full README rebuild in this task makes
   the point moot; new counts must be measured, not narrated.
5. **HEAD/commit identity drift** — five different "current" commits across
   documents (a5ec759 / 5abca22 / 71a303e / (nothing) / 0282e67). → Rebuild:
   every rebuilt document states HEAD 0282e67b (or the final 5M-task commit,
   once made) with its role (baseline vs report commit).
6. **SP1 implementation status wording** (docs/ARCHITECTURE_MAP vs
   docs/DATA_FLOW_MAP). → Rebuild: both docs get a one-line historical banner;
   the authoritative SP1 statement lives in the new reports.
7. **"Largest ever = 100K"** — falsified by the 2026-09-09 probes and (if
   completed) the 5M run. → Rebuild: replaced by the new authoritative scale.
8. **Verification-matrix PARTIAL composition** changed under an identical
   "20 PASS / 2 PARTIAL" headline (Q18+Q19 vs Q18+Q21). → Rebuild: new matrix
   lists members explicitly.
9. **Memory metric basis silently mixed** (tracemalloc vs ru_maxrss vs
   unlabeled). → Rebuild: hard rule — every memory figure carries its
   measurement method inline.
10. **1K throughput across passes** (22,402 vs 4,841.5 rps, both "fresh").
    → Rebuild: single authoritative table from this pass; cross-pass variance
    mentioned only as methodology caveat.
11. **Allowlist size evolution** 59 (draft) vs 62 (delivered contract) — the
    59-code draft doc is self-labeled DRAFT-UNVERIFIED; keep, but new reports
    must not cite it as authority.
12. **HISTORY_INDEX test-count lineage** skips the documented 327 stage.
    → Fix line in the consistency phase (one-word-level edit, evidence-backed).
13. **pytest version metadata** differs across eras (9.1.1 vs 9.0.2) —
    historical only; new documents pin the measured version.
14. **`0cf6eb93…` identity** — audit-premise ("manifest hash") was contradicted;
    repo consistently treats it as the SP1 contract-document hash
    (COMPANY-SUPPLIED, not locally re-computable). Keep with E-class label.

## 4. Stale-as-current clusters requiring rebuild or banner

| Cluster | Files | Action in this task |
|---|---|---|
| Scale ceiling "100K largest ever" | README, BENCHMARK_REPORT | Superseded by new 5M/1M/100K evidence in rebuilt docs |
| Commit identity drift | COMPANY_ALIGNMENT, CROSS_REFERENCE, DELIVERY_MANIFEST.json, README | Supersession note + new authoritative value |
| README-shape narration | FINAL_TEST_AND_FORENSIC addenda, FINAL_IMPROVEMENT §H | Superseded by full README rebuild |
| docs/ stale wording (SP1, R3) | docs/ARCHITECTURE_MAP.md, docs/DATA_FLOW_MAP.md | Historical banner (doc-only change), authoritative text in new reports |
| Untraceable benchmark family | FINAL_TEST_AND_FORENSIC §28, FINAL_IMPROVEMENT §H | Marked superseded by new performance report (H-class evidence) |
| Mixed memory bases | BENCHMARK_REPORT, README, LIMITATIONS | New reports label every memory figure |

## 5. Claim-hygiene baseline carried into the rebuild

- Every numerical claim in the rebuilt documents must trace to
  `evidence/final_5m_execution/FINAL_RESULTS.json` or an explicitly cited
  artifact (per the taskbook).
- Historical reports remain in place untouched (they are evidence of their own
  era); the rebuilt documents carry the "current vs historical" distinction.
- Terminology set for the rebuild: PASS / PASS WITH LIMITATIONS / PARTIAL /
  COMPANY-GATED / BLOCKED / NOT IMPLEMENTED / NOT AUTHORIZED / NOT RUNTIME
  VERIFIED / NOT VERIFIED. Vague phrases are forbidden.
- Claim-strength labels A–F (this file) are carried into
  `docs/EVIDENCE_COVERAGE.md`.
