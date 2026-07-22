# staff-console

## ADDED Requirements

### Requirement: Task-first console home for staff
The "Admin" sidebar entry SHALL open, for `is_staff` users, a console that presents the correction jobs in domain language (verbs, concrete objects), not Django model names, inside the Federation Standard shell. Non-staff users SHALL NOT reach it.

#### Scenario: Staff opens the console
- **WHEN** an `is_staff` user follows the Admin entry
- **THEN** they see a task-first console (find participant, re-open, withdraw, retire judge), not a raw model list

#### Scenario: Non-staff attempt
- **WHEN** a category judge requests the console URL directly
- **THEN** access is denied (not rendered)

### Requirement: Find a participant and see their score state
The console SHALL let staff search participants (by name / club / tablo) and view a participant's participations with each judge's score state, so the right object is found before any correction.

#### Scenario: Locate a finished participant
- **WHEN** staff search for a name that has finished participations
- **THEN** the results show the participant's participations and per-judge score state, disambiguated by tablo

### Requirement: Re-open a judge slot or a whole participation for re-entry
The console SHALL let staff re-open a specific judge's score slot — or an entire participation — for any participation including finished ones, so the correction is re-entered through the validated judging UI rather than by editing score fields directly. This generalizes the existing active-only re-open.

#### Scenario: Correct a finished participant's score
- **WHEN** staff re-open a judge's slot for a finished participation
- **THEN** that judge can re-enter the score through the normal judging screen, and the result re-aggregates through the validated path

### Requirement: Irreversible corrections confirm in domain terms
Withdrawing a participation and retiring a judge (and re-opening, which discards a saved result) SHALL require an explicit confirmation that names the concrete object, with the destructive control styled competition-red and separated from routine actions.

#### Scenario: Withdraw a participation
- **WHEN** staff withdraw a participation
- **THEN** a confirmation naming the participant and tablo is shown before the irreversible delete, in competition-red

### Requirement: Retire a judge without deleting history
The console SHALL retire a judge by setting `is_active=False`, never by deletion (scores are protected), and SHALL make clear this preserves competition history.

#### Scenario: Retire a judge who has scores
- **WHEN** staff retire a judge that already recorded scores
- **THEN** the judge is deactivated, their scores remain, and no deletion is attempted
