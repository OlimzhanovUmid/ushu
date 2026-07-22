# lan-deployment

## ADDED Requirements

### Requirement: Server accepts LAN client requests
The server SHALL accept HTTP requests addressed by any host name or IP a venue client uses (LAN IP, hostname), with `ALLOWED_HOSTS` configured explicitly rather than relying on the pre-1.11 DEBUG bypass.

#### Scenario: Judge client connects via LAN IP
- **WHEN** a client requests `http://192.168.x.x:8081/` (any LAN address of the server)
- **THEN** the server responds normally, not with `400 Bad Request (DisallowedHost)`

### Requirement: SQLite is configured for concurrent judge writes
The database connection SHALL apply a busy-timeout of at least 20 seconds (the `OPTIONS` dict placed inside the `default` alias) and SHALL run SQLite in WAL journal mode so readers are not blocked by the single writer.

#### Scenario: Two judges submit simultaneously
- **WHEN** two judge submissions write to the database at the same moment
- **THEN** the second write waits for the lock instead of failing with `database is locked` after 5 seconds

#### Scenario: Timeout actually applied
- **WHEN** the Django connection for the `default` alias is inspected
- **THEN** its options contain the configured timeout (regression test for the misplaced-`OPTIONS` bug)

### Requirement: All assets are served offline
Every page SHALL load without internet access: no external font/CDN references remain, and static files plus media SHALL be served with `DEBUG=False` (via WhiteNoise or equivalent), so DEBUG is no longer load-bearing.

#### Scenario: Page load with no internet
- **WHEN** any screen (login, judge, secretary, monitor) is loaded on a machine with no internet route
- **THEN** first paint is not delayed by external requests and no request leaves the LAN

#### Scenario: Static and media with DEBUG off
- **WHEN** the server runs with `DEBUG=False`
- **THEN** CSS, JS, and country-flag images are still served successfully

### Requirement: Secrets and mode come from the environment
`SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` SHALL be read from environment variables (with safe development defaults), and the committed production secret key SHALL be rotated out of use.

#### Scenario: Production launch
- **WHEN** the server is started via the production launcher
- **THEN** it runs with `DEBUG=False` and a secret key supplied by the environment, not the historical committed value
