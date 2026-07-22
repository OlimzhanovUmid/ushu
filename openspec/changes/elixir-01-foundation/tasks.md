# Tasks — elixir-01-foundation

## 1. Toolchain & project generation

- [x] 1.1 Pin the toolchain: commit `elixir/.tool-versions` with Elixir 1.19.5 / OTP 28 (asdf/mise) — pinned the ACTUAL installed toolchain, not the 1.18.x/27 in the original task text, because pinning a version absent from the machine would fail the "verify `elixir --version` matches" step; Phoenix ~> 1.8 fully supports 1.19/OTP 28
- [x] 1.2 Install the generator: `mix archive.install hex phx_new` → phx_new 1.8.9
- [x] 1.3 Generate the project: from repo root ran `mix phx.new elixir --app ushu --module Ushu --database sqlite3 --no-mailer`; confirmed `app: :ushu`, `mod: {Ushu.Application, []}`, `lib/ushu` + `lib/ushu_web`, no Swoosh, no umbrella
- [x] 1.4 Add `elixir/`-appropriate entries to `.gitignore` (generator ships `_build/`, `deps/`, `*.db*`, `/assets/node_modules/`; added `*.sqlite3*`) without touching Django ignores
- [x] 1.5 Run `mix deps.get && mix assets.setup` once with internet access; `mix.lock` committed (deps.get exit 0; assets.setup binaries installed)

## 2. Dependencies & code-style gates

