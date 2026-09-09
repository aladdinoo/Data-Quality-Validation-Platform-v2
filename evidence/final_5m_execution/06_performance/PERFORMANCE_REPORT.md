# PERFORMANCE REPORT — FINAL 5M VALIDATION TASK
Captured: 2026-09-09 (all numbers from this pass; artifacts listed in §7)

## 0. Measurement methods (explicitly labeled — no unlabeled "RAM usage" anywhere)

| Symbol | Method | What it measures |
|---|---|---|
| **peak RSS** | `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` around the CLI child process (Linux KiB→MB); cross-checked in flagship runs by `/proc/<pid>/status` **VmHWM** 0.5 s polling | maximum resident set size of the whole process (Python interpreter, objects, buffers) |
| **tracemalloc peak** | `tracemalloc.get_traced_memory()` (repo's `scripts/benchmark.py`) | Python-object allocations only; EXCLUDES interpreter baseline; NOT comparable to peak RSS |
| duration | wall clock around the invoked CLI process | end-to-end validate duration (includes schema pass, rule pass, reconciliation pass, manifest) |

Every memory figure below carries its method inline. The 5M attempt (§5) also
captured the **kernel OOM record** — the only run in this pass that died.

## 1. Official ladder — real CLI runs, seed 20260909 (this pass)

| Rows | Validate duration (s) | Throughput (rows/s) | peak RSS (MB) | RSS per 1K rows (KB) |
|---|---|---|---|---|
| 1,000 | 0.187 | 5,343.8 | 22.43 | — |
| 10,000 | 0.566 | 17,680.1 | 28.91 | — |
| 100,000 | 4.471 | 22,365.8 | 93.87 | 715 |
| 1,000,000 | 45.917 | 21,778.5 | 735.71 | 713 |
| 3,000,000 (Run 1) | 138.472 | 21,664.1 | 2,192.27 | 731 |
| 3,000,000 (Run 2) | 140.466 | 21,357.6 | 2,195.82 | 732 |
| 5,000,000 | **FAILED at 185.307 s (98.9%)** | — (incomplete) | 3,592.0 at kill (kernel anon-rss) | — |

Small-size overhead note: 1K/10K durations include fixed interpreter/startup
and evidence-writing costs; throughput stabilizes at ~21,400–22,400 rows/s
from 100K upward.

## 2. tracemalloc continuity (repo's own benchmark script, this pass)

`evidence/final_5m_execution/06_performance/benchmark_tracemalloc_20260909.json`
(copy of the refreshed `evidence/benchmarks/benchmark.json`):

| Rows | Duration (s) | rows/s | tracemalloc peak (MB) |
|---|---|---|---|
| 1,000 | 0.209 | 4,791.7 | 1.00 |
| 10,000 | 1.471 | 6,799.2 | 7.23 |
| 100,000 | 14.941 | 6,692.9 | 68.65 |

tracemalloc per-row: 0.70 KB/row at 100K — matches the committed 2026-09-07
artifact family (68.65 MB). The historical "0.199/1.438/14.607 s" family from
the 2026-09-07 addenda remains untraceable (see REPORTING_FORENSIC_AUDIT
Contradiction 1) and is superseded by this pass's measurements.

## 3. Scaling interpretation (carefully separated claims)

- **Implementation-level O(N) behavior** — established by code inspection:
  `ValidationEngine.validate` is streaming per row, but total in-process
  memory is O(N) via `id_set` (one ID string per row) and
  `LineageRecorder.row_records` (one record object per flag event; ~2.256
  events/row with this frozen generator because `zip_state_assessable` fires
  on ~100% of rows). The engine docstring says exactly this; no O(1) claim
  exists anywhere.
- **Observed empirical scaling** — from the measurements above: throughput is
  approximately flat at scale (21,357–22,366 rows/s for 100K–3M) and peak RSS
  grows approximately linearly (~713–732 KB per 1K rows, RSS basis; 0.70
  KB/row, tracemalloc basis at 100K). The measurements are CONSISTENT with
  the inspection-based model; they do not by themselves prove O(N).
- **Memory model accuracy**: the pre-registered linear model
  (715.63 MB per 1M rows + 15.78 MB base, from 1M/2M probes) predicted the 3M
  peak at ~2,162 MB; measured 2,192/2,196 MB (+1.4%). It predicted 5M at
  ~3,594 MB; the kernel killed the run at 3,592,016 KiB anonymous RSS
  (+0.1% error). The model is validated within 1.5%.

## 4. Bottleneck / resource observations (this pass)

- CPU: single-process, single-threaded; 2 vCPU available; one core saturates
  during the streaming rule pass (per-row Python predicate evaluation).
- IO: sequential CSV read + write (~1.3 GB input at 3M); the run is CPU-bound
  rather than IO-bound (throughput flat across an order of magnitude of size
  while page cache is warm or cold).
- Memory: O(N) accumulators dominate at scale; at 3M the process peaked at
  ~2.19 GB (54% of the 4,041 MB total RAM) — safe; at 5M the same growth
  exceeds the ~3.55 GB available (no swap, non-root) → OOM kill (§5).
- The reconciliation pass (second full read of the output) is included in the
  durations; it is IO-streaming and adds no O(N) memory.

## 5. The 5,000,000-row attempt (honest failure record)

- Command: canonical CLI validate against the verified 5M dataset
  (`02_dataset/`, SHA-256 44e41bb8…).
- Outcome: kernel OOM killer terminated the process at 185.307 s,
  4,943,922/5,000,000 rows written (98.9%), `anon-rss: 3592016 kB`.
  Evidence: `03_run1/oom_kernel_log.txt` (live dmesg capture),
  `03_run1/EXECUTION_BLOCKED_SUMMARY.md`.
- Claim hygiene: 5M execution is reported as **FAILED — ENVIRONMENT OOM**;
  no throughput, no result status, and no output hash is claimed for 5M.

## 6. What this report does NOT claim

- No O(N) claim from measurements alone (separated in §3).
- No 5M throughput/memory/performance claims (run failed; §5).
- No 800M/721M-scale performance claims (company figures remain
  COMPANY-SUPPLIED / arithmetic-only).
- No constant-memory claim of any kind.

## 7. Evidence index

| Artifact | Path |
|---|---|
| Ladder (1K–1M) terminal captures | `06_performance/bench_<size>_generation_terminal.txt`, `bench_<size>_validation_terminal.txt` |
| Ladder machine-readable | `06_performance/bench_ladder.json` |
| Flagship 3M runs | `11_largest_safe_execution_3m/run1/`, `run2/` (result.json, runtime.txt, memory.txt, hashes.txt, terminal_output.txt, command.txt) |
| tracemalloc continuity | `06_performance/benchmark_tracemalloc_20260909.json`; prior artifact backup `benchmark_prior_20260907_backup.json` |
| 5M failure evidence | `03_run1/` (all files) |
| 1M/2M probes (pre-attempt feasibility anchors) | `00_baseline/feasibility_probe.txt`, `00_baseline/baseline_assessment.md` |
