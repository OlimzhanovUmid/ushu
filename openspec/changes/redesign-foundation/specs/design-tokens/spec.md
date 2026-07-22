# design-tokens

## ADDED Requirements

### Requirement: Tokens are the single source of truth
All color, typography, radius, shadow, and spacing values SHALL be defined as CSS custom properties in `style.css` matching the `DESIGN.md` frontmatter; screen and component CSS SHALL reference those tokens and SHALL NOT hardcode literal color, radius, or shadow values.

#### Scenario: A screen needs the brand color
- **WHEN** a screen styles a primary action
- **THEN** it uses `var(--c-primary)`, not `#2f6df6`

#### Scenario: A token drifts from DESIGN.md
- **WHEN** the audit finds a `style.css` value that disagrees with the DESIGN.md frontmatter
- **THEN** the two are reconciled to one value (token corrected, or DESIGN.md corrected), never left split

### Requirement: Contrast conformance
Body text SHALL meet ≥4.5:1 against its background and large text ≥3:1; the stage/monitor token combinations SHALL exceed AA (target ≥7:1) for hall-distance legibility. Placeholder text SHALL meet the same 4.5:1 as body.

#### Scenario: Muted text on tinted surface
- **WHEN** muted-slate text is placed on the cool field background
- **THEN** the pair measures ≥4.5:1 or the text color is bumped toward ink

### Requirement: Gold is reserved for "current"
The gold token SHALL be applied only to mark what is currently active (live athlete, active element, main mark), per the DESIGN.md Gold-Means-Now Rule; it SHALL NOT be used decoratively.

#### Scenario: Two golds on one screen
- **WHEN** gold appears in more than one meaning on a single screen
- **THEN** that is a defect and one usage is removed

### Requirement: Cool ground and single family
The app background token SHALL stay cool (`#eef2f8`-class), never a warm cream/beige; the type system SHALL use Inter in weights 500–800 as the only family, with hierarchy carried by weight and size, not a second typeface.

#### Scenario: Warmth requested
- **WHEN** a "warmer" look is wanted
- **THEN** warmth comes from accent/typography, and the body background stays cool

### Requirement: Weak-client and reduced-motion budget
The foundation SHALL NOT load fonts from an external CDN (offline LAN), SHALL keep effects cheap enough for underpowered clients, and every animation SHALL provide a `prefers-reduced-motion: reduce` alternative (crossfade or instant).

#### Scenario: Reduced motion
- **WHEN** a client requests reduced motion
- **THEN** transitions degrade to instant/crossfade and no content visibility depends on an animation firing
