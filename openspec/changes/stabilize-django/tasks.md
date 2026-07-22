## 1. Golden tests (baseline, no behavior change)

- [x] 1.1 Characterization tests for `Participation.get_scores` end-to-end: full 3A/4B/3C panel, bonus, no-show sentinel (`FINISHED + finalscore==0`), exact final floats under CURRENT rules (incl. `int()` truncation)
- [x] 1.2 Characterization tests for ranking: `counts()` / `cmp()` / `sort()` — equal finals broken by e4/e3/e2, unfinished ordering, current `done==2` behavior
- [x] 1.3 Characterization tests for `calculateB` edge panel sizes (2 distinct → 0, 3 distinct → middle/2) marking them as to-be-changed
- [x] 1.4 Run full suite green; commit as regression baseline

## 2. Deployment / settings (lan-deployment)

- [x] 2.1 `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `EVENT_TITLE`, `EVENT_SUBTITLE` from environment with dev defaults; production env file next to launcher (not committed); rotate the committed key out of use
- [x] 2.2 Move `OPTIONS` inside `DATABASES['default']` with `timeout: 20`; enable WAL via `connection_created` signal; test asserting the option is applied to the connection
- [x] 2.3 Add WhiteNoise for static; serve media via explicit view gated on env; verify CSS/JS/flags with `DEBUG=0`
- [x] 2.4 Self-host fonts: external Google Fonts links removed from `base.html`, `login.html`, `monitor.html`; CSS falls back to the existing system font stack (offline LAN cannot fetch woff2; vendor Inter when online)
- [x] 2.5 Rewrite launchers (`start.bat`/`debug.bat`/`migrate.bat`/`shell.bat`) for current runtime: venv python, waitress with `--threads=16`, env vars, correct paths; `DEPLOY.md` documents WAL-aware backup (copy db+wal+shm or checkpoint)
- [x] 2.6 `git rm --cached db.sqlite3 backup.sqlite3`; `.gitignore` covers them + wal/shm + `.venv*/`; removed broken `idea/` line
- [x] 2.7 LAN smoke test: `DEBUG=0` waitress, fake LAN host → 200, static + media 200, disallowed host → 400, no external requests

## 3. Scoring correctness (scoring-correctness)

- [x] 3.1 `get_b_score`: return `None` for no-input, keep 0.00 as real vote, clamp negatives to 0; update aggregation to filter `is not None`
- [x] 3.2 Rewrite `calculateB` per D2 (repeated value wins with high-tie-break; trimmed mean /(n−2); n==2 average; n==1 identity); update locked tests to new spec, assert 4-judge parity with old formula
- [x] 3.3 Replace `int(B*100)` with `round()`; end-to-end test for the 9.58 artifact
- [x] 3.4 `calculateC`: treat `done==2` as abstention (2-of-N majority over real votes; no-majority → no deduction, not performed); `zip(*)` handles any panel size without the positional-unpack crash
- [x] 3.5 `counts()` tie-break: count only `done==1` elements; update ranking tests
- [x] 3.6 `JudgeCSubmit`: server-side completeness gate — reject save while own elements have `done==2`, message shown; removed the `done==2`-reopens-card hack *(client disable-until-marked deferred to Group 6 template pass)*
- [x] 3.7 New-spec tests for all of the above written from the spec scenarios; full suite green

## 4. Access control & mutation safety (judging-access-control)

- [x] 4.1 Shared `get_current_participation()` helper (safe `None`); replaced all `filter(state=PS_DOING)[0]` call sites
- [x] 4.2 Judge submits (A/B/C): handle no-active-participation with redirect + message; replaced `except: pass` with validation feedback (invalid error-code ranges, unparseable B score)
- [x] 4.3 `JudgeCSubmit`: ownership filter — only `ElementStatus` rows reachable from this judge's own Score for the current participation
- [x] 4.4 `open_judge`: require `is_staff`, convert to POST; `scores.html` links → `formaction` submit buttons
- [x] 4.5 `delete_participation`: POST + confirmation dialog in `tablo_detail.html`
- [x] 4.6 Activation: POST, `is_staff`-restricted, guarded transition WAITING→DOING inside transaction, friendly failure when another is DOING or state ≠ WAITING
- [x] 4.6b Draw (`JrebiView`) and monitor-push (`TabloMonitorView`, score/current POST) actions: `is_staff`-restricted
- [x] 4.7 `has_updated`: `login_required` returning `JsonResponse` (no AnonymousUser crash); judge templates use `{% url %}` for polling endpoints *(judge poll-URL fix in Group 6 template pass)*
- [x] 4.8 View tests: anonymous/wrong-role rejection for every mutating endpoint, forged-pk (IDOR) rejection, double-activation, submit-after-finalize
- [x] 4.9 (found during 4.8) migration `0012` repairs the SQLite `ElementStatus.done` column type — fresh installs declared it boolean, collapsing `done=2` to 0 and breaking the C tri-state

## 5. Data integrity (data-integrity)

- [x] 5.1 Data migration: dedupe `Tablo(age,sex,category)`, `Participation(participant,tablo)`, `Score(judge,participation)` (keep lowest pk) + demote extra DOING rows; rehearsed on a copy of the real `db.sqlite3` (applied clean)
- [x] 5.2 `UniqueConstraint`s for the three tuples + partial unique `one_doing` on `state=DOING`
- [x] 5.3 `on_delete=PROTECT`: Score→judge, ElementStatus→element, WrapperErrorCode→error_code, Club→country, Participant→club
- [x] 5.4 `assign_participation`: add `is_active=True` filter; test with deactivated judge
- [x] 5.5 Admin: help text on the judge Permissions fieldset (deactivate, don't delete); ProtectedError verified in tests (not a 500)

## 6. Monitor SSE (monitor-realtime)

- [x] 6.1 `MonitorState` module (`tablo/monitor_state.py`): thread-safe snapshot (pages list + revision), atomic swap, condition-based wakeup
- [x] 6.2 Publishers: activation, score-monitor button, `TabloMonitorView` render pages fully then publish (render failure keeps previous snapshot); flag image guarded in `monitor_tablo.html`
- [x] 6.3 `GET /monitor/stream`: `StreamingHttpResponse` SSE — initial snapshot, push on revision change, 15s keepalive comments, `retry: 3000`
- [x] 6.4 Monitor client: replaced polling JS with `EventSource`; removed 100ms retry loop, full-HTML diff, and the stray `style.js` space-key mutator
- [x] 6.4b Idle screen renders `EVENT_TITLE`/`EVENT_SUBTITLE` from settings (Uzbek strings as defaults)
- [x] 6.5 Removed `render_to_file`, `MONITOR_FL_COUNT`, `showme_view`, `ShowmeView`, `CounterView`; deleted committed `showme*.html` + `file.count`
- [x] 6.6 Fixed `tablo_detail.html`: `in_process` passed into context, computed `p.rank` (finished-only numbering) instead of `forloop.counter`
- [x] 6.7 `CurrentParticipantScoreView`: no-active → friendly redirect, POST double-submit safe (Group 4)
- [x] 6.8 Render-walk (mechanical): SSE stream delivers snapshots (test), flagless country renders safely (test), live waitress serves the monitor page + `text/event-stream` with `retry`. Full browser multi-client walk not run (no browser tool in this environment)
- [x] 6.9 Judge poll endpoints use `{% url "has_updated" %}` (was relative), satisfying the URL-restructure requirement

## 7. Cleanup & performance

- [x] 7.1 Deleted dead code: `monitor/` app, `tablo/models_py`, `tablo/models - копияpy`, `JudgeScoreView`, `CounterView`, `gl_*` cache helpers (kept the DB query as `judge_has_pending_score`), `request.iterator` vestige, `sex.translate('en')` no-ops
- [x] 7.2 Deleted dead assets: `static__/`, selectize bundle, jqBootstrapValidation + bootstrap-table (sources, collected copies, and `<script>`/`<link>` includes); collectstatic verified
- [x] 7.3 Removed `seven_twelve` field + `Country.thumbnail` (migrations `elements/0005`, `clubs/0005`); dropped redundant `delete_tablo` signal; dropped `psycopg2-binary` from requirements
- [x] 7.4 `get_scores` prefetch (`cclass__statuses__element`, `aclass__error_code`, `berrors__error_code`) + per-instance memoization (kills the O(n log n) re-query in the ranking sort); query-count test asserts a fixed 8 regardless of panel size
- [x] 7.5 Replaced `jrebiy.py` + `jrebiy_hammasiga.bat` with `manage.py jrebiy`: single transaction, per-tablo numbering, skips `started=True` unless `--force`; tests for draw / skip / force
- [x] 7.6 Full suite (91) green; `manage.py check --deploy` clean except the 4 accepted HTTPS warnings (plain-HTTP LAN); final `DEBUG=0` LAN smoke all 200/302, SSE streams, dead assets 404
