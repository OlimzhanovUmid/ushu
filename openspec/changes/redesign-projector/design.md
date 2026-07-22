# Design: redesign-projector

## Context

The monitor screens render on a beamer in the hall, driven by SSE snapshots the secretary pushes (`stabilize-django`). `body.monitor-screen` already establishes a dark navy gradient with a transparent luminous table. Viewers are 5–30 m away; text that is comfortable on a laptop is illegible at that distance. This redesign is markup + screen-scoped CSS only, consuming `redesign-foundation` tokens.

## Goals / Non-Goals

**Goals:**
- Everything critical (current performer, live score, ranks) reads across the hall.
- Contrast exceeds AA (target ≥7:1) for beamer washout headroom.
- The current performer is unmistakable.
- No clutter — one clear focus, no competing motion.

**Non-Goals:**
- No SSE/transport change (that is `stabilize-django`).
- No token/shell edits (that is `redesign-foundation`).
- No judge or admin screens.

## Decisions

### D1. Display-type scale for distance
Headline/score type uses the display token (clamp up to ~6rem) so it survives beamer downscaling and distance. Rationale: PRODUCT.md hall-legibility metric; laptop-comfortable sizes fail at 20 m.

### D2. Beyond-AA contrast, beamer headroom
Target ≥7:1 on the dark surface, not just AA, because beamers wash out and ambient hall light varies. White/gold on deep navy carries it.

### D3. Anti-clutter over broadcast tropes
No competing animations, no TV-scoreboard overlays (PRODUCT.md anti-reference). Motion only where it aids reading (a new score landing), always with a reduced-motion fallback.

## Execution — /workflows pass

opus/sonnet only (no Fable):

```
phase Critique  parallel: /impeccable audit each of the 4 monitor screens → contrast + distance + clutter
phase Redesign  pipeline: screen → full markup+CSS redesign on foundation tokens
phase Audit     parallel: contrast (>AA), simulated-distance legibility, projector aspect, reduced-motion
phase Verify    adversarial: readable at 20 m? is current unmistakable? any competing motion?
```

## Risks

- Projector aspect ratios vary (4:3, 16:9). Mitigation: responsive to aspect, verify both.
- Flag images missing for some countries. Mitigation: safe placeholder fallback (already required by stabilize-django's render-safety); the redesign must honor it.
