# runtime-configuration

## ADDED Requirements

### Requirement: Deploy-variable settings come from USHU_* environment variables

`config/runtime.exs` SHALL read all deploy-variable settings from the environment, with the Django-compatible names: `USHU_SECRET_KEY_BASE` (Endpoint `secret_key_base`), `USHU_PORT` (HTTP port, default `8081` for parity with the Django deployment), `USHU_DB_PATH` (SQLite file path, defaulting to a path under the release/project directory), `USHU_EVENT_TITLE` and `USHU_EVENT_SUBTITLE` (event branding, defaulting to the same strings as the Django app: `"O'ZBEKISTON USHU FEDERATSIYASI"` / `"O'RTA OSIYO CHEMPIONATI"`), and `USHU_MEDIA_DIR` (directory of country-flag/media files served by the app via `Plug.Static`, defaulting to a path under the release/project directory).

#### Scenario: Port override

- **WHEN** the app starts with `USHU_PORT=9000`
- **THEN** the endpoint listens on port 9000; without the variable it listens on 8081

#### Scenario: Branding override

- **WHEN** the app starts with `USHU_EVENT_TITLE="Кубок Ташкента"`
- **THEN** `Application.get_env(:ushu, :event)[:title]` returns that string; without the variable the Django-era default is returned

#### Scenario: Media directory override

- **WHEN** the app starts with `USHU_MEDIA_DIR=/data/media` containing a flag file
- **THEN** the endpoint serves that file via `Plug.Static` from the configured directory; without the variable the default directory is used

### Requirement: Production fails fast without a secret

In `config_env() == :prod`, a missing `USHU_SECRET_KEY_BASE` SHALL abort boot with a clear error message (raise in `runtime.exs`); in `:dev` and `:test` a committed, obviously-insecure default MAY be used. No production secret SHALL ever be committed to the repository.

#### Scenario: Prod boot without secret

- **WHEN** a release starts with `MIX_ENV=prod` and no `USHU_SECRET_KEY_BASE`
- **THEN** the VM exits during configuration with an error naming the missing variable, before the endpoint binds

### Requirement: SQLite runs in WAL mode with a venue-grade busy timeout

`Ushu.Repo` SHALL be configured (all environments) with `journal_mode: :wal`, `busy_timeout: 20_000` or higher, and foreign-key enforcement ON. Pool size SHALL be small (≤ 5) acknowledging SQLite's single-writer model. This carries over the pinned Django `lan-deployment` rule: concurrent judge submissions must wait for the write lock, not fail with `database is locked`.

#### Scenario: Pragmas actually applied

- **WHEN** a test inspects the live connection (`PRAGMA journal_mode`, `PRAGMA busy_timeout`, `PRAGMA foreign_keys`)
- **THEN** it reads `wal`, a value ≥ 20000, and `1` respectively (regression guard against misplaced options)

#### Scenario: Concurrent writes

- **WHEN** two processes write to the database at the same moment
- **THEN** the second write waits for the lock within the busy timeout instead of raising

### Requirement: Endpoint accepts LAN clients

The endpoint SHALL bind `0.0.0.0` in dev and prod, and origin checking SHALL NOT reject venue clients that connect by LAN IP or hostname: `check_origin` SHALL be `false` (offline venue LAN, no public exposure — rationale in design.md D8). No page SHALL reference an external host.

#### Scenario: Judge client connects via LAN IP

- **WHEN** a client opens `http://192.168.x.x:8081/` and its LiveView socket connects
- **THEN** the HTTP response and the WebSocket upgrade both succeed with no origin rejection

### Requirement: Compile-time and runtime config are strictly separated

`config/config.exs`, `dev.exs`, `test.exs`, `prod.exs` SHALL contain only settings that are legitimately compile-time or environment-structural (logger level, code reloader, asset watchers, endpoint compile flags); every setting that can differ between two venue deployments of the SAME release binary (secret, port, DB path, branding) SHALL live only in `config/runtime.exs`.

#### Scenario: One release, two events

- **WHEN** the same compiled release is started twice with different `USHU_EVENT_TITLE`/`USHU_PORT` values
- **THEN** both instances reflect their own values without recompilation
