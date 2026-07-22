# Tasks: redesign-judge-hotpath

_Depends on: redesign-foundation (tokens + shell) merged first._

## 1. Critique (baseline)

- [ ] 1.1 `/impeccable critique` each of judgea/b/c, judge_empty, pnt_element, scores → mis-entry, speed, target findings
- [ ] 1.2 Consolidate findings into a ranked backlog

## 2. Entry screens redesign (judge-entry-ui)

- [ ] 2.1 Redesign `judgea.html` — large single score control + obvious submit, gold current participant
- [ ] 2.2 Redesign `judgeb.html` — same entry vocabulary
- [ ] 2.3 Redesign `judgec.html` — element tree with per-element marking, gold active element, visible completeness gate
- [ ] 2.4 Redesign `judge_empty.html` — calm, legible waiting state
- [ ] 2.5 Redesign `pnt_element.html` — element-points helper aligned to the entry vocabulary

## 3. Stage breakdown redesign (score-breakdown-ui)

- [ ] 3.1 Redesign `scores.html` — dark stage, >AA contrast, gold main mark, semantic status colors legible

## 4. Verify

- [ ] 4.1 Audit: target size, contrast (stage >AA), reduced-motion, weak-client budget
- [ ] 4.2 Adversarial: can a wrong score be submitted by accident? is "current" unmistakable? does the C gate block visibly?
- [ ] 4.3 Screenshot each screen; confirm against DESIGN.md and PRODUCT.md hot-path metric
