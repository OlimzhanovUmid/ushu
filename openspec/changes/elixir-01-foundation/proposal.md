# elixir-01-foundation

## Why

The ushu judging system is being rewritten from Django to Elixir/Phoenix (see the master plan: 7 layered changes, `elixir-01` … `elixir-07`). This change creates the Phoenix project skeleton that every later layer builds on — nothing domain-specific yet, but every convention (config, database pragmas, tooling, i18n, tests) is fixed here so the following six changes never re-litigate them.

## What Changes

- New Phoenix ~> 1.8 project generated under `elixir/` in this repo: app `ushu`, modules `Ushu.*` / `UshuWeb.*`, single OTP application (no umbrella), generated with `--database sqlite3 --no-mailer` (LiveView and LiveDashboard kept — rationale in design.md D2).
- Pinned dependency set in `mix.exs` (`phoenix ~> 1.8`, `phoenix_live_view ~> 1.0`, `ecto_sql ~> 3.12`, `ecto_sqlite3 ~> 0.18`, `gettext ~> 0.26`, `bandit ~> 1.5`, `credo ~> 1.7` dev/test, and the Phoenix asset toolchain).
- `config/runtime.exs` reads all deploy-variable settings from `USHU_*` environment variables (`USHU_SECRET_KEY_BASE`, `USHU_PORT`, `USHU_DB_PATH`, `USHU_EVENT_TITLE`, `USHU_EVENT_SUBTITLE`, `USHU_MEDIA_DIR` — the directory of country-flag/media files served by the app via `Plug.Static`), mirroring the Django app's env contract; prod fails fast when the secret is missing.
- SQLite tuned for the venue workload: WAL journal mode, `busy_timeout` ≥ 20 000 ms, foreign keys ON — parity with the pinned `lan-deployment` rules of the Django app.
- Code style gates: `mix format --check-formatted` and Credo (strict) both pass on the fresh tree.
- Gettext scaffolding for `ru` (default) and `en`, including translated Ecto changeset errors.
- Test skeleton: ExUnit + `Ushu.DataCase` / `UshuWeb.ConnCase` with the SQL sandbox; `mix test` green on a fresh checkout.
- Dev vs prod configuration philosophy documented and enforced: compile-time config in `config/*.exs`, everything deploy-variable in `runtime.exs`.

## Capabilities

### New Capabilities

- `elixir-project-skeleton`: the generated Phoenix project — layout, dependency set, supervision tree, formatting/lint gates, test skeleton.
- `runtime-configuration`: env-driven runtime config (`USHU_*`), SQLite WAL pragmas, LAN-friendly endpoint binding, dev/prod split.
- `i18n-foundation`: gettext backend with `ru` default and `en` secondary locales, translated validation errors.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- New directory `elixir/` only; no Django file is touched (the Django app keeps running until `elixir-07-cutover`).
- Position: layer 1 of 7. Depends on nothing; **all** of `elixir-02-scoring-core` … `elixir-07-cutover` depend on this change (they add code into the project created here).
- Interfaces exposed to later layers: `Ushu.Repo` + SQLite config (used by `elixir-03-ecto-schema`), `Ushu.PubSub` name (used by `elixir-05-realtime`), `UshuWeb.Gettext` and the `:ushu, :event` branding config (read by `elixir-06-liveview-ui`), release/env contract (consumed by `elixir-07-cutover`).
