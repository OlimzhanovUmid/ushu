# Tasks — elixir-02-scoring-core

## 1. Structs and module skeleton

- [ ] 1.1 Create `elixir/lib/ushu/scoring/deduction.ex` — `%Deduction{code_id, value_c}` with `@enforce_keys`, `@type t`, `is_integer` guard on `value_c`; doctest showing construction
- [ ] 1.2 Create `elixir/lib/ushu/scoring/mark.ex` — `%Mark{element_id, position, verdict, score_c, landing}` with `verdict :: :pending | :performed | :failed` typespec and a `new/1` validating the verdict atom
- [ ] 1.3 Create `elixir/lib/ushu/scoring/b_score.ex` — `%BScore{base_c, deductions}` plus `effective/1`: `nil` when nothing entered, else `max(0, base_c − Σ value_c)`; doctests for nil / zero-vote / clamped cases
- [ ] 1.4 Create `elixir/lib/ushu/scoring/result.ex` — `%Result{a_agreed, a_score_c, b_values, b_score_c, c_agreed, c_score_c, bonus, final_c, complete?}` and `no_show/0` zero constructor
- [ ] 1.5 Create `elixir/lib/ushu/scoring.ex` facade with `@moduledoc` describing centi-point convention and rule provenance (stabilize-django scoring-correctness)

## 2. aggregate_a

- [ ] 2.1 Implement `aggregate_a/2` — consuming 2-of-3 majority keyed on `code_id` (recursive consume of judge-2/3 lists, then leftover judge-2 vs judge-3 pass), returning `{agreed, max − Σ}`
- [ ] 2.2 Implement `a_max/1` — `:adult -> 500`, other five buckets `-> 700`, guarded against unknown atoms
- [ ] 2.3 Tests `elixir/test/ushu/scoring/aggregate_a_test.exs` — golden cases: no agreement → {[], 700}; all three agree 150 → 550; two-of-three 200 → 500; judges 2+3 only 100 → 600; adult no-agreement → 500
- [ ] 2.4 Test one-to-one consumption: a judge reporting the same code twice pairs at most twice against the other judges' copies

## 3. aggregate_b

- [ ] 3.1 Implement `aggregate_b/1` — drop `nil` only; `Enum.frequencies/1`; repeated value wins with frequency ties → higher value; else trimmed mean `round((sum − max − min) / (n − 2))` for n ≥ 3, average for n == 2, passthrough for n == 1, 0 for empty
- [ ] 3.2 Doctests on `aggregate_b/1` covering repeated-wins and trimmed-mean branches
- [ ] 3.3 Tests `elixir/test/ushu/scoring/aggregate_b_test.exs` — golden: [950,950,970,980]→950; [950,950,980,980]→980; [940,950,960,970]→955; [700,900,800]→800; [800,800,900]→800; [850,850,850]→850; [940,960]→950; [930]→930; [nil,0,0]→0; [nil,nil]→0; []→0; [0,0,0]→0
- [ ] 3.4 Tests for `BScore.effective/1` — nil input → nil; base 0 → 0; base 50 − deduction 200 → 0 (clamped)

## 4. aggregate_c

- [ ] 4.1 Implement `aggregate_c/1` — strict equal-length zip of per-judge mark lists by position (raise on length mismatch), per-element decision: ≥2 `:performed` → agreed performed; ≥2 `:failed` → agreed failed + pool deduction; else excluded
- [ ] 4.2 Implement pools — movement 140 / landing 60, deduct by `landing` flag, `max(0, pool)` each, sum capped at 200; empty input → `{[], 0}`
- [ ] 4.3 Tests `elixir/test/ushu/scoring/aggregate_c_test.exs` — golden: all performed → 200; all failed movement 50 → 150; all failed landing 30 → 170; (:pending,:performed,:performed) → agreed performed, 200; (:pending,:failed,:failed) → agreed failed, 150; (:pending,:performed,:failed) → excluded, 200; (:pending,:pending,:performed) → excluded, 200; empty → {[], 0}
- [ ] 4.4 Test pool floor: failed elements totaling > 1.4 movement floor the pool at 0 rather than going negative

## 5. Assembly and tie-break

- [ ] 5.1 Implement `assemble/1` — takes per-panel inputs + `age_bucket` + `bonus` + `saved` flags, runs the three aggregators, `final_c = a + b(+5 if bonus) + c`, sets `complete?` (all saved), returns `%Result{}`
- [ ] 5.2 Wire `:no_show` → `Result.no_show/0` (all aggregates empty, `final_c: 0`, `complete?: false`)
- [ ] 5.3 Implement `tiebreak_counts/1` — fold agreed marks, filter `verdict: :performed and landing: false`, thresholds `score_c > 30 / > 20 / > 10` → `{e4, e3, e2}`
- [ ] 5.4 Implement `compare/2` over `{final_c, {e4, e3, e2}}` → `:gt | :eq | :lt`, final first then e4/e3/e2
- [ ] 5.5 Tests `elixir/test/ushu/scoring/assembly_test.exs` — golden end-to-end: A 600 + B 960 + C 200 → `final_c` 1760 (17.6); bonus → 1765 (17.65); B [957,959,940,970] → contribution 958, final 1758 (17.58); unsaved card → `complete?: false`; no-show → zeros
- [ ] 5.6 Tests `elixir/test/ushu/scoring/tiebreak_test.exs` — golden: performed movement 50 → {1,1,1}; pending → {0,0,0}; failed → {0,0,0}; performed landing → {0,0,0}; equal finals with {1,1,1} vs {0,0,0} → `:gt`; fully equal → `:eq`
- [ ] 5.7 Test the trimmed-mean rounding boundary (a .5-centi trimmed mean) locking Elixir `round/1` half-away-from-zero behavior as spec

## 6. Quality gates

- [ ] 6.1 Doctest coverage check — every public function in `Ushu.Scoring` and its structs has ≥ 1 doctest and all doctests run from the test files
- [ ] 6.2 `@spec` on every public function; `mix format --check-formatted` and `mix credo --strict` clean on all new files
- [ ] 6.3 Full suite green: `cd elixir && mix test` passes with the ported golden numbers exactly (no `assert_in_delta` on centi integers)
- [ ] 6.4 Cross-check the golden tally against Django: run `python manage.py test tablo.test_scoring_golden tablo.test_scoring_rules` and confirm every asserted number appears in the Elixir suite
