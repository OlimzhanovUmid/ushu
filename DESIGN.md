---
name: Ushu Federation Scoring
description: Authoritative, calm scoring system for live wushu competitions — one screen from draw to results to projector.
colors:
  primary: "#2f6df6"
  primary-dark: "#1e4fd0"
  navy: "#0b1f3a"
  navy-2: "#122a4d"
  accent: "#ef3e4a"
  accent-dark: "#c92f3a"
  gold: "#f5b53d"
  bg: "#eef2f8"
  surface: "#ffffff"
  ink: "#1b2430"
  muted: "#6b7787"
  border: "#e3e8f0"
  status-ok: "#2f6df6"
  status-warn: "#f59e0b"
  status-fail: "#1b2430"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(3rem, 8vw, 6rem)"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontWeight: 700
    fontSize: "26px"
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontWeight: 600
    fontSize: "19px"
    lineHeight: 1.25
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontWeight: 500
    fontSize: "16px"
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontWeight: 600
    fontSize: "12px"
    lineHeight: 1.4
    letterSpacing: "0.04em"
rounded:
  sm: "6px"
  md: "10px"
  lg: "16px"
spacing:
  gutter: "32px"
  sm: "14px"
  md: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "13px 18px"
  button-primary-hover:
    backgroundColor: "{colors.primary-dark}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "13px 18px"
  button-red:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "13px 18px"
  button-white:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "13px 18px"
  table:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "13px 14px"
  label-current:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.navy}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
---

# Design System: Ushu Federation Scoring

## 1. Overview

**Creative North Star: "The Federation Standard"**

This is the visual language of an official sports federation running a live competition — structured, ceremonial, and trustworthy under pressure, without ever raising its voice. A deep navy shell frames every screen like the border of a crest; an electric blue does the working (links, primary actions, default scoring state); a competition red marks the identity and the moments that demand attention; and a single gold accent is reserved for one job only — the athlete or element that is *current*. The system reads as an instrument of record first and an interface second.

It runs on a LAN: one server laptop, roughly ten underpowered clients, and a projector in the hall. So the aesthetic is deliberately economical. Depth comes from soft, navy-tinted shadows lifting cards and tables off a cool `#eef2f8` background — never from glass, gradients-for-decoration, or motion for its own sake. The two registers live in one system: the light app screens are a calm workbench for judges and organizers; the dark stage and monitor screens turn immersive for distance legibility, where the moment earns the drama.

It explicitly rejects the consumer-SaaS dashboard (playful gradients, illustrated mascots, marketing flourish), the flat gray Bootstrap-admin default it is being redesigned away from, the cluttered TV-broadcast scoreboard (competing overlays and animations), and lifeless enterprise gray (tiny gray text at ERP density). Officialdom, not decoration.

**Key Characteristics:**
- Navy-framed shell with a red identity block and a single gold "current" accent
- Two registers in one system: calm light workbench, immersive dark stage/monitor
- Soft ambient shadows for structure; no glass, no decorative gradients
- Tactile, confident controls sized for fast, mistake-proof judge entry
- Light enough to stay fast on weak LAN clients and old browsers

## 2. Colors

A federation palette: navy authority, electric-blue utility, competition red for identity, and one gold reserved for the live moment — on a cool near-white ground.

