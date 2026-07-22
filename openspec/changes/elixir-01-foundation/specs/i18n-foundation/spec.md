# i18n-foundation

## ADDED Requirements

### Requirement: Gettext backend with ru default and en secondary

The project SHALL define a Gettext backend (`UshuWeb.Gettext`) with `default_locale: "ru"` and known locales `["ru", "en"]`, configured in `config/config.exs`. `priv/gettext/` SHALL contain scaffolded `ru` and `en` locale directories with `default.po` and `errors.po` catalogs (extracted via `mix gettext.extract --merge`).

#### Scenario: Default locale is Russian

- **WHEN** the application renders a translated string without any explicit locale selection
- **THEN** the Russian translation is used

#### Scenario: Catalogs exist for both locales

- **WHEN** `priv/gettext/` is inspected
- **THEN** `ru/LC_MESSAGES/{default,errors}.po` and `en/LC_MESSAGES/{default,errors}.po` all exist and compile without warnings

### Requirement: Ecto validation errors are translated

`Ushu.DataCase`/core error helpers SHALL route Ecto changeset error messages through `UshuWeb.Gettext` (the generated `translate_error/1` mechanism), so validation messages produced by later layers (`elixir-03-ecto-schema`, `elixir-04-contexts`) appear in Russian by default without per-schema work.

#### Scenario: Changeset error in Russian

- **WHEN** a changeset fails a `validate_required` check under the `ru` locale with the corresponding `errors.po` entry translated
- **THEN** the rendered error message is the Russian string, not the English msgid

### Requirement: Per-request locale selection is deferred but not blocked

This change SHALL NOT implement user-facing locale switching; the process-level mechanism (`Gettext.put_locale/2`) SHALL be the designated extension point, and a session/`on_mount`-based locale hook is explicitly left to `elixir-06-liveview-ui`. Nothing in the foundation SHALL hard-code a locale outside the Gettext configuration.

#### Scenario: Locale can be switched programmatically

- **WHEN** a test calls `Gettext.put_locale(UshuWeb.Gettext, "en")` and renders a translated string in the same process
- **THEN** the English string is returned, proving the switch mechanism works for layer 06 to build on
