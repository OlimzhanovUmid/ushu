# Design: stabilize-django

## Context

Django 6 / Python 3.14 app, one waitress process (4 threads) on one laptop, ~10 browser clients on an offline venue LAN, SQLite. A full audit (July 2026) found: LAN deployment broken post-upgrade (`ALLOWED_HOSTS`), scoring defects that change results, unauthenticated mutation endpoints, no DB-level invariants, and a monitor channel built on rendering HTML into the templates directory. This change stabilizes the current stack; an Elixir rewrite follows later, so every scoring decision fixed here doubles as the rewrite's spec. Owner decisions (2026-07-12): judge C must mark all elements (unmarked = abstention); B aggregation generalized (repeated value wins, else trimmed mean over n−2); monitor moves to SSE.

## Goals / Non-Goals

**Goals:**
- Next tournament runs on this codebase without 400s, 500s, lock errors, or score corruption.
- Scoring rules pinned by tests = executable spec for the rewrite.
- Every mutation authenticated, authorized, POSTed, and race-safe.
- Repo hygiene: dead code and runtime artifacts gone.

**Non-Goals:**
- No new features (championship entity, multi-carpet, audit log, printable protocol, judge CRUD, i18n overhaul — all deferred to the rewrite).
- No UI redesign beyond what fixes require (POST forms, confirmation, C-completeness gate, SSE client).
- No database engine change; SQLite stays.
- No multi-process serving; single waitress process remains the supported topology.

## Decisions

### D1. Golden tests BEFORE formula changes
Write characterization tests for `get_scores` end-to-end and `cmp`/`counts` against current behavior first, commit them, then change formulas and update the deliberately-changed assertions in the same commit as the fix. Rationale: the diff of test expectations IS the record of intentional behavior change (there are already tests locking bugs, e.g. `test_three_distinct_no_majority`). Alternative — write only new-spec tests — loses the before/after evidence.

### D2. B aggregation (owner decision)
`calculateB`: filter to *submitted* scores (see D3), then (a) if any value occurs ≥2 times → most common value, ties broken by the higher value; (b) else n≥3 → `(sum − max − min)/(n − 2)`; (c) n==2 → average (was: 0); (d) n==1 → that score; (e) n==0 → 0. Preserves 4-judge results exactly; kills the parity heuristic. Deductions/bonus flow unchanged.

### D3. "Submitted" B score ≠ falsy
`get_b_score` must distinguish "no input" from 0.00. Return `None` only when the judge saved nothing (`bclass is None` and no berrors); aggregation filters `is not None` instead of truthiness. Negative effective scores clamp to 0.

### D4. C completeness enforced server-side, helped client-side
Server: `JudgeCSubmit` rejects (re-renders card with unmarked elements highlighted) if any own `ElementStatus.done == 2`; `saved=True` unreachable otherwise. Client: submit button disabled until cursor covers all elements (existing counter logic). Aggregation (`calculateC`) treats 2 as abstention: majority over real votes; (2,1,0)/(2,2,x) → excluded from deductions AND from tie-break "performed" counts (`counts()` filters `done == 1` explicitly). The done==2-keeps-card-open trick ("fill again") is replaced by the explicit completeness gate.

### D5. Single-DOING invariant: partial unique index + guarded transition
`Participation` gets `UniqueConstraint(fields=['state'], condition=Q(state=PS_DOING), name='one_doing')`. Activation becomes `POST`, runs `UPDATE ... SET state=DOING WHERE pk=? AND state=WAITING` inside a transaction; IntegrityError/0-rows → user-visible message. Consumers replace `filter(state=PS_DOING)[0]` with a `get_current_participation()` helper returning `None` safely. Alternative considered — advisory in-app mutex — rejected: DB constraint survives restarts and races.

### D6. SSE via StreamingHttpResponse, snapshot registry in memory
A module-level `MonitorState` (thread-safe: snapshot swap under a lock, condition/event for wakeup) holds the latest rendered pages + revision. Publishers (`activate`, `monitor` button, `TabloMonitorView`) render pages fully, then swap atomically; render failure = no publish. `GET /monitor/stream` is a `StreamingHttpResponse(text/event-stream)` that emits the current snapshot, then blocks on the condition with a 15s keepalive comment. Monitor JS = `EventSource` with `retry: 2000`. Works because waitress is one process with a thread per connection; document thread-pool sizing (monitors ≤ handful; raise waitress `threads` to cover streams + requests). Judge screens keep short polling (5s/2s) — 10 clients ÷ 5s is trivial — only the URL becomes `{% url %}`-reversed; converting judges to SSE is optional stretch, not required. Alternatives: django-channels/ASGI — rejected as oversized for one process; polling+memory — rejected by owner (SSE chosen).

