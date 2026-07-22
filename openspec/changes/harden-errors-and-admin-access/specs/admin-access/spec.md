# admin-access

## ADDED Requirements

### Requirement: Staff can reach the Django admin from the shell
The app-shell sidebar SHALL show an "Admin" link pointing at Django's admin index (`/admin/`) for authenticated `is_staff` users (the main judge / secretary), styled with the existing sidebar navigation token vocabulary.

#### Scenario: Staff user sees the Admin link
- **WHEN** an `is_staff` user views a screen that renders the shell sidebar
- **THEN** an "Admin" nav link is present and navigates to `/admin/`

#### Scenario: Category judge does not see the Admin link
- **WHEN** a non-staff (category A/B/C) judge views the shell
- **THEN** no "Admin" link is shown
