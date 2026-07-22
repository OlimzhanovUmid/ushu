# Proposal: redesign-foundation

## Why

The full Django UI redesign is split into a shared foundation plus three surface "worlds" (judge hot path, projector, admin). The foundation must land first: every world screen consumes the same token system and app shell, so redesigning them before the shared layer is stable guarantees divergence and rework. `core/static/css/style.css` was partially redesigned already and `DESIGN.md` now captures the intended system — this change makes the tokens and the shell fully conform to that system so the worlds build on solid ground.

Scope is the Elixir rewrite-agnostic Django UI only; the `elixir/` project is untouched.

## What Changes

- Audit and refine the `style.css` token layer to fully match `DESIGN.md` frontmatter — colors, type scale (Inter 500→800), radius, shadow (navy-tinted), spacing — and remove Bootstrap-3 overrides that fight the system.
- Enforce the DESIGN.md named rules in the tokens: Gold-Means-Now (gold only for `current`), Cool-Ground (cool `#eef2f8` bg, no warm cream), Navy-Shadow, One-Family (Inter only).
- Rebuild the app shell (`base.html` + `base_tablo_wmenu.html`): navy topbar with the red brand block and `EVENT_TITLE`, token-derived sidebar with gold hover/active marker, layout offsets from `--topbar-h`/`--sidebar-w`/`--gutter`.
- Extract a documented, reusable component set (buttons, tables, inputs, labels, cards) matching `.impeccable/design.json` so the worlds reuse, not reinvent.
- Bake in the weak-client + accessibility budget: no font CDN (self-hosted/system stack), honor `prefers-reduced-motion`, cheap effects only.
- Fix `base.html` `lang="en"` → `ru`.

Out of scope: per-screen redesign (deferred to redesign-judge-hotpath / redesign-projector / redesign-admin); removing Bootstrap (keep the grid, restyle on top).

## Capabilities

### New Capabilities

- `design-tokens`: the canonical token set and the DESIGN.md conformance + contrast rules every screen obeys.
- `app-shell`: the topbar / sidebar / layout frame all authenticated screens inherit.

### Modified Capabilities

_None — these are the first UI-redesign specs._

## Impact

- **Code**: `core/static/css/style.css`, `core/templates/core/base.html`, `tablo/templates/tablo/base_tablo_wmenu.html`.
- **Design artifacts**: `DESIGN.md` / `.impeccable/design.json` are the normative reference; discrepancies found during the audit are reconciled into them.
- **Behavior**: no functional change; visual/structural only. Downstream world changes depend on this one.
- **Execution**: a `/workflows` pass (Critique → Redesign → Audit → Verify), opus/sonnet agents (no Fable).
