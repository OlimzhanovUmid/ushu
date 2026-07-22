# Proposal: redesign-admin

## Why

Before and between rounds, the organizer/registrar and the main judge work the setup surfaces: signing in, registering athletes, browsing and drawing the tablo grid, and printing protocols. `PRODUCT.md` ranks this third after the judge hot path and projector, but it is where an event is assembled — clarity and speed here prevent errors that surface later on the carpet. This change is a full redesign of the admin/setup surfaces on the tokens and shell from `redesign-foundation`. `login.html` was already partially redesigned, so it needs a polish pass, not a rebuild.

## What Changes

- Redesign the list/detail tables — `tablo_list.html`, `tablo_detail.html`: scannable, token-styled tables with clear row actions and status, so the grid and its state are legible at a glance.
- Redesign the entry forms — `participant_create.html`: clear labels, visible focus, and inline error messaging so registration is fast and mistakes are caught at entry.
- Polish `login.html`: bring the already-redesigned sign-in fully in line with the finalized foundation tokens.
- Redesign `tablo_print.html`: a clean, ink-efficient printable protocol with a dedicated print stylesheet (the shell chrome dropped for print).

Out of scope: judging and projector screens (separate world changes); token/shell (owned by `redesign-foundation`); any change to registration/draw logic.

## Capabilities

### New Capabilities

- `admin-tables-ui`: the list/detail and printable-protocol contract — scannability, row actions, status legibility, print output.
- `entry-forms-ui`: the sign-in and registration form contract — labels, focus, inline errors, speed.

### Modified Capabilities

_None._

## Impact

- **Code**: `tablo/templates/tablo/tablo_list.html`, `tablo_detail.html`, `tablo_print.html`, `participant_create.html`, `login.html`; screen-scoped and print CSS in `style.css`.
- **Depends on**: `redesign-foundation` (tokens + shell) merged first.
- **Behavior**: visual/interaction only; no change to registration, draw, or print data.
- **Execution**: a `/workflows` pass (Critique → Redesign → Audit → Verify), opus/sonnet (no Fable).
