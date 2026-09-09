5M RUN 2 — NOT EXECUTED (decision record)

Run 1 (03_run1/) was killed by the kernel OOM killer at 98.9% completion with
anon-rss 3,592,016 KiB against 3,576 MB available (dmesg evidence captured).
The failure mode is deterministic: the frozen engine allocates the same O(N)
structures on every run for the same input, and no swap/root is available.
A second 5M attempt would deterministically repeat the kill and waste ~3 minutes
plus ~1.3 GB of scratch disk. Decision: NOT EXECUTED, by pre-registered fallback
(00_baseline/baseline_assessment.md). The dual-run protocol (Run1+Run2+byte
comparison) was instead completed at 3,000,000 rows — see
11_largest_safe_execution_3m/ — which is the largest scale satisfying the
pre-registered safety rule (projected peak 2,162 MB <= 2,829 MB = 70% of RAM).
