# elixir-02-scoring-core

## Why

The scoring rules (A/B/C aggregation, final assembly, medal tie-break) are the
correctness heart of ushu; porting them first as a pure, database-free Elixir
module lets every later layer build on a fully tested core whose numbers are
locked to the Django golden tests.

## What Changes

- New pure module namespace `Ushu.Scoring` inside the `elixir/` Phoenix app
  created by `elixir-01-foundation` — no Repo, no Ecto, no process state; only
  functions over plain structs.
- Input structs: `Ushu.Scoring.Deduction` (an A/B error code reference with its
  value), `Ushu.Scoring.BScore` (a B judge's base score plus deductions),
  `Ushu.Scoring.Mark` (a C judge's per-element verdict `:pending | :performed |
  :failed` with element score and landing flag).
- `aggregate_a/2` — 2-of-3 consumption-majority over A judges' error lists,
  age-dependent maximum (700 centi-points, 500 for `:adult`).
- `aggregate_b/1` — repeated-value-wins (count ties break to the higher value),
  otherwise trimmed mean `(sum − max − min) / (n − 2)`; `nil` (no submission)
  is dropped, a real zero is a vote; panel-size independent.
- `aggregate_c/1` — 2-of-N real-vote majority per element, `:pending` counts as
  abstention and never as performed; failed elements deduct from the movement
  (1.40) or landing (0.60) pool, pools floor at 0, sum capped at 2.00.
- `assemble/1` — final score in integer centi-points (A + B + C), bonus adds
  +5 centi-points to the B contribution, B aggregate is rounded (never
  truncated) into centi-points; zeroed result for `:no_show`.
- Tie-break: `tiebreak_counts/1` (e4/e3/e2 counters over agreed **performed
  movement** elements with score > 0.30 / > 0.20 / > 0.10) and `compare/2`
  for equal-final ranking.
- ExUnit test suite reproducing, number for number, the Django golden cases
  from `tablo/test_scoring_golden.py`, `tablo/test_scoring_rules.py` and the
  pure-method cases in `tablo/tests.py`; doctests on every public function.

## Capabilities

### New Capabilities

- `scoring-aggregation`: pure A/B/C panel aggregation — input structs, 2-of-3
  error majority with age-dependent maximum, panel-size-independent B rule,
  C majority with abstentions and capped pools.
- `scoring-final-assembly`: final score assembly in integer centi-points with
  bonus and rounding, the no-show zero result, and the e4/e3/e2 medal
  tie-break counters and comparison.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- Layer 2 of 7 in the Elixir rewrite sequence. Depends on
  `elixir-01-foundation` (project skeleton, test tooling). Depended on by
  `elixir-04-contexts`, which loads persisted scores via the schemas from
  `elixir-03-ecto-schema`, maps them to these structs and calls this module;
  and indirectly by `elixir-06-liveview-ui`, which renders `Result` values.
- Files: `elixir/lib/ushu/scoring.ex`, `elixir/lib/ushu/scoring/*.ex`,
  `elixir/test/ushu/scoring/*_test.exs`. No migrations, no runtime config,
  no supervision-tree changes.
- The Django app is untouched; this module is behavior-locked against its
  test suite.
