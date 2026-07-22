# Design: redesign-admin

## Context

The setup surfaces are used on a laptop (not the projector, not the time-pressured carpet): sign-in, participant registration, the tablo list/detail grid, and printable protocols. These are ordinary product-admin screens where the existing token table style already gets most of the way. `login.html` was partially redesigned already. This change is markup + screen-scoped/print CSS only, consuming `redesign-foundation` tokens.

## Goals / Non-Goals

**Goals:**
- The tablo grid and its state are scannable at a glance; row actions are clear.
- Registration is fast, with labels/focus/inline errors that catch mistakes at entry.
- Sign-in matches the finalized foundation.
- The printable protocol is clean and ink-efficient.

**Non-Goals:**
- No registration/draw/print logic change.
- No token/shell edits (that is `redesign-foundation`).
- No judge or projector screens.
- `login.html` is a polish pass, not a rebuild.

## Decisions

### D1. Tables over cards for the grid
The tablo list/detail stays tabular (the token `.table` style), not card grids. Rationale: DESIGN.md — cards are the lazy answer; a competition grid is inherently tabular and scans better as a table.

### D2. Inline, specific form errors
Registration errors render inline next to the field with specific messages (a `clarify` pass), not a generic top banner. Rationale: catch entry mistakes at the point of entry.

### D3. Dedicated print stylesheet for protocols
`tablo_print.html` gets a print stylesheet that drops the shell chrome (topbar/sidebar), maximizes ink-efficiency, and preserves the standings structure. Rationale: a printed protocol is a different medium than the screen.

## Execution — /workflows pass

opus/sonnet only (no Fable):

```
phase Critique  parallel: /impeccable critique list/detail/register; polish login; audit print
phase Redesign  pipeline: screen → markup+CSS redesign on foundation tokens (login: polish only)
phase Audit     parallel: table scannability, form a11y (labels/focus/errors), print output, contrast
phase Verify    adversarial: is the grid state clear? are form errors specific + inline? does print drop chrome?
```

## Risks

- Print CSS regressions are easy to miss on screen. Mitigation: verify with an actual print/PDF render.
- Over-redesigning login when it only needs polish. Mitigation: scope login to token alignment.
