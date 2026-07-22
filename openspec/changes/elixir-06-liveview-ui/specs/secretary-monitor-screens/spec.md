# secretary-monitor-screens

Secretary console, main-judge score review, projector monitor and printable
protocol. All business operations are context functions from
`elixir-04-contexts`; realtime events and the `MonitorBoard` snapshot come
from `elixir-05-realtime`.

## ADDED Requirements

### Requirement: Secretary console presents the tablo grid and standings

`SecretaryLive` SHALL present a grid of tablos
organized by element category x age bucket x sex, and, for a selected tablo,
the participation list ordered by draw order with state badges
(`:waiting`/`:performing`/`:finished`/`:no_show`) and a standings table whose
ranks are computed by the tie-break rules of `elixir-04-contexts` (final score,
then e4/e3/e2 performed-element counters). Rank numbers SHALL be assigned only
to `:finished` participations; `:no_show` rows appear unranked at the bottom.

#### Scenario: Selecting a tablo

- **WHEN** the secretary clicks a tablo cell in the grid
- **THEN** the participation list and standings for that tablo render without a page reload (`handle_params` patch)

#### Scenario: Standings ranks

- **WHEN** two finished participations have equal final scores and different tie-break counters
- **THEN** the standings table orders them per the tie-break and shows distinct ranks

### Requirement: Secretary actions are guarded, confirmed, and reactive

The secretary console SHALL expose: activate a `:waiting` participation, run
the per-tablo draw, push standings/scores to the monitor, and delete a
participation. Destructive or state-changing actions (delete, draw over an
already-drawn tablo) SHALL require an explicit confirmation dialog. Failures
returned by the contexts (e.g. another participation already `:performing` —
the partial unique index) SHALL surface as a flash/error, never a crash. The
console SHALL subscribe to the `"competition"` topic and refresh its lists on
`{:performance_started, id}`, `{:score_saved, score_id}`,
`{:score_reopened, score_id}`, `{:performance_finalized, id}`.

#### Scenario: Double activation race

- **WHEN** the secretary activates a participant while another is still `:performing`
- **THEN** the context returns an error, the console shows "another participant is on the carpet", and no second activation happens

#### Scenario: Judge submits while secretary watches

- **WHEN** a judge saves a score for the active participation
- **THEN** the secretary's panel updates the judge's submitted-status without any manual refresh

#### Scenario: Delete requires confirmation

- **WHEN** the secretary clicks delete on a participation row
- **THEN** a confirmation dialog must be accepted before the context delete is called

### Requirement: Secretary sees judge presence

The secretary console SHALL display a judge presence panel driven by
`Phoenix.Presence` (topic and metadata defined in `elixir-05-realtime`),
listing each active judge account with an online/offline indicator and their
category, updating on presence diffs without refresh.

#### Scenario: Judge station disconnects

- **WHEN** a judge's browser loses its socket (machine sleeps, cable pulled)
- **THEN** within the presence timeout the secretary's panel shows that judge as offline

### Requirement: Main judge reviews and controls scores per judge

`ScoresLive` (roles `:main_judge`, `:admin`) SHALL show, for the `:performing`
participation, the per-judge breakdown: each A judge's recorded errors, each B
judge's effective score, each C judge's marks, plus the aggregated A/B/C and
projected final from the scoring core. It SHALL offer: toggle bonus (+0.05 on
B), finalize (allowed only when every panel card is saved), mark no-show
(records state `:no_show`, no score sentinel), and per-judge reopen —
including B judges — each reopen behind a confirmation and recorded to the
audit trail (`score_events`, `elixir-04-contexts`).

#### Scenario: Finalize gate

- **WHEN** at least one judge card for the active participation is unsaved
- **THEN** the finalize control is disabled and lists which judges are missing

#### Scenario: Reopen a B judge

- **WHEN** the main judge confirms reopening a specific B judge's saved card
- **THEN** that card's `submitted` becomes false, a `{:score_reopened, score_id}` broadcast returns the card on that judge's console, other judges are untouched, and an audit event is recorded

#### Scenario: No-show

- **WHEN** the main judge confirms no-show for the performing participant
- **THEN** the participation state becomes `:no_show` (not `:finished` with score 0) and standings render it unranked

### Requirement: Monitor renders MonitorBoard snapshots in four modes

`MonitorLive` SHALL, on connected mount, read the current snapshot from
`Ushu.Competition.MonitorBoard` and subscribe to the `"monitor"` topic,
re-rendering on `{:monitor_updated, %MonitorState{}}`. It SHALL render four
modes from the snapshot's `mode`: `:idle` (event title/subtitle from
configuration), `:performing` (current athlete: name, club, country flag with
blank placeholder when missing, tablo), `:scores` (the finalized athlete's
A/B/C and final score), `:standings` (top rows of the pushed tablo). Rendering
SHALL use projector-scale typography readable from the hall. The client SHALL
NOT poll; reconnection after a server restart uses LiveView's built-in rejoin
and re-reads the snapshot in mount.

#### Scenario: Push standings

- **WHEN** the secretary pushes a tablo's standings to the monitor
- **THEN** every connected monitor swaps to `:standings` mode with the new data within the broadcast, without re-requesting

#### Scenario: Server restart

- **WHEN** the server restarts while the projector page is open
- **THEN** the LiveView client reconnects automatically and mount re-reads the current `MonitorBoard` snapshot — no manual reload at the projector

#### Scenario: Missing flag

- **WHEN** the snapshot contains a country without a flag asset
- **THEN** a blank placeholder is rendered and the rest of the screen is unaffected

### Requirement: Printable protocol with finished-only ranks

`PrintLive` (roles `:admin`, `:main_judge`) SHALL render a per-tablo protocol
suitable for printing: header (event title, tablo category/age/sex, date),
rows ordered by rank with name, club, A/B/C, final score. Only `:finished`
participations receive rank numbers; `:no_show` rows print with a no-show
marking and no rank. A print stylesheet (`@media print`) SHALL hide
navigation/chrome and paginate cleanly.

#### Scenario: Protocol excludes unfinished from ranking

- **WHEN** a tablo has finished, waiting and no-show participations
- **THEN** the printed ranks 1..n cover exactly the finished ones, in tie-break order

#### Scenario: Browser print

- **WHEN** the secretary hits Ctrl+P on the protocol page
- **THEN** the print output contains only the protocol content, with page breaks between large sections

### Requirement: All screens are localized with Russian as default

Every user-visible string in the LiveViews and layouts SHALL go through
`gettext`; the default locale is `ru` with `en` as secondary. The locale SHALL
be resolvable per session (query param or session setting) and applied in a
plug/on_mount so both dead and live renders agree. No raw msgid leaks to the
screen for the `ru` locale.

#### Scenario: Default Russian UI

- **WHEN** a judge opens any screen without choosing a locale
- **THEN** all labels, buttons, flashes and validation messages render in Russian

#### Scenario: Switching to English

- **WHEN** the locale is switched to `en`
- **THEN** subsequent renders (including LiveView re-renders after events) use English strings
