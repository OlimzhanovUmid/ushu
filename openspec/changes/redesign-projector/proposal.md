# Proposal: redesign-projector

## Why

The projector/monitor screens are seen by the most people — the whole hall, plus athletes and spectators — from a distance, on a beamer. `PRODUCT.md` makes hall-legibility a first-class success metric ("legible across a hall") co-equal with the judge hot path. The monitor now pushes updates over SSE (`stabilize-django`), so the data pipeline is solid; this change is a full redesign of the four projector surfaces for glanceable, beyond-AA legibility on the tokens and shell from `redesign-foundation`.

## What Changes

- Redesign `monitor.html` (the public idle/standings screen): large display type, beyond-AA contrast, the current performer unmistakable, standings columns (rank / name / club / score) readable at distance.
- Redesign `monitor_doing.html` (current performer): the live athlete front and center with the gold current marker.
- Redesign `monitor_score.html` (live score): the just-landed score readable across the hall the moment it appears.
- Redesign `monitor_tablo.html` (per-tablo standings): standings table on the dark projector surface, ranks and finals clear, country flags rendered with a safe placeholder fallback.
- Enforce the anti-clutter line: no competing animations or broadcast-overlay noise; the eye lands on what matters.

Out of scope: the SSE transport and monitor state (owned by `stabilize-django`); judge and admin screens (separate world changes); token/shell (owned by `redesign-foundation`).

## Capabilities

### New Capabilities

- `monitor-display-ui`: the projector surface contract — display-type scale, beyond-AA contrast, current-performer marking, standings legibility at distance, anti-clutter.

### Modified Capabilities

_None._

## Impact

- **Code**: `tablo/templates/tablo/monitor.html`, `monitor_doing.html`, `monitor_score.html`, `monitor_tablo.html`; screen-scoped CSS in `style.css`.
- **Depends on**: `redesign-foundation` (tokens + shell) merged first; consumes the SSE snapshots from `stabilize-django`.
- **Behavior**: visual only; no change to what is pushed or when.
- **Execution**: a `/workflows` pass (Critique → Redesign → Audit → Verify), opus/sonnet (no Fable).
