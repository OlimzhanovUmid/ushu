# Proposal: redesign-judge-hotpath

## Why

The judge-entry screens are the hot path: A/B/C judges enter live scores for the athlete currently performing, under time pressure, on weak LAN clients, and must never submit a wrong value by accident. `PRODUCT.md` makes this a first-class success metric ("fast and mistake-proof"). The current screens are minimally themed Bootstrap. This change is a full redesign of the entire judging surface — data entry (A/B/C), the waiting state, the element-points helper, and the dark score-breakdown stage — on the tokens and shell from `redesign-foundation`.

## What Changes

- Redesign `judgea.html` / `judgeb.html` / `judgec.html`: oversized, unambiguous score controls; the active participant and (for C) active element marked with gold; the C-judge completeness gate surfaced clearly so an incomplete card cannot be submitted by accident.
- Redesign `judge_empty.html`: a calm, legible waiting state ("no active participant") that reads at a glance and never looks broken.
- Redesign `pnt_element.html`: the element-points helper aligned to the same entry vocabulary.
- Redesign `scores.html`: the immersive dark stage breakdown — high-contrast white-on-navy, gold main mark, per-judge marks legible.
- Bake in speed: minimal steps from "athlete performing" to "score submitted"; large targets sized for fast, error-free interaction.

Out of scope: scoring logic/aggregation (owned by `stabilize-django`); the projector and admin screens (separate world changes); token/shell changes (owned by `redesign-foundation`).

## Capabilities

### New Capabilities

- `judge-entry-ui`: the visual/interaction contract of the A/B/C entry screens and the waiting state — target size, current-focus marking, mistake-proofing, speed.
- `score-breakdown-ui`: the dark stage score-breakdown screen contract — contrast, hierarchy, gold main mark.

### Modified Capabilities

_None._

## Impact

- **Code**: `tablo/templates/tablo/judgea.html`, `judgeb.html`, `judgec.html`, `judge_empty.html`, `pnt_element.html`, `scores.html`; screen-scoped CSS in `style.css`.
- **Depends on**: `redesign-foundation` (tokens + shell) merged first.
- **Behavior**: visual/interaction only; no change to what a score means or how it aggregates.
- **Execution**: a `/workflows` pass (Critique → Redesign → Audit → Verify), opus/sonnet (no Fable).
