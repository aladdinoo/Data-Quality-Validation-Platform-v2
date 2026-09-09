# 5M RUN 1 — EXECUTION FAILED: ENVIRONMENT OOM (honest record)

Run: run_5m_r1 (the FIRST real 5M pipeline execution ever attempted in this repository)
Command: see command.txt (canonical CLI `python -m runner.cli validate`)
Result: **FAILED — the process was killed by the kernel OOM killer (SIGKILL, exit code -9)
after 185.307 s, at 4,943,922 of 5,000,000 output rows (98.9% complete).**

## Evidence chain (all captured, nothing reconstructed)

1. `terminal_output.txt` — captured stdout (empty; process killed before flushing),
   exit code -9, "TERMINATED BY SIGNAL 9 (SIGKILL — probable OOM)".
2. `oom_kernel_log.txt` — **kernel OOM killer record captured live from dmesg**:
   `oom-kill:constraint=CONSTRAINT_NONE,...,global_oom,task=python,pid=3565,uid=1001`
   `Out of memory: Killed process 3565 (python) total-vm:3678772kB, anon-rss:3592016kB,
   file-rss:7168kB, shmem-rss:0kB, UID:1001 ... oom_score_adj:0`
   → the CLI process reached **3,592,016 KiB (3,426 MiB) anonymous RSS** when killed.
3. `memory.txt` — two labeled measurement methods:
   RUSAGE_CHILDREN ru_maxrss = **3,612.96 MB** (this is the max over children of the
   harness, dominated by this run; VmHWM-polling observed 3,592.00 MB).
4. `runtime.txt` — start/end UTC, wall duration 185.307 s, MemAvailable before 3553.4 MB.
5. `result.json` — structured failure record, status FAILED_TERMINATED_BY_SIGNAL_9.
6. `hashes.txt` — input SHA-256 (44e41bb8…) and the partial output SHA-256.
7. `partial_output_record.txt` — the partial output file's measured row count and size.

## Why it died (pre-registered model, confirmed)

The Phase 0 baseline (`00_baseline/baseline_assessment.md`) projected a 5M peak RSS of
~3,594 MB from the measured 1M (731.41 MB) and 2M (1,447.04 MB) anchors
(marginal 715.63 MB per 1M rows), against 3,576 MB available RAM, no swap,
non-root environment. The attempt was pre-authorized in that document despite the
thin margin, because the task demands real execution. The kernel record
(anon-rss 3,592,016 KiB at kill) matches the projection within 0.1%.

Root cause (frozen V1 engine architecture, code inspection — see baseline):
`ValidationEngine.validate` accumulates O(N) memory: `id_set` (5M ID strings) and
`LineageRecorder.row_records` (one record per flag event; the frozen generator emits
a valid (state, zip) pair on every row, so `zip_state_assessable` fires on ~100% of
rows → ~2.256 events/row → ~11.28M record objects at 5M). This is documented engine
behavior (FINAL_SCALE_REPORT, benchmark.json note), not a defect introduced here.

## Remediation attempted / ruled out

- swap: NOT POSSIBLE (uid 1001, no CAP_SYS_ADMIN; swapon unavailable)
- zram/compression: NOT POSSIBLE (requires root)
- streaming-lineage variant of the engine: NOT ATTEMPTED — would require modifying
  frozen V1 production semantics (forbidden by the taskbook and by the delivery
  discipline of this repository)
- split into two 2.5M runs: NOT EQUIVALENT (not a single 5M run; id_set/reconciliation
  would be per-split) — rejected as misrepresentation

## Consequences recorded

- `05_run2/` for 5M: NOT EXECUTED (a second identical attempt would deterministically
  repeat the OOM; decision documented there).
- The pre-registered fallback governs: the complete dual-run protocol
  (Run 1 → independent verification → Run 2 → byte comparison) executes at the
  largest scale satisfying the pre-registered safety rule
  (peak RSS ≤ ~70% of total RAM = 2,829 MB → **3,000,000 rows**, projected 2,162 MB);
  see `11_largest_safe_execution_3m/`.
- The 5M DATASET itself is complete and forensically verified (02_dataset/):
  exactly 5,000,000 rows, SHA-256 44e41bb8cfe1c0d2fbafbff5e91bb40b100f8331ef26f946532b84c57409fb9d.
- Partial output deletion: the 1,415,583,267-byte partial output (4,943,923 lines incl.
  header, SHA-256 a15936b2bdcb46180cd550748e368da38e4a2a8aeefa9e96c905c24323eca7ae)
  was recorded and then deleted to free disk; deletion is justified because the run
  FAILED (the file is an incomplete scratch artifact, its identifying measurements
  are preserved in this record).
