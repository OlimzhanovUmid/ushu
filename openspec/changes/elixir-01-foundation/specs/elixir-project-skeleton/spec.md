# elixir-project-skeleton

## ADDED Requirements

### Requirement: Project is generated with pinned generator flags

The Phoenix project SHALL live in `elixir/` at the repo root and SHALL be generated with `mix phx.new ushu --database sqlite3 --no-mailer` (Phoenix generator ~> 1.8), producing app `:ushu`, root modules `Ushu` and `UshuWeb`, a single OTP application (no umbrella), with LiveView and LiveDashboard included and the Swoosh mailer absent. The generated frontend toolchain (esbuild + tailwind with locally cached binaries) SHALL be kept so all assets build and serve offline.

#### Scenario: Fresh generation matches the contract

- **WHEN** the project under `elixir/` is inspected after generation
- **THEN** `mix.exs` declares `app: :ushu`, no umbrella structure exists, `lib/ushu/` and `lib/ushu_web/` are present, no `Swoosh`/mailer module or dependency exists, and `UshuWeb.Telemetry` plus LiveDashboard routing are present in the dev environment

#### Scenario: Assets build without internet

- **WHEN** `mix assets.build` runs on a machine with esbuild/tailwind binaries already fetched
- **THEN** CSS and JS bundles are produced from local sources with no CDN or external URL referenced in the resulting HTML layouts

### Requirement: Dependency set is pinned in mix.exs

`mix.exs` SHALL declare, at minimum: `{:phoenix, "~> 1.8"}`, `{:phoenix_live_view, "~> 1.0"}`, `{:phoenix_ecto, "~> 4.5"}`, `{:ecto_sql, "~> 3.12"}`, `{:ecto_sqlite3, "~> 0.18"}`, `{:gettext, "~> 0.26"}`, `{:bandit, "~> 1.5"}`, `{:jason, "~> 1.4"}`, `{:phoenix_live_dashboard, "~> 0.8"}`, and `{:credo, "~> 1.7", only: [:dev, :test], runtime: false}`. `mix.lock` SHALL be committed. No Postgres driver (`postgrex`) SHALL be present.

#### Scenario: Lockfile is authoritative

- **WHEN** `mix deps.get` runs on a fresh checkout
- **THEN** it resolves exactly the versions recorded in the committed `mix.lock` and `postgrex` is not among them

### Requirement: Application supervision tree boots the shared services

`Ushu.Application` SHALL start, under one root supervisor named `Ushu.Supervisor` (strategy `:one_for_one`), at least: `UshuWeb.Telemetry`, `Ushu.Repo`, `{Phoenix.PubSub, name: Ushu.PubSub}`, and `UshuWeb.Endpoint`. The PubSub process name `Ushu.PubSub` is the contract consumed by `elixir-05-realtime`.

#### Scenario: Application starts cleanly

- **WHEN** `mix phx.server` (or `iex -S mix`) starts the app in dev
- **THEN** the supervision tree comes up with Repo, PubSub, Telemetry and Endpoint alive, and `Process.whereis(Ushu.PubSub)` returns a pid

### Requirement: Domain and web code are separated

Business/domain modules SHALL live under `lib/ushu/` (`Ushu.*` — contexts, schemas, pure logic) and SHALL NOT depend on `UshuWeb.*`; web modules (controllers, LiveViews, components, endpoint, router) SHALL live under `lib/ushu_web/`. Later layers follow this split (`Ushu.Scoring` in 02, contexts in 04, LiveViews in 06).

#### Scenario: Dependency direction check

- **WHEN** modules under `lib/ushu/` are grepped for `UshuWeb`
- **THEN** no reference from the domain layer to the web layer exists

### Requirement: Formatting and lint gates pass on the clean tree

The project SHALL include `.formatter.exs` (with the Phoenix/Ecto import_deps and LiveView HEEx plugin) and `.credo.exs` with strict mode enabled. Both `mix format --check-formatted` and `mix credo --strict` SHALL exit 0 on the committed tree; these are the standing style gates for every later change.

#### Scenario: Gates green on fresh checkout

- **WHEN** `mix format --check-formatted && mix credo --strict` runs after `mix deps.get`
- **THEN** both commands exit with status 0

### Requirement: Test skeleton runs green with the SQL sandbox

The project SHALL ship `test/support/data_case.ex` and `test/support/conn_case.ex` configured for `Ecto.Adapters.SQL.Sandbox` over the SQLite test database, plus at least one smoke test per case type (a Repo round-trip is not required yet — a context-boot assertion suffices). `mix test` SHALL exit 0 on a fresh checkout and is the standing Gate-2 check for all later changes.

#### Scenario: Fresh checkout test run

- **WHEN** `mix deps.get && mix test` runs on a clean clone with no env vars set
- **THEN** all tests pass using the dev-default configuration and a throwaway test database
