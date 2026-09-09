# DOCUMENT CONSISTENCY REPORT
Task: FINAL 5M VALIDATION + PROFESSIONAL REPORTING REBUILD — Phase 17

Swept 10 current documents against FINAL_RESULTS.json with
negation-aware patterns; historical locations (reports/history/, dated
2026-09-05/06/07 root reports, bannered docs/) excluded from 'current'.

## Result

- **0 unexplained numerical contradictions**
- **0 unexplained status contradictions**
- **0 stale-current claims** in the swept current set

All checked values agree with FINAL_RESULTS.json across the current document set; all forbidden-claim patterns returned 0 hits (negation-aware); all stale-value patterns returned 0 hits in current docs. Historical documents retain their values under explicit historical labels/banners, which is the required presentation, not a contradiction.

## Method note

Negation-aware = a phrase is only flagged when no negation cue (not/never/
no/…) appears within the match's context window. Superseded-value checks
target the *current* set only; historical docs are allowed to carry their
era's numbers under labels — that is the required current-vs-historical
distinction, verified in README §13 (HISTORICAL / SUPERSEDED EVIDENCE).