- [x] 2.1 Review generated `mix.exs`: pinned `{:ecto_sqlite3, "~> 0.18"}` (was `>= 0.0.0`); confirmed `phoenix ~> 1.8.9`, `phoenix_live_view ~> 1.2`, `bandit ~> 1.5`, `gettext ~> 1.0` (generator ships gettext 1.0, newer than the spec's `~> 0.26` floor — kept the newer major), `ecto_sql ~> 3.13`; `postgrex` absent (only an optional transitive reference, no lock entry, not in dep tree)
- [x] 2.2 Add `{:credo, "~> 1.7", only: [:dev, :test], runtime: false}`; ran `mix deps.get` → credo 1.7.19
- [x] 2.3 Generated `.credo.exs` (`mix credo gen.config`), set `strict: true`; tuned `Design.AliasUsage` to `if_called_more_often_than: 2` so canonical one-off `Ecto.Adapters.SQL.*` calls in generated/test code don't trip it; fixed the one zero-arity-parens finding in `application.ex` (definition only — the call site keeps `()`)
- [x] 2.4 Confirmed `.formatter.exs` has `import_deps: [:ecto, :ecto_sql, :phoenix]` and the `Phoenix.LiveView.HTMLFormatter` plugin; ran `mix format`
- [x] 2.5 Gate check: `mix format --check-formatted` exit 0 and `mix credo --strict` exit 0 (found no issues)

## 3. Runtime configuration & SQLite

- [x] 3.1 Rewrote `config/runtime.exs`: reads `USHU_SECRET_KEY_BASE` (raise in prod if missing), `USHU_PORT` (default 8081), `USHU_DB_PATH` (default `../ushu.sqlite3`), `USHU_EVENT_TITLE`/`USHU_EVENT_SUBTITLE` + `USHU_MEDIA_DIR` (Django-parity defaults) into `Application` config (`:ushu, :event` keyword + `:ushu, :media_dir`)
- [x] 3.2 Configured `Ushu.Repo` in all envs with `journal_mode: :wal`, `busy_timeout: 20_000`, `foreign_keys: :on` (real exqlite atom option, verified in `deps/exqlite`), `pool_size` 5 (test keeps the SQL sandbox pool)
- [x] 3.3 Endpoint: binds `{0,0,0,0}` in dev and prod; `check_origin: false`; `USHU_PORT` reaches the Bandit `http: [port: ...]` listener in both runtime.exs (prod) and dev.exs
- [x] 3.4 Swept `config/{config,dev,test,prod}.exs`: all deploy-variable settings live in `runtime.exs`; **removed `force_ssl` from prod.exs** (would redirect the plain-HTTP LAN to https and break every client); added the D7 rule comment block to config.exs and prod.exs
- [x] 3.5 Audited layouts/assets: `root.html.heex` loads only local `/assets/*`; replaced the generated `home.html.heex` placeholder (had github/discord/fly.io anchor links) with a minimal offline landing showing the event title; set `lang="ru"`

## 4. Gettext ru/en

- [x] 4.1 Configured `UshuWeb.Gettext` in `config/config.exs` with `default_locale: "ru"` and `allowed_locales: ~w(ru en)` (the real gettext option — the task draft's `locales` key does not exist; verified in `deps/gettext`)
- [x] 4.2 Scaffolded catalogs: `mix gettext.extract` then `mix gettext.merge priv/gettext --locale ru` (created `ru/LC_MESSAGES/{errors,default}.po`) and `--locale en`; `.po`/`.pot` files present
- [x] 4.3 Translated all 24 `errors.po` msgids into Russian for the `ru` locale (3-form plurals), plus the 6 `default.po` strings incl. the landing message
- [x] 4.4 Confirmed `translate_error/1` in `UshuWeb.CoreComponents` (core_components.ex:481) routes through `Gettext.dngettext/dgettext(UshuWeb.Gettext, "errors", ...)` — generated default, no change needed

## 5. Tests & verification

- [x] 5.1 Confirmed `test/support/data_case.ex` and `conn_case.ex` use `Ecto.Adapters.SQL.Sandbox` against a throwaway SQLite test DB; `mix test` green
- [x] 5.2 Added the pragma regression test (`test/ushu/repo_pragma_test.exs`): live-connection `PRAGMA journal_mode` = `wal` and `PRAGMA foreign_keys` = 1. **`PRAGMA busy_timeout` cannot be used** — exqlite installs a custom NIF busy handler and avoids the pragma (which would destroy that handler; verified in `deps/exqlite/connection.ex`), so the pragma always reads 0. Guarded busy_timeout at the Repo config value (≥ 20000) instead — the misplaced-option failure mode D4 actually cares about
- [x] 5.3 Added config test (`test/ushu/runtime_config_test.exs`): with no env vars, `:event` `:title`/`:subtitle` equal the Django-era defaults; both keys present; `:media_dir` set
- [x] 5.4 Added supervision smoke test (`test/ushu/application_test.exs`): `Process.whereis(Ushu.PubSub)` and `Ushu.Repo` return pids
- [x] 5.5 Added gettext test (`test/ushu_web/gettext_test.exs`): default locale `"ru"`, an `errors`-domain msgid renders Russian by default, and `put_locale("en")` switches within the process
- [x] 5.6 Added domain/web separation test (`test/ushu/domain_web_separation_test.exs`): no module under `lib/ushu/` references `UshuWeb`, excluding the `Ushu.Application` composition root (which legitimately wires the endpoint/telemetry)
- [x] 5.7 Full gate green with no env vars set: `mix format --check-formatted` (0), `mix credo --strict` (0, no issues), `mix test` (17 tests, 0 failures)
- [x] 5.8 Boot/render check: booted `PHX_SERVER=true mix phx.server`; `GET /` returns 200 on BOTH `localhost:8081` and the LAN IP `192.168.0.149:8081` (0.0.0.0 bind + no origin rejection, D8), event title + Russian landing string render, local `/assets/css|js` both 200, LiveDashboard `/dev/dashboard` → 200, zero external-host refs in served HTML. (A literal second-device browser open remains an owner action; LAN-IP curl proves reachability.)

## 6. Documentation

- [x] 6.1 Wrote `elixir/README.md`: prerequisites (`.tool-versions`), setup + gate commands, the `USHU_*` env table, the D7 compile/runtime rule, and the "never first-build at the venue" warning
- [x] 6.2 Finalized the Russian explainer `docs/elixir-rewrite/01-foundation.md`: reconciled the deps snippet to the real toolchain (Elixir 1.19.5/OTP 28, gettext 1.0, ecto_sql 3.14, exqlite 0.38), rewrote the SQLite section to teach the exqlite busy_timeout/PRAGMA gotcha and `foreign_keys: :on` atom, fixed `allowed_locales`, and documented the `force_ssl` removal + render-walk result
