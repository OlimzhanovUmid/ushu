# judging-access-control

## ADDED Requirements

### Requirement: Every mutating endpoint requires authentication and authorization
All state-changing endpoints SHALL require a logged-in user, and role-restricted actions SHALL verify `is_staff` server-side: reopening a judge's card (`open_judge`), deleting a participation, activating a participant, running the draw, and pushing content to the monitor SHALL all require `is_staff` (a dedicated secretary is provisioned by granting the flag in admin).

#### Scenario: Anonymous reopen attempt
- **WHEN** an unauthenticated client calls the reopen-judge endpoint
- **THEN** it is redirected to login and no `Score.saved` flag changes

#### Scenario: Regular judge tries to reopen
- **WHEN** a logged-in non-staff judge calls the reopen-judge endpoint
- **THEN** the request is rejected (403) and no state changes

#### Scenario: Regular judge tries to activate
- **WHEN** a logged-in non-staff judge posts to the activation endpoint
- **THEN** the request is rejected (403) and no participation becomes DOING

### Requirement: State changes travel over POST with CSRF protection
Activation, reopening, deletion, and draw actions SHALL be POST requests carrying a CSRF token; GET requests to these endpoints SHALL NOT mutate state. Destructive actions (delete participation) SHALL require an explicit confirmation step in the UI.

#### Scenario: GET cannot delete
- **WHEN** a GET request hits the delete-participation URL
- **THEN** nothing is deleted (method not allowed or redirect)

#### Scenario: Delete requires confirmation
- **WHEN** the secretary clicks the delete control in the standings table
- **THEN** a confirmation is required before the POST is sent

### Requirement: A judge can modify only their own scorecard
Judge submissions SHALL only affect rows belonging to the submitting judge's own `Score` for the currently active participation: `JudgeCSubmit` MUST filter `ElementStatus` by ownership (score → judge) instead of trusting POSTed primary keys.

#### Scenario: Forged element pk
- **WHEN** a logged-in user posts an `ElementStatus` pk that belongs to another judge's score
- **THEN** that row is not modified and the submission is rejected

### Requirement: At most one participation is active
The system SHALL enforce at the database level (partial unique index on `state=DOING`) that no two participations are active simultaneously; activation SHALL be valid only from the WAITING state and SHALL fail cleanly when another participation is already active.

#### Scenario: Double activation
- **WHEN** two secretary requests activate different participants concurrently
- **THEN** exactly one becomes DOING; the other request fails with a visible message and no judge ever sees two candidates

#### Scenario: Re-activating a finished participation
- **WHEN** activation is requested for a participation whose state is FINISHED
- **THEN** the request is rejected and the state does not change

### Requirement: Judge submits fail gracefully without an active participant
When no participation is DOING (e.g. the main judge finalized while a judge's form was open), judge submissions SHALL NOT crash with a 500; the judge SHALL be redirected to the waiting screen with an explanatory message, and invalid inputs (unparseable score, unknown error code) SHALL produce visible feedback instead of being silently swallowed.

#### Scenario: Submit after finalization
- **WHEN** a judge posts a score after the main judge saved the final result
- **THEN** the judge lands on the waiting screen with a "participant already finalized" message

#### Scenario: Invalid error code
- **WHEN** a judge submits an error code outside the valid range for their category
- **THEN** the code is rejected with feedback on the form, not silently dropped
