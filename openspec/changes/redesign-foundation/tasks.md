# Tasks: redesign-foundation

## 1. Token audit & refinement (design-tokens)

- [ ] 1.1 Audit `style.css` custom properties against `DESIGN.md` frontmatter; list every drift (color/type/radius/shadow/spacing)
- [ ] 1.2 Reconcile each drift to a single source (fix token or fix DESIGN.md); update `.impeccable/design.json` to match
- [ ] 1.3 Sweep for literal color/radius/shadow values in CSS; replace with `var(--token)`
- [ ] 1.4 Verify contrast on every token pair (body ≥4.5:1, large ≥3:1, stage/monitor >AA); bump failing text toward ink
- [ ] 1.5 Enforce Gold-Means-Now, Cool-Ground, One-Family in the token layer and comments

## 2. App shell rebuild (app-shell)

- [ ] 2.1 Rebuild `base.html`: token-driven topbar (red brand block + `EVENT_TITLE`), sidebar, offsets; set `lang="ru"`
- [ ] 2.2 Align `base_tablo_wmenu.html` to the same shell; remove per-screen margin hacks
- [ ] 2.3 Sidebar nav states: 82% white → full white + gold left marker on hover/active
- [ ] 2.4 Confirm no external font CDN; system/self-hosted stack only

## 3. Shared components (design-tokens)

- [ ] 3.1 Consolidate button variants (primary / red / white / link) on tokens, matching `.impeccable/design.json`
- [ ] 3.2 Consolidate table, input, label, card styles on tokens
- [ ] 3.3 Add `prefers-reduced-motion` alternatives for every transition

## 4. Verify

- [ ] 4.1 Every token traces to DESIGN.md; zero literal colors remain (adversarial pass)
- [ ] 4.2 Contrast + reduced-motion checks pass
- [ ] 4.3 Screenshot the shell (light) and confirm against DESIGN.md; hand off to world changes
