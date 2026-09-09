# PHASE 0 — BASELINE ASSESSMENT (FINAL 5M VALIDATION)

Captured: 2026-09-09T15:21:48.236791+00:00 (probe measurements updated same day, see below)

## Verdict at baseline

- Repository: /home/z/my-project/Data-Quality-V1-Final-Company-Integrated
- HEAD/branch: see git_state.txt (`0282e67bf1212b188915973b9449e09bcd22a11b` on `main`).
- Working tree: mode-only deltas (0 content rows in `git diff --numstat`);
  filesystem-mount artifacts documented since FINAL-CONSOLIDATION; NOT code changes.
- Prior claimed 2M evidence: DOES NOT EXIST (proven in FINAL-2M-EVIDENCE-RECHECK).
- Prior claimed 3M evidence: DOES NOT EXIST (the 3M taskbook was superseded by
  this 5M taskbook before any 3M execution; directory check above confirms).
- Therefore the NEW 5M run becomes the largest and the authoritative execution
  ever performed in this repository (if it completes).

## Environment constraints (measured)

- RAM (free -m): total 4041 MB, available 3576 MB, Swap 0. NOTE: the earlier
  `free -g` display truncated 4041 MB to "3"; the megabyte reading is authoritative.
- Swap cannot be added: uid 1001 (non-root), swapon unavailable.
- Disk free: ~8.6 GB at probe time.
- Prior benchmark telemetry (tracemalloc, object-level): 100K rows → 68.65 MB.

## Feasibility probes (empirical, measured — real engine, real data)

Measurement method: `resource.getrusage(RUSAGE_SELF).ru_maxrss` (Linux KiB → MB),
i.e. process peak resident set size (VmHWM-equivalent). NOT tracemalloc.

| Probe | Rows | Phase | Duration (s) | Peak RSS (MB) |
|---|---|---|---|---|
| probe_1m (seed 20260909) | 1,000,000 | generation | 25.34 | 20.00 |
| probe_1m | 1,000,000 | validation | 47.03 | 731.41 |
| probe_2m (seed 20260909) | 2,000,000 | generation | 49.60 | 13.85 |
| probe_2m | 2,000,000 | validation | 95.67 | 1447.04 |

Both probes returned success=True with in==out==N and the deterministic flag
pattern (e.g. 2M: email_blank=160000, email_syntax_failure=140000,
proposed_email_export_eligible=1700000, zip_state_assessable=2000000,
geography_mismatch_candidate=99386, first_name_cleaning_candidate=211548,
last_name_cleaning_candidate=140296, name_cleaning_candidate=60674).

### Linear memory model (measured)

- Marginal validation cost: 1447.04 − 731.41 = **715.63 MB per 1M rows**.
- Interpreter/process base: 731.41 − 715.63 = **15.78 MB**.
- Projected 5M validation peak: 15.78 + 5 × 715.63 = **3593.9 MB**, plus a
  transient id-set resize spike (id_set crosses the 2^23-slot boundary near
  4.2M rows) → realistic worst case ≈ **3.6–3.7 GB**.
- Available RAM: **3576 MB**. No swap. Non-root.

### Generation feasibility

Generation is streaming: 1M in 25.3 s at 20 MB peak RSS → 5M generation is
SAFE (projected ~130 s, < 50 MB peak RSS, ~1.31 GB input CSV on disk).

### DECISION (recorded before execution)

1. The 5,000,000-row dataset WILL be generated and forensically verified —
   generation is streaming and safe.
2. The 5M pipeline execution WILL BE ATTEMPTED through the real CLI. The
   projection (~3.59–3.7 GB) is within measurement noise of available RAM
   (3576 MB): the attempt is justified because the outcome is genuinely
   uncertain and the task demands real execution. A failure would be captured
   as honest evidence (exit code / SIGKILL), never hidden.
3. If the attempt is killed by the OOM killer, the result is recorded as
   `5M EXECUTION FAILED — ENVIRONMENT OOM` and everything else in this task
   continues with honest labels (largest completed execution becomes the
   flagship).

## Pipeline memory architecture (from code inspection — D-class static evidence)

- `ValidationEngine.validate` streams rows via csv.DictReader/DictWriter.
- O(N) accumulators: `id_set` (unique input IDs); `LineageRecorder.row_records`
  (all flagged-row events; 1000-cap applies only at persist time,
  recorder.py:174 — the full list lives in memory during the run).
  Because the frozen generator always emits a valid (state, zip) pair,
  `zip_state_assessable` fires on ~100% of rows → ~2.256 lineage events per
  row → ~11.28M events at 5M rows. This is the dominant memory term.
- Bounded: flag_counts (8), blank_counts (33), row_lineage_buffer (<=100),
  audit events (run-level), schema validation (header-only).
- Generator `SyntheticDataGenerator.generate` streams rows; defect pattern is
  `defect_modes[i % 100]` (deterministic, frozen V1 behavior).

## Baseline discipline confirmations

- No production semantics will be modified for the 5M run.
- SP1 remains isolated/unregistered; E1 not implemented; ClickHouse untouched.
- All terminal outputs in this evidence tree are captured from real executions.
- Probe files (data/generated/probe_1m*.csv, probe_2m*.csv) are measurement
  artifacts; they will be removed before final packaging, with their
  measurements retained in this file and in 06_performance/.
