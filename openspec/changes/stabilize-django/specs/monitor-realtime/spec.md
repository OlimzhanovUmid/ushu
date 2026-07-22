# monitor-realtime

## ADDED Requirements

### Requirement: Monitor updates are pushed over SSE
The projector/monitor screen SHALL receive display updates via a Server-Sent Events stream: the server pushes a complete snapshot (current pages + revision) on connect and whenever the displayed content changes; the client SHALL NOT poll on a timer, and reconnection SHALL use SSE's built-in retry with a floor of 2 seconds (no 100ms retry storms).

#### Scenario: Secretary sends standings to the monitor
- **WHEN** the secretary pushes a tablo's standings to the monitor
- **THEN** every connected monitor receives the new snapshot within a second, without re-requesting

#### Scenario: Server restarts
- **WHEN** the server restarts while monitors are connected
- **THEN** each monitor reconnects with backoff (≥2s) and receives the current snapshot on reconnect

### Requirement: Monitor state lives in process memory, not the filesystem
Monitor snapshots SHALL be held in process memory (single-process server) and updated atomically; the system SHALL NOT write rendered HTML into the templates directory, and `showme*.html`/`file.count` runtime artifacts SHALL be removed from the repository.

#### Scenario: No torn reads
- **WHEN** a snapshot with a new page count is published while a monitor is reading
- **THEN** the monitor receives either the complete old snapshot or the complete new one, never a mix

#### Scenario: Read-only code directory
- **WHEN** the application directory is mounted read-only
- **THEN** monitor functionality still works

### Requirement: Snapshot rendering must not partially fail
Rendering the monitor pages SHALL either fully succeed or leave the previous snapshot intact: a render error (e.g. a country without a flag image) SHALL NOT publish a partial update, and missing flag images SHALL render as a blank placeholder instead of raising.

#### Scenario: Country without a flag
- **WHEN** standings containing a club whose country has no flag image are sent to the monitor
- **THEN** the pages render with a placeholder and the snapshot publishes completely

### Requirement: Idle-screen branding is configurable
The monitor idle screen SHALL render its event title and subtitle from configuration (`EVENT_TITLE`, `EVENT_SUBTITLE` environment/settings values) instead of hardcoded template text, with the current Uzbek strings as defaults.

#### Scenario: New tournament rebranding
- **WHEN** the operator sets `EVENT_TITLE`/`EVENT_SUBTITLE` in the launcher environment and restarts
- **THEN** the monitor idle screen shows the new texts without any source-code edit

### Requirement: Judge screens keep working after URL restructuring
Judge-screen auto-refresh endpoints SHALL be referenced via reversed URLs (`{% url %}`), not relative paths, so mounting the app under a prefix does not silently break judges' polling/refresh.

#### Scenario: App mounted under a prefix
- **WHEN** the app is served under a non-root URL prefix
- **THEN** judge screens still detect participant changes
