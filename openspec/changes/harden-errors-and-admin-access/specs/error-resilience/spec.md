# error-resilience

## ADDED Requirements

### Requirement: Missing objects return 404, not 500
Views that resolve a domain object from URL/query input SHALL return HTTP 404 when the object does not exist, instead of raising an unhandled `DoesNotExist` (HTTP 500). This covers the tablo detail (`category` + `age` + `sex`), tablo monitor and print (`pk`), the participant score and element-points views (`pk`), and the activation lookup.

#### Scenario: Detail URL opened without query params
- **WHEN** a request hits `/tablo/detail/<pk>/` with no or blank `age`/`sex` params, or with a combination that matches no Tablo
- **THEN** the response is a 404, not a 500 traceback

#### Scenario: Print/monitor for a non-existent pk
- **WHEN** a print or monitor URL references a tablo pk that does not exist
- **THEN** the response is a 404

#### Scenario: Score/points for a non-existent participant
- **WHEN** a score or element-points URL references a participant pk that does not exist
- **THEN** the response is a 404

### Requirement: On-brand error pages under DEBUG=0
The application SHALL render on-brand `404` and `500` pages (foundation navy shell, Russian text, a link back to a safe screen) when `DEBUG=0`, instead of Django's plain default pages. The `500` page SHALL be self-contained and SHALL NOT depend on request context that may be unavailable during an error.

#### Scenario: 404 in production
- **WHEN** a not-found response is returned with `DEBUG=0`
- **THEN** the user sees the branded 404 page with a way back, not the plain Django 404

#### Scenario: 500 in production
- **WHEN** an unexpected server error occurs with `DEBUG=0`
- **THEN** the user sees the branded 500 page, and rendering it does not itself raise

### Requirement: Favicon is served
Every page SHALL declare a favicon and the application SHALL respond to `/favicon.ico` (reusing the existing logo asset) so browsers' implicit favicon requests do not 404.

#### Scenario: Browser requests favicon.ico
- **WHEN** a browser implicitly requests `/favicon.ico`
- **THEN** it receives the logo (directly or via redirect), not a 404
