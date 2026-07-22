# Tasks: redesign-admin

_Depends on: redesign-foundation (tokens + shell) merged first._

## 1. Critique (baseline)

- [x] 1.1 `/impeccable critique` tablo_list, tablo_detail, participant_create; audit tablo_print; scope login to a polish pass
- [x] 1.2 Consolidate findings into a ranked backlog

## 2. Tables & protocol redesign (admin-tables-ui)

- [x] 2.1 Redesign `tablo_list.html` — scannable token table, clear per-row actions and status
- [x] 2.2 Redesign `tablo_detail.html` — same table vocabulary; destructive actions marked red and separated
- [x] 2.3 Redesign `tablo_print.html` — dedicated print stylesheet, chrome dropped, ink-efficient protocol

## 3. Forms redesign (entry-forms-ui)

- [x] 3.1 Redesign `participant_create.html` — labeled fields, visible focus, inline field-level errors
- [x] 3.2 Polish `login.html` — align to finalized foundation tokens (no rebuild)

## 4. Verify

- [x] 4.1 Audit: table scannability, form a11y (labels/focus/inline errors), contrast, print output
- [x] 4.2 Adversarial: is grid state clear at a glance? are errors specific + inline? does print drop chrome?
- [x] 4.3 Screenshot each screen (and a print/PDF render); confirm against DESIGN.md
