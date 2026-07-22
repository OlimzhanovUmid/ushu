# Tasks: redesign-judge-hotpath

_Depends on: redesign-foundation (tokens + shell) merged first._

## 1. Critique (baseline)

- [x] 1.1 `/impeccable critique` each of judgea/b/c, judge_empty, pnt_element, scores → mis-entry, speed, target findings
- [x] 1.2 Consolidate findings into a ranked backlog

## 2. Entry screens redesign (judge-entry-ui)

- [x] 2.1 Redesign `judgea.html` — large single score control + obvious submit, gold current participant
- [x] 2.2 Redesign `judgeb.html` — same entry vocabulary
- [x] 2.3 Redesign `judgec.html` — element tree with per-element marking, gold active element, visible completeness gate
- [x] 2.4 Redesign `judge_empty.html` — calm, legible waiting state
- [x] 2.5 Redesign `pnt_element.html` — element-points helper aligned to the entry vocabulary

## 3. Stage breakdown redesign (score-breakdown-ui)

- [x] 3.1 Redesign `scores.html` — dark stage, >AA contrast, gold main mark, semantic status colors legible

## 4. Verify

- [x] 4.1 Audit: target size, contrast (stage >AA), reduced-motion, weak-client budget
- [x] 4.2 Adversarial: can a wrong score be submitted by accident? is "current" unmistakable? does the C gate block visibly?
- [x] 4.3 Screenshot each screen; confirm against DESIGN.md and PRODUCT.md hot-path metric
