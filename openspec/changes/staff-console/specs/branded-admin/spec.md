# branded-admin

## ADDED Requirements

### Requirement: The Django admin is on-brand, not generic
The setup/reference Django admin SHALL render on the Federation Standard visual system (navy header, cool surfaces, token-based buttons and type) via a custom `AdminSite` and template/CSS overrides, so it no longer reads as generic Bootstrap/enterprise-gray admin (a PRODUCT.md anti-reference).

#### Scenario: Staff opens the styled admin
- **WHEN** staff open the admin for a setup model (e.g. clubs)
- **THEN** it renders in the navy Federation Standard shell, not the default Django blue/gray

### Requirement: Domain wording and usable lists on heavy models
Admin models SHALL carry Russian `verbose_name`/`verbose_name_plural`, and the high-volume models (Score, Participation) SHALL define `list_display`, `search_fields`, and `list_filter` that identify rows by domain fields (participant, tablo, judge, state) so a large table is navigable without guessing at ids.

#### Scenario: Find a score in a large table
- **WHEN** staff open the Score list (thousands of rows)
- **THEN** rows show participant / judge / tablo, and can be searched/filtered by them, not just by primary key

### Requirement: Reachable from the console, not a dead end
The styled admin SHALL be reachable from the staff console (a "setup / open admin" link) and SHALL keep the shell navigation so staff can return to the app, not get stranded in a separate admin silo.

#### Scenario: Return from admin
- **WHEN** staff finish a setup edit in the styled admin
- **THEN** they can navigate back to the app/console without using the browser back button as the only path
