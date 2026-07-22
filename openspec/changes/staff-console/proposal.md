# Proposal: staff-console

## Why

Staff (the main judge / secretary, and the registrar before an event) reach Django's raw admin through the new sidebar "Admin" link. That admin is generic model-CRUD — exactly the "generic Bootstrap admin / enterprise gray" that `PRODUCT.md` lists as an anti-reference — and it serves two very different jobs badly:

- **Setup** (pre-event, unhurried, low-risk): create judges with a category and `is_staff`, register clubs/countries, maintain the element/combination/error-code reference data, view/edit participants.
- **Live correction** (mid/post-event, urgent, irreversible): fix a wrong result, re-open a finished participation for re-entry, withdraw a mis-registered participation, retire a judge who already has scores. Here model-first CRUD with foreign-key dropdowns over 111 participants / 168 tablos / 1635 scores is slow and dangerous — one careless edit corrupts a competition result.

A **hybrid** wrapper fits: a small, task-first, mistake-proof **staff console** owning the 3–5 hot correction tasks, plus a **branded, more usable Django admin** for the long tail of setup/reference CRUD. Both on the "Federation Standard" shell so staff never drop into a generic-admin context.

Scope is the current Django app; the `elixir/` rewrite is untouched. The console's task taxonomy and guard patterns are portable concepts even though the code is not.

## What Changes

**Staff console (bespoke, task-first):**
- A console home listing the hot tasks in domain language (not model names), reachable from the sidebar "Admin" for `is_staff` users.
- **Find a participant** (search by name/club/tablo) → see their participations and per-judge score state.
- **Re-open a judge's slot** for a chosen participation so that judge can re-enter — generalizing today's `open_judge`, which only works for the currently-active participant, to any finished participation.
- **Re-open a whole participation** (un-finalize) for re-judging.
- **Withdraw a participation** (delete) behind an explicit, named confirmation — competition-red, irreversible-aware.
- **Retire a judge**: set `is_active=False` (never delete — scores are `PROTECT`-ed), framed as a task with the "why" surfaced.
- Every irreversible action confirms first; destructive controls are competition-red and separated from routine ones; large targets, Russian wording.

**Branded admin (styled long tail):**
- A custom `AdminSite` with base templates + CSS on the foundation tokens so the setup/reference CRUD escapes the generic-admin look.
- Domain-friendly Russian `verbose_name`s and useful `list_display`/`search_fields`/`list_filter` on the heavy models (Score, Participation) so the long tail is navigable.
- The "Admin" sidebar entry points at the console; the console links out to the styled admin for the rare surgical CRUD.

Out of scope: raw field-level score editing in the console (error-code M2M and C-element trees stay in the styled admin for the rare case); any scoring-logic change; the Elixir rewrite; new setup features (bulk import, championship entity).

## Capabilities

### New Capabilities

- `staff-console`: the task-first console — its task set, search, re-open/withdraw/retire flows, and mistake-proofing.
- `branded-admin`: the styled, domain-worded Django admin for the setup/reference long tail.

### Modified Capabilities

_None._

## Impact

- **Code**: new console views/urls/templates (likely under `tablo/` or a small `staff/` area), reusing `open_judge`/`delete_participation` logic and generalizing the re-open to any participation; `judges`/`tablo`/`clubs`/`elements`/`participants` `admin.py` (custom AdminSite registration, verbose names, list config); admin base template + CSS on tokens; the sidebar "Admin" link retargeted to the console.
- **Behavior**: adds a safer path for corrections currently only possible via raw admin; the generalized re-open touches finished participations (new capability), gated to `is_staff`. No scoring-logic change.
- **Depends on**: redesign-foundation tokens/shell (merged) and harden-errors-and-admin-access (the sidebar Admin link).