### Primary
- **Electric Blue** (#2f6df6): The working color. Links, primary buttons, focus rings, and the default/untouched scoring state (`status-ok`). It carries interaction, not identity. Deepens to **Electric Blue Deep** (#1e4fd0) on hover/active and in the sign-in gradient.

### Secondary
- **Competition Red** (#ef3e4a): The identity accent. The brand block in the topbar and destructive/negative actions (`btn-red`). Deepens to **Competition Red Deep** (#c92f3a) on hover. Used sparingly — it signals "this is the federation" and "this is consequential", nothing else.

### Tertiary
- **Federation Gold** (#f5b53d): Reserved for one meaning — *current*. The `label-current` highlight ring, the live element being judged, the main mark on the score-breakdown screen, and the active hover accent inside dark surfaces. Its rarity is the entire point.

### Neutral
- **Deep Navy** (#0b1f3a) and **Navy 2** (#122a4d): The shell — topbar, sidebar, and the base of every dark stage/monitor gradient. The frame of the crest.
- **Cool Field** (#eef2f8): The light app background. Cool, not warm — a workbench, not paper.
- **Surface White** (#ffffff): Cards, tables, inputs, the sign-in panel.
- **Ink** (#1b2430): Primary text; also the `status-fail` (failed element) color.
- **Muted Slate** (#6b7787): Secondary text, table header labels, captions. Never used for body copy that must be read at distance.
- **Hairline** (#e3e8f0): Borders and dividers.

### Semantic scoring
- **status-ok** (#2f6df6 / electric blue): element untouched / default.
- **status-warn** (#f59e0b / amber): element performed.
- **status-fail** (#1b2430 / ink): element failed.

### Named Rules
**The Gold-Means-Now Rule.** Gold (#f5b53d) is forbidden as decoration. It appears only to mark what is *current* — the live athlete, the active element, the main mark. If gold is on screen in more than one meaning, one of them is wrong.

**The Cool-Ground Rule.** The light background is cool (#eef2f8), never a warm cream or beige. Warmth is not this brand; officialdom is.

## 3. Typography

**Display / Body / Label Font:** Inter (with `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` fallback)

**Character:** One family, many weights. A single neutral, highly legible grotesque carries the whole system — no pairing, no serif, no decorative face. Legibility at a hall's distance and speed of scanning beat typographic personality here. Hierarchy comes from weight (500→800) and size, not from mixing families. Headings tighten tracking slightly (-0.01em to -0.02em); the projector display goes large and heavy.

### Hierarchy
- **Display** (800, clamp up to ~6rem, 1.05): The projector/monitor headline and giant score-entry numerals (`.input-heading` reaches 110px). Built to read across a hall.
- **Headline** (700, ~26px, 1.2): The topbar competition title (`navbar-text-secondary`) and screen H1s.
- **Title** (600–700, ~19px, 1.25): Card titles, the sign-in title, section headers.
- **Body** (500, 16px, 1.5): Default text and form inputs. Cap prose at 65–75ch. Note the base weight is 500, not 400 — the workbench text is a touch heavier for confidence and screen legibility.
- **Label** (600, 12px, +0.04em, uppercase): Table column headers and the sign-in subtitle. The only place tracking opens up.

### Named Rules
**The One-Family Rule.** Inter is the only typeface. Do not introduce a second family, a serif, or a display face for "personality" — hierarchy is weight and size. A second family would read as marketing, which this is not.

## 4. Elevation

Soft ambient layering. Surfaces are lifted off the cool `#eef2f8` ground by navy-tinted shadows so cards, tables, and the sign-in panel read as physical objects on a workbench — structural depth, not decoration. Shadows carry a navy hue (`rgba(11,31,58,...)`), not neutral black, so they belong to the palette. The dark stage and monitor screens drop shadows entirely; there, depth comes from radial-gradient glow and contrast instead.

### Shadow Vocabulary
- **Ambient Low** (`box-shadow: 0 1px 3px rgba(11,31,58,0.08)`): Resting lift for small controls and `btn-white`.
- **Ambient** (`box-shadow: 0 4px 16px rgba(11,31,58,0.10)`): Default card, table, and primary-button elevation.
- **Ambient High** (`box-shadow: 0 18px 50px rgba(11,31,58,0.18)`): The sign-in panel and modal-level surfaces that should float clearly above the page.

### Named Rules
**The Navy-Shadow Rule.** Shadows are tinted navy (`rgba(11,31,58,…)`), never neutral gray/black. A gray shadow reads as generic Bootstrap; the navy tint keeps depth on-brand.

## 5. Components

Tactile and confident: controls are generously sized and give clear physical feedback (lift on hover, press on `:active`), because the hot path is a judge entering a score fast and needing to trust the tap. Every state transition runs on a shared `0.16s ease`.

### Buttons
- **Shape:** Gently rounded (6px, `--radius-sm`).
- **Primary:** Electric blue fill, white text, 13px vertical padding, ambient shadow. The sign-in button (`btn-login`) uses a blue→deep-blue gradient and lifts 1px on hover.
- **Hover / Focus:** Primary deepens to #1e4fd0; buttons lift subtly and press down (`translateY(1px)`) on `:active`.
- **Red (`btn-red`):** Competition red fill for destructive/negative actions; deepens to #c92f3a.
- **White (`btn-white`):** White fill, blue text, hairline border — the quiet secondary. Inverts to blue-fill/white-text on hover.
- **Context inversion:** Link-buttons are blue on light surfaces; inside the topbar, sidebar, and dark stage screens they turn white and hover to gold.

### Cards / Containers
- **Corner Style:** 10px (`--radius`); the sign-in panel and modals use 16px (`--radius-lg`).
- **Background:** Surface white on the cool field.
- **Shadow Strategy:** Ambient (see Elevation). Tables clip their corners (`overflow: hidden`) so the rounded surface stays clean.
- **Border:** Hairline (#e3e8f0) where a divider is needed.
- **Internal Padding:** 13–16px in table cells; 40px on the sign-in panel.

### Tables
- **Header:** Pale `#f7f9fc` band, uppercase 12px muted-slate labels with +0.04em tracking, 2px hairline underline.
- **Rows:** 500-weight ink text, 1px hairline top borders, a soft `#f5f8ff` hover tint.
- **On the monitor screen:** the table goes transparent — white text, low-opacity white borders — so it reads as luminous data on the dark projector.

### Inputs / Fields
- **Style:** White fill, hairline border, 6px radius.
- **Focus:** Border shifts to electric blue with a 3px blue glow ring (`0 0 0 3px rgba(47,109,246,0.18)`).
- **Score-entry inputs:** Oversized and borderless (`.input-center` at 43px, `.input-heading` at 110px) — the number *is* the interface on the judging screens.

### Navigation
- **Shell:** Fixed navy topbar (72px) with a red gradient brand block on the left; fixed navy sidebar (232px). Layout offsets derive from tokens (`--topbar-h`, `--sidebar-w`, `--gutter`), not magic pixels.
- **Sidebar links:** 82%-opacity white, 500 weight; on hover they brighten to full white with a gold left-edge marker and a faint white wash.

### Stage & Monitor Screens (signature)
- **Stage** (`body.stage`): Immersive dark judging/score-breakdown screen — navy radial-glow gradient, 92%-opacity white text, color scoring labels reading on dark, gold for the main mark.
- **Monitor** (`body.monitor-screen`): The public projector — deep navy gradient, white 800-weight headline, transparent luminous table. Built for hall-distance legibility above AA.

## 6. Do's and Don'ts

### Do:
- **Do** reserve gold (#f5b53d) exclusively for *current* — the live athlete, active element, main mark. Its rarity is the meaning.
- **Do** keep the light background cool (#eef2f8); carry any warmth in nothing — this brand has none.
- **Do** tint shadows navy (`rgba(11,31,58,…)`) so depth stays on-brand.
- **Do** build hierarchy from Inter weights (500→800) and size alone.
- **Do** size the judging controls large and give clear press/hover feedback — the hot path must be fast and mistake-proof.
- **Do** push the stage/monitor screens beyond AA contrast for hall-distance legibility, and provide a `prefers-reduced-motion` fallback for any motion.
- **Do** keep runtime light — effects and JS must stay cheap for weak LAN clients and old browsers.

### Don't:
- **Don't** make it look like consumer SaaS or a startup dashboard — no playful gradients, illustrated mascots, or marketing flourish. This is an official event record.
- **Don't** fall back to generic gray Bootstrap-admin — the flat gray-box default this system is being redesigned away from.
- **Don't** build a cluttered broadcast scoreboard — no competing overlays or animations fighting for attention on the monitor.
- **Don't** drift to enterprise gray — no tiny gray text at ERP density; body text is 500-weight ink, not muted slate.
- **Don't** introduce a second typeface or a decorative display face; Inter is the only family.
- **Don't** use `border-left`/`border-right` greater than 1px as a colored accent stripe on cards or list items — the sidebar's gold edge marker is the one sanctioned exception, and it stays at 3px on a nav item, never on content cards.
- **Don't** use decorative glassmorphism or gradient text anywhere.
