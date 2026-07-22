# Proposal: stabilize-django

## Why

The June–July 2026 modernization (Python 3.13, Django 1.11→5.2→6) left the app in a state where the actual deployment model — one laptop server plus ~10 weak LAN clients — no longer works (`ALLOWED_HOSTS=[]` now returns 400 for every LAN request), and a full-code audit surfaced defects that directly corrupt live competition results (untouched C-elements score as passed, B-score truncation, medal tie-break counting unjudged elements) plus unauthenticated endpoints that let anyone on the venue LAN mutate scores. These must be fixed before the planned Elixir rewrite, both to survive the next tournament and to pin down the correct scoring behavior the rewrite will port.

## What Changes

- Fix LAN deployment: `ALLOWED_HOSTS`, misplaced SQLite `OPTIONS` (busy-timeout silently ignored), WAL mode, self-hosted fonts (no render-blocking Google Fonts on an offline LAN), WhiteNoise so static/media survive `DEBUG=False`, env-var driven `SECRET_KEY`/`DEBUG`.
- Fix scoring correctness — **BREAKING** (scores can change vs. current behavior, per owner's decisions):
  - Judge C must mark every element before submitting; unmarked elements aggregate as abstention, never as "performed". Same rule applied to the medal tie-break counters.
  - `calculateB` generalized: a value repeated ≥2 times wins; otherwise trimmed mean `(sum − max − min)/(n − 2)` for n≥3. Identical results for the standard 4-judge panel.
  - B contribution rounded, not truncated (`int(B*100)` → `round`).
  - A legitimate 0.00 B-score counts as a submitted vote.
- Lock scoring behavior with golden tests on `Participation.get_scores` end-to-end and on the tie-break (`cmp`/`counts`) before touching the formulas.
- Access control: authentication + authorization on every mutating endpoint (`open_judge`, `delete_participation`, activation), all mutations become POST, `JudgeCSubmit` restricted to the judge's own `ElementStatus` rows, judge submits stop 500ing when no participant is active.
- Enforce the single-active-participant invariant at the database level (partial unique index on `state=DOING`).
- Data integrity: unique constraints on `Tablo(age,sex,category)`, `Participation(participant,tablo)`, `Score(judge,participation)`; `on_delete=PROTECT` on reference/history relations so competition history can't vanish via one admin delete.
- Replace the file-based monitor channel (HTML rendered into the templates directory + 1s polling with 100ms error retry) with Server-Sent Events push; monitor snapshots live in process memory.
- Fix crash/render bugs: unguarded country flag on `monitor_tablo`, `in_process` never passed to template, rank numbering skipping over unfinished rows, `CurrentParticipantScoreView` double-submit 500.
- Remove dead weight: `monitor/` app, legacy `tablo/models_py` + `models - копияpy`, `static__/`, selectize, jqBootstrapValidation (48K), bootstrap-table (72K), unrouted views (`JudgeScoreView`, `CounterView`), vestigial `gl_*` cache helpers, `seven_twelve`, `Country.thumbnail`, committed runtime artifacts (`showme*.html`, `file.count`).
- Fix hot-path N+1 (`get_scores` prefetch, tie-break sort).
- Secretary actions (activate, draw, monitor-push, reopen, delete) restricted to `is_staff`; monitor idle-screen branding moves to `EVENT_TITLE`/`EVENT_SUBTITLE` settings; the global-draw shell script becomes a transactional `manage.py jrebiy` command with per-tablo numbering.

Out of scope (deferred to the rewrite): championship/event entity, multi-carpet support, audit timestamps, printable protocol redesign, i18n overhaul, judge-management UI, per-B-judge reopen affordance.

## Capabilities

### New Capabilities

- `lan-deployment`: server reachable from LAN clients, fully offline-capable asset serving, SQLite configured for ~10 concurrent judge writers, safe settings management.
- `scoring-correctness`: the A/B/C aggregation and medal tie-break rules as decided by the owner, including completeness requirements on judge C input.
- `judging-access-control`: who may call which judging/administration endpoint, mutation semantics (POST-only), per-judge data ownership, and the single-active-participant invariant.
- `data-integrity`: database-level uniqueness and deletion-protection guarantees for competition data.
- `monitor-realtime`: push-based (SSE) monitor/projector channel replacing filesystem snapshots and polling.

### Modified Capabilities

_None — no specs exist yet; this change introduces the first specs._

## Impact

- **Code**: `ushu/settings.py`, `ushu/urls.py`, `tablo/views.py` (most views), `tablo/models.py` (scoring + constraints via migrations), `tablo/urls.py`, judge/monitor templates (POST forms, SSE client, CSRF), `core/templates/core/base.html` (fonts, dead JS), `requirements.txt` (add whitenoise; drop unused psycopg2-binary).
- **Schema**: new migrations for unique constraints, partial unique index on DOING, `on_delete=PROTECT`, dead-field removals. Existing data must be deduplicated before constraints apply (data migration).
- **Behavior**: recorded final scores may differ from the old system in the fixed edge cases; 4-judge B panels and fully-judged C cards produce identical results. Judge C UI gains a "mark everything first" gate.
- **Tests**: golden tests added first (regression net), then updated to the decided rules; existing `tablo/tests.py` locks that encode the old buggy behavior get updated deliberately.
- **Ops**: `.bat` launchers rewritten for the current runtime (waitress, correct paths); DEBUG no longer load-bearing.
