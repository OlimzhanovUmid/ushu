# Design: redesign-foundation

## Context

Django 6 / Python 3.14, Bootstrap-3 base with a partially-completed modern theme in `core/static/css/style.css`. `PRODUCT.md` (register: product, platform: web) and `DESIGN.md` ("The Federation Standard") define the target system. The app renders through one shell template (`base.html`) and a menu variant (`base_tablo_wmenu.html`); layout offsets already derive from tokens (`--topbar-h`, `--sidebar-w`, `--gutter`). This change locks the shared layer so the three world redesigns are pure consumers.

## Goals / Non-Goals

**Goals:**
- `style.css` tokens are the single source of truth and fully match `DESIGN.md` frontmatter.
- The shell (topbar + sidebar + offsets) is one coherent, token-driven frame.
- A reusable component vocabulary exists, matching `.impeccable/design.json`.
- Contrast, reduced-motion, and weak-client budgets are enforced at the foundation, inherited everywhere.

**Non-Goals:**
- No per-screen redesign (worlds 1–3 own that).
- No Bootstrap removal — keep the grid, restyle on top.
- No functional/behavioral change.
- No Elixir/LiveView work.

## Decisions

### D1. Tokens hex-canonical, DESIGN.md is the reference
The `style.css` custom properties stay hex (Stitch-compatible, matches the current file). Any value that drifts from `DESIGN.md` is reconciled *into* the tokens, and if DESIGN.md itself is wrong, it is corrected — one source of truth, no split.

### D2. Restyle Bootstrap, don't fight it
Keep Bootstrap's grid and structural classes; override only the visual layer through tokens. Rationale: full removal is a throwaway cost given the eventual Elixir rewrite, and the grid already carries the layouts.

### D3. Foundation before worlds
This change must merge before redesign-judge-hotpath / redesign-projector / redesign-admin start, so they consume stable tokens and shell. The worlds do not re-open foundation files except to add screen-scoped CSS.

## Execution — /workflows pass

Multi-agent, opus/sonnet only (no Fable):

```
phase Critique  parallel: audit style.css vs DESIGN.md; audit shell markup
phase Redesign  refine tokens → rebuild shell → extract components
phase Audit     contrast (AA body, >AA stage tokens), reduced-motion, weak-client budget
phase Verify    adversarial: does every token trace to DESIGN.md? any literal color left?
```

## Risks

- Token changes ripple to every screen; visual regressions possible. Mitigation: the worlds re-verify their own screens after consuming.
- Bootstrap override specificity wars. Mitigation: scope overrides, avoid `!important` beyond existing uses.
