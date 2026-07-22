# data-integrity

## ADDED Requirements

### Requirement: Competition rows are unique at the database level
The schema SHALL enforce: one `Tablo` per (age, sex, category); one `Participation` per (participant, tablo); one `Score` per (judge, participation). Existing duplicate rows SHALL be merged or removed by a data migration before the constraints apply.

#### Scenario: Duplicate registration
- **WHEN** the same participant is registered twice into the same tablo (double-click, concurrent requests)
- **THEN** the second insert fails at the database and the UI reports the duplicate instead of creating a second participation

#### Scenario: Signal race on category save
- **WHEN** the `ElementCategory` post-save signal runs concurrently for the same category
- **THEN** no duplicate `Tablo` rows can exist for one (age, sex, category)

### Requirement: Reference and history data is protected from cascade deletion
Deleting reference entities that recorded results depend on SHALL be blocked while dependents exist: judge → scores, element → element statuses, error code → recorded deductions, country/club → participants SHALL use `on_delete=PROTECT` (deactivation, not deletion, is the supported path for retiring judges).

#### Scenario: Deleting a judge with recorded scores
- **WHEN** an admin attempts to delete a judge user who has `Score` rows
- **THEN** the deletion is refused with a protected-object error and history stays intact

#### Scenario: Deleting an element used in past results
- **WHEN** an admin attempts to delete an `Element` referenced by any `ElementStatus`
- **THEN** the deletion is refused

### Requirement: Global draw is transactional and per-tablo
The global draw SHALL be a `manage.py jrebiy` management command that runs in a single transaction, numbers participations independently within each tablo (0..n−1, matching the per-tablo UI draw), and SHALL refuse to re-draw tablos already marked `started` unless explicitly forced. The legacy `jrebiy.py` shell script and its `.bat` wrapper are removed.

#### Scenario: Crash mid-draw
- **WHEN** the draw command fails partway through
- **THEN** no order or `started` changes persist (full rollback)

#### Scenario: Draw after competition started
- **WHEN** the command runs while some tablos have `started=True`
- **THEN** those tablos are skipped with a warning unless `--force` is given

### Requirement: Score cards go only to active judges
`assign_participation` SHALL create `Score` rows only for judges with `is_active=True` (in addition to the existing superuser/staff exclusions), so deactivated judges cannot block `can_be_saved` or break panel-size assumptions.

#### Scenario: Deactivated judge
- **WHEN** a participant is registered while a deactivated judge account exists
- **THEN** no `Score` row is created for that judge