### D7. Country flag guard
`monitor_tablo.html` gets the same `{% if %}` guard as the other monitor templates; plus publisher-side render-then-swap (D6) makes any residual template error non-destructive.

### D8. Constraints + PROTECT with data migration first
Order: (1) data migration deduping `Tablo`/`Participation`/`Score` (keep lowest pk, merge nothing — duplicates are junk rows), (2) `UniqueConstraint`s, (3) `on_delete=PROTECT` on: Score→judge, ElementStatus→element, WrapperErrorCode→error_code, Club→country, Participant→club. Participation→participant/tablo and Score→participation stay CASCADE (deleting a participation legitimately deletes its scores — that's the delete_participation flow). `assign_participation` adds `is_active=True` filter.

### D9. Settings via environment
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` from `os.environ` with dev defaults (`DEBUG=1` default true for dev; production launcher sets `DEBUG=0`, `ALLOWED_HOSTS=*`). Rotate key: new random default generated per deployment (env file next to the launcher, not committed). WhiteNoise added for static; media served via explicit `re_path` + `django.views.static.serve` gated on a `SERVE_MEDIA` env (acceptable for LAN scale) — keeps flags working with DEBUG off without adding a reverse proxy. `OPTIONS` moved inside `default` with `timeout: 20` + `init_command` enabling WAL (`PRAGMA journal_mode=WAL`) via connection signal.

### D10. Dead code removal is mechanical and last
Delete: `monitor/` app dir, `tablo/models_py`, `tablo/models - копияpy`, `static__/`, selectize assets, jqBootstrapValidation + bootstrap-table includes and files, `JudgeScoreView`, `CounterView`, `gl_*` cache helpers (keep the DB-querying `gl_has_active_participant`, renamed), `request.iterator` vestige, `seven_twelve` field, `Country.thumbnail` field (migrations), committed `showme*.html`/`file.count`, stale error-swallowing `except: pass` blocks (replaced by validation per access-control spec). Git-tracked `db.sqlite3` stops being tracked (`git rm --cached`), stays on disk.

### D11. N+1 fixes scoped to hot paths only
`get_scores`: `prefetch_related('cclass__statuses__element', 'aclass__error_code', 'berrors__error_code')`. Ranking: prefetch participations with scores before `sort()`. No broader ORM tuning — rewrite territory.

## Risks / Trade-offs

- [Changed scores vs. history] Fixed rules mean some past inputs produce different outputs → golden-test diff documents every intentional change; owner signed off on the three rule decisions.
- [SSE holds a waitress thread per monitor] Thread starvation if many monitors connect → raise `--threads` in launcher (e.g. 16), document monitor count assumption (≤4), keepalive detects dead streams.
- [Partial unique index on SQLite] Supported (SQLite ≥3.8, Django `UniqueConstraint(condition=...)`) but the dedup migration must run on real tournament DBs → migration is idempotent and logged; test on a copy of `db.sqlite3` first.
- [PROTECT breaks admin habits] Admins used to deleting judges/elements will hit errors → admin help text; deactivation documented as the path.
- [C completeness gate slows judges] A judge must now mark everything → this is the owner's chosen rule; UI highlights remaining elements to keep it fast.
- [WAL leaves -wal/-shm files] Backup procedure must copy all three or checkpoint first → document in launcher README.

## Migration Plan

1. Land golden tests (no behavior change) → green baseline.
2. Settings/deployment fixes (D9, WAL, WhiteNoise, fonts) — verifiable by `DEBUG=0` smoke run over LAN.
3. Scoring fixes (D2–D4) with test updates in the same commits.
4. Access control + single-DOING (D5) with view tests.
5. Schema migrations (D8) — run against a copy of the real DB, then the real one.
6. SSE monitor (D6, D7); remove file pub/sub.
7. Dead code sweep (D10), N+1 (D11), launcher `.bat`/`.sh` rewrite.
Rollback: each step is an independent commit; schema step ships with a reverse migration (constraints dropped, PROTECT→CASCADE); pre-migration DB copy retained.

## Resolved Questions (owner, 2026-07-12)

- **Secretary role**: activation, draw, and monitor-push require `is_staff`. No new role in this change — a dedicated secretary gets the `is_staff` flag in admin. Save/reopen stays `is_staff` too (same person or main judge).
- **Idle-screen branding**: moves to settings — `EVENT_TITLE` / `EVENT_SUBTITLE` read from environment (same env file as D9), rendered by `monitor.html` instead of the hardcoded Uzbek strings.
- **Global draw**: `jrebiy.py` + `jrebiy_hammasiga.bat` are replaced by a `manage.py jrebiy` management command — one transaction, numbering *per tablo* (consistent with `JrebiView`), refuses to run for tablos that already `started` unless `--force`. Old script and .bat deleted.
