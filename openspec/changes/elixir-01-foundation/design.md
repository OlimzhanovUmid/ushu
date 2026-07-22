# Design — elixir-01-foundation

## Context

ushu is a live wushu-competition judging system deployed on one laptop serving ~10 weak browser clients over an offline venue LAN. The Django 6 app was recently stabilized (`openspec/changes/stabilize-django/`) and its business rules pinned; the owner is rewriting it in Elixir/Phoenix while learning the stack (Kotlin/Spring background). This is layer 1 of 7: the project skeleton. Everything here is infrastructure — the goal is that layers 02–07 only ever ADD code, never revisit tooling/config decisions.

## Goals / Non-Goals

**Goals**

- A committed, boot-able Phoenix project under `elixir/` with green `mix test`, `mix format --check-formatted`, `mix credo --strict`.
- The env-var contract (`USHU_*`) and SQLite pragmas fixed once, matching the Django deployment's operational shape (port 8081, WAL, 20 s busy timeout, offline assets).
- Gettext ru/en scaffolding so no later layer ships untranslatable strings.

**Non-Goals**

- No domain code: no schemas, no scoring, no auth (`phx.gen.auth` runs in `elixir-03` — schema/context generation — with UI adaptation in `elixir-06`), no LiveViews beyond the generated placeholder, no PubSub topics (05), no release packaging or Windows launcher (07).
- No multi-carpet, championships archive, or online entries (out of scope for the whole rewrite).

## Decisions

**D1 — `elixir/` subdirectory of the existing repo, not a new repo.**
The Django app must keep running until `elixir-07-cutover`; keeping both in one repo lets the importer (07) and the pinned openspec rules reference each other directly, and history stays in one place. *Alternative:* separate repo — rejected: complicates the cutover diffing and the openspec cross-references for a single-owner project.

**D2 — `mix phx.new ushu --database sqlite3 --no-mailer`, LiveDashboard kept.**
`--database sqlite3` pulls `ecto_sqlite3` and generates the right Repo/adapter wiring. `--no-mailer`: there are no email flows at all — auth is username+password on an offline LAN (fixed architecture decision), so Swoosh is dead weight and one less dep to explain. LiveDashboard is KEPT: it costs nothing at runtime in prod (route it dev-only, or behind admin later), has zero external dependencies (works offline), and is a first-class learning tool for the owner — live view of the supervision tree, ETS, processes, telemetry on the very laptop running the event. *Alternatives:* `--no-dashboard` — rejected for its diagnostic value on a one-laptop deploy; `--no-assets`/`--no-html` — rejected, layer 06 needs the full HTML/asset pipeline.

**D3 — SQLite (WAL) stays; Postgres rejected.**
Fixed architecture decision, but restated: one laptop, zero ops burden, file-copy backups, trivial import from the Django SQLite DB with preserved integer ids. Write volume is tiny (≤ 10 judges submitting scorecards); WAL lets the monitor/standings readers proceed while a judge write is in flight. Postgres would add a service to install/start/monitor on a Windows venue laptop for no measurable benefit. *Alternative:* Postgres — rejected on ops grounds; revisit only if multi-carpet ever becomes real.

**D4 — Pragmas pinned in config: `journal_mode: :wal`, `busy_timeout: 20_000`, foreign keys ON, pool ≤ 5.**
`ecto_sqlite3` has reasonable defaults, but the Django stabilization was bitten by a misplaced-options bug (timeout configured but not applied), so we pin them EXPLICITLY and add a pragma-inspection regression test. 20 s matches the pinned `lan-deployment` rule ("two judges submit simultaneously → second waits, not `database is locked`"). Small pool because SQLite has one writer; a big pool just queues inside the DB instead of in Ecto.

**D5 — Single OTP app, no umbrella.**
One deployable, one supervision tree, one team member. Context modules (`Ushu.Scoring`, `Ushu.Competition`, …) give all the modularity needed. *Alternative:* umbrella app — rejected: adds path/config ceremony that solves a problem (independent releases) we don't have.

**D6 — Env-var contract mirrors Django (`USHU_*`), defaults mirror Django values.**
The venue operator already knows `USHU_SECRET_KEY`/`USHU_EVENT_TITLE`; the Elixir app keeps the prefix and semantics (`USHU_SECRET_KEY_BASE` — Phoenix's name for the secret, `USHU_PORT` default 8081, `USHU_DB_PATH`, `USHU_EVENT_TITLE`, `USHU_EVENT_SUBTITLE`). Branding lands in `Application.get_env(:ushu, :event)` — the read-side contract for `elixir-06-liveview-ui` (monitor/print headers). Prod raises on missing secret (fail fast at config time, before the endpoint binds). *Alternative:* config file on disk — rejected; env vars compose with the Windows launcher exactly like the Django `start.bat` does today.

**D7 — Strict compile-time vs runtime split.**
Rule: if two venues running the SAME release binary could need different values, it goes in `runtime.exs`; otherwise it may live in `config/*.exs`. This is the single most common Elixir-deployment mistake for newcomers (config.exs is evaluated at COMPILE time), so the foundation encodes the rule and the explainer teaches it.

**D8 — `check_origin: false`, bind `0.0.0.0`.**
Clients connect by whatever LAN IP the laptop got from the venue router; origin checking against a configured host list would reproduce Django's `DisallowedHost` failure mode with zero security benefit on an air-gapped LAN. *Alternative:* enumerate origins via env — rejected: operationally fragile at a venue, protects against nothing there.

**D9 — Tooling: `mix format` + Credo strict; Dialyzer deferred.**
Format + Credo are fast, zero-config gates that CI-of-one (the owner) will actually run. Dialyzer/dialyxir is valuable but its PLT build time and noise are a poor trade while learning; noted as a possible later addition. *Alternative:* Styler — unnecessary on a greenfield tree that starts formatted.

**D10 — Bandit as the HTTP server (generator default).**
Pure-Elixir, the Phoenix 1.8 default, one fewer C dependency to build on Windows. *Alternative:* Cowboy — no advantage for this workload.

## Risks / Trade-offs

- [SQLite single-writer stalls under a burst of judge submits] → WAL + 20 s busy timeout + small pool; write transactions in later layers kept short (Ecto.Multi, no long transactions); load is ≤ 10 humans.
- [esbuild/tailwind binaries are downloaded on first `mix assets.setup` — venue has no internet] → binaries are fetched at development/build time and cached; `elixir-07` ships prebuilt assets inside the release. Document "never first-build at the venue".
- [`check_origin: false` would be unsafe on a public network] → deployment is an offline LAN by definition; revisit only if the deployment model changes (noted for 07's checklist).
- [Version drift between the owner's machines] → `mix.lock` committed; `.tool-versions` (Elixir 1.18.x / OTP 27) committed for asdf/mise.
- [Keeping LiveDashboard could leak internals if exposed] → dev-only route now; if kept in prod later, gate behind the admin role from `elixir-04`.

## Migration Plan

None needed — this change only creates `elixir/`; the Django app is untouched and remains the production system until `elixir-07-cutover`.

## Open Questions

- Should `USHU_PORT` default differ from Django's 8081 so both can run side-by-side during the transition? **Default resolved:** keep 8081 as the documented default; during side-by-side testing the operator sets `USHU_PORT=8082` explicitly. Final venue port assignment is `elixir-07`'s call.
- Add dialyxir now? **Default resolved:** no — revisit after `elixir-04` when contexts give types worth checking.
