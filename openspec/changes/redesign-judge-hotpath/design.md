# Design: redesign-judge-hotpath

## Context

The judge screens are reached after login (`JudgeView` at root) and post to per-category submit endpoints. A/B judges enter a single numeric score; C judges mark a tree of elements (each `done` tri-state: untouched / performed / failed) and are gated on completeness. `scores.html` is the dark "stage" breakdown. The redesign consumes `redesign-foundation` tokens/shell; it changes only markup and screen-scoped CSS, never scoring logic.

## Goals / Non-Goals

**Goals:**
- A correct score is fast to enter and a wrong one is hard to submit.
- The current athlete (and current element for C) is unmistakable.
- The waiting state is calm and obviously "waiting", not "broken".
- The stage breakdown reads at distance with the gold main mark.

**Non-Goals:**
- No scoring-logic change (that is `stabilize-django`).
- No token/shell edits (that is `redesign-foundation`).
- No projector or admin screens.

## Decisions

### D1. Big-target, single-focus entry
Score controls are oversized (the existing `.input-heading`/`.input-center` direction, generalized) with one obvious primary action per screen. Rationale: PRODUCT.md hot-path metric — speed + no mis-tap on weak clients.

### D2. Completeness gate is visible, not just server-side
`stabilize-django` added a server-side C-completeness gate. This redesign makes it visible: the submit affordance reads as disabled/blocked until every element is marked, so the judge never round-trips a rejected save mid-competition.

### D3. Gold marks "current" only
Active participant / active element use the gold token; nothing else does (DESIGN.md Gold-Means-Now).

## Execution — /workflows pass

opus/sonnet only (no Fable):

```
phase Critique  parallel: /impeccable critique each of the 6 screens → mis-entry + speed + target findings
phase Redesign  pipeline: screen → full markup+CSS redesign on foundation tokens
phase Audit     parallel: target size, contrast (scores stage >AA), reduced-motion, weak-client
phase Verify    adversarial: can a wrong score be submitted by accident? is current unmistakable?
```

## Risks

- Larger targets vs. dense element trees for C — balance density and tap size. Mitigation: verify on the real C card depth.
- Weak-client render cost of a heavier stage screen. Mitigation: audit budget gate.
