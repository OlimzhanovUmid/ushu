# Tasks: redesign-projector

_Depends on: redesign-foundation (tokens + shell) merged first. Consumes SSE snapshots from stabilize-django._

## 1. Audit (baseline)

- [x] 1.1 `/impeccable audit` each of monitor, monitor_doing, monitor_score, monitor_tablo → contrast, distance legibility, clutter
- [x] 1.2 Consolidate findings into a ranked backlog

## 2. Projector redesign (monitor-display-ui)

- [x] 2.1 Redesign `monitor.html` — display-scale idle/standings, >AA contrast, current performer primacy
- [x] 2.2 Redesign `monitor_doing.html` — live athlete centered, gold current marker
- [x] 2.3 Redesign `monitor_score.html` — just-landed score readable across the hall
- [x] 2.4 Redesign `monitor_tablo.html` — standings table on dark surface, ranks/finals clear, safe flag placeholder

## 3. Verify

- [x] 3.1 Audit: contrast >AA, simulated-distance legibility, projector aspect (4:3 + 16:9), reduced-motion
- [x] 3.2 Adversarial: readable at ~20 m? current unmistakable? any competing motion or overlay clutter?
- [x] 3.3 Screenshot each screen at projector aspect; confirm against DESIGN.md and PRODUCT.md hall-legibility metric
