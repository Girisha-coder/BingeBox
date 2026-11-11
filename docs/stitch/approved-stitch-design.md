# User-approved Stitch palette direction

Approved in chat on 21 October 2026 after the first concept preview. This file preserves Stitch's own generated design system; it is not an existing BingeBox layout and was not supplied to the initial generation. Component/features mentioned below are concept output, not approved additions to project scope.

---
name: Cinematic Obsidian
colors:
  surface: '#11131d'
  surface-dim: '#11131d'
  surface-bright: '#373844'
  surface-container-lowest: '#0c0e18'
  surface-container-low: '#191b26'
  surface-container: '#1d1f2a'
  surface-container-high: '#282934'
  surface-container-highest: '#323440'
  on-surface: '#e1e1f0'
  on-surface-variant: '#c6c5d6'
  inverse-surface: '#e1e1f0'
  inverse-on-surface: '#2e303b'
  outline: '#908f9f'
  outline-variant: '#454654'
  surface-tint: '#bdc2ff'
  primary: '#bdc2ff'
  on-primary: '#03139f'
  primary-container: '#4f5cd8'
  on-primary-container: '#e9e9ff'
  inverse-primary: '#4350cc'
  secondary: '#bdc2ff'
  on-secondary: '#131f8b'
  secondary-container: '#2f3aa2'
  on-secondary-container: '#a7afff'
  tertiary: '#b9c8de'
  on-tertiary: '#233143'
  tertiary-container: '#5c6b7e'
  on-tertiary-container: '#dfecff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dfe0ff'
  primary-fixed-dim: '#bdc2ff'
  on-primary-fixed: '#000767'
  on-primary-fixed-variant: '#2835b3'
  secondary-fixed: '#dfe0ff'
  secondary-fixed-dim: '#bdc2ff'
  on-secondary-fixed: '#000766'
  on-secondary-fixed-variant: '#2f3aa2'
  tertiary-fixed: '#d4e4fa'
  tertiary-fixed-dim: '#b9c8de'
  on-tertiary-fixed: '#0d1c2d'
  on-tertiary-fixed-variant: '#39485a'
  background: '#11131d'
  on-background: '#e1e1f0'
  surface-variant: '#323440'
typography:
  display-hero:
    fontFamily: Syne
    fontSize: 64px
    fontWeight: '800'
    lineHeight: 72px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Syne
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Syne
    fontSize: 44px
    fontWeight: '700'
    lineHeight: 52px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Syne
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Syne
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0.01em
  label-caps:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.12em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 3.5rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes an ultra-premium, cinematic streaming environment tailored for cinephiles, entertainment connoisseurs, and contemporary viewers who expect immersion over utility clutter. The interface disappears behind the content, evoking the physical ambiance of an elite private screening room—dark, focused, and acoustically pure.

The design language balances **Editorial Minimalism** with **Luminous Glassmorphism**. Layouts leverage expansive aspect-ratio viewports, deliberate micro-borders, deep canvas layering, and focused bursts of electric indigo to signal interactivity. Every frame feels intentional, high-production, and dignified. Visual noise is aggressively eliminated to maximize dynamic range between the deep canvas and rich key art.

## Colors

The palette is anchored in an unyielding void—a true black canvas (`#000000`) engineered for OLED contrast. Structural depth relies on cold obsidian surface tiers (`#0A0C16`, `#121528`, `#181C38`) rather than artificial drop shadows.

- **Primary Accent (`#4F5CD8` / `#3E49B0`):** Electric indigo serves as the singular vehicle for actionable states, active scrub bars, focus halos, and primary invitations.
- **Secondary Titanium Slate (`#94A3B8` / `#64748B`):** Restrained metallics provide clear hierarchy for metadata, runtimes, cast listings, and secondary descriptors without competing with bright white titles.
- **Typography & Canvas:** High-contrast pure white (`#FFFFFF`) commands lead titles and active controls, set against the zero-luminance canvas to preserve cinematic weight.
- **Micro-Gradients & Glows:** Used sparingly at `12%–24%` opacity behind hero art transitions to fuse background obsidian layers directly with streaming content.

## Typography

The type system creates a dynamic juxtaposition between theatrical drama and razor-sharp modern interface engineering.

- **Headlines (`Syne`):** High-impact, sculptural display letterforms command hero banners, editorial collections, and premier feature titles. Negative letter-spacing gives major headlines an architectural, poster-like presence.
- **Interface & Body (`Plus Jakarta Sans`):** Selected for its geometric clarity and open apertures, preserving legibility at micro-sizes across television distances, tablet screens, and compact mobile interfaces.
- **Metadata Labels (`label-caps`):** Formatted in structural uppercase with wide tracking (`0.12em`) to ground audio badges (4K UHD, HDR10, ATMOS), release dates, and studio attributions without competing against show names.

## Layout & Spacing

The layout is built upon a flexible 12-column fluid grid system paired with horizontal scroll carousels that bleed past margins to cue continuous discovery.

- **Desktop (1440px+):** 12-column grid, `3.5rem` canvas margins, and `1.5rem` gutters. Content rows use generous vertical separation (`space-xl` or `4rem`) to allow cover art to breathe.
- **Tablet (768px – 1439px):** 8-column layout with `2rem` outer padding, collapsing hero banners into centered 16:9 cinematic spotlights.
- **Mobile (< 768px):** 4-column layout with `1.25rem` margins and `1rem` gutters. Navigation docks to a glassmorphic bottom bar, and poster rails default to a multi-card peek ratio.
- **Edge Bleed:** Horizontal rails must break past right-side page margins by half a card width, inviting swipe and scroll behavior.

## Elevation & Depth

Spatial depth is achieved through structural layering and optical luminance rather than heavy drop shadows.

- **Obsidian Tiering:**
  - **Base Canvas:** Pure Black (`#000000`) represents resting space and infinite edge transitions.
  - **Surface Level 1:** Deep Obsidian (`#0A0C16`) forms card backings, side rails, and drawer panels.
  - **Surface Level 2:** Mid Obsidian (`#121528`) handles hover surfaces and expanded modals.
  - **Surface Level 3:** Elevated Slate (`#181C38`) serves nested components, badge grounds, and tooltip overlays.
- **Micro-Borders:** Every surface tier is delimited by a 1px hairline border (`rgba(255, 255, 255, 0.08)` on rest; `rgba(79, 92, 216, 0.6)` on focus).
- **Glassmorphism Layers:** Floating header bars and overlay badges utilize translucent backdrops (`rgba(10, 12, 22, 0.75)`) combined with an active `20px` background blur.
- **Indigo Atmospheric Glow:** Focused or active elements project an ambient diffuse aura: `box-shadow: 0 0 32px -4px rgba(79, 92, 216, 0.35)`.

## Shapes

The design system maintains a balanced geometry (`roundedness: 2` / base `8px`), combining the structural authority of classic cinema displays with tactile contemporary touch targets.

- **Base Cards & Modules:** `0.5rem` (`8px`) border-radius preserves the crisp, rectangular aspect ratios of standard film stills (16:9, 2:3, and 21:9 ultra-wide).
- **Overlays, Drawers & Modals:** `1rem` (`16px`) for larger floating surfaces to soften large transitions.
- **Controls & Badges:** Interactive buttons, search inputs, tags, and chips take on fully rounded pill profiles (`9999px`) to create clear differentiation between clickable tools and viewable content.

## Components

### Buttons
- **Primary Action (Play / Resume):** High-contrast pure white fill (`#FFFFFF`) with deep black text (`#000000`), pill shape, bold weight, with an electric indigo shadow on hover.
- **Secondary Action (Add to List / Info):** Translucent glass fill (`rgba(255, 255, 255, 0.08)`), pure white text, 1px perimeter border (`rgba(255, 255, 255, 0.15)`), shifting to solid slate border on hover.
- **Icon / Control Pills:** Circular or pill-shaped, `44px` minimum hit area, housing SVG icons centered with strict 1:1 ratios.

### Cards (Film Ratios)
- **Portrait Poster (2:3 Ratio):** Standard catalog card. Features smooth zoom on hover (`scale 1.03`), glowing indigo border outline, and a bottom gradient vignette revealing metadata on hover.
- **Landscape Backdrop (16:9 Ratio):** Episode selections, watch history, and documentary formats. Includes integrated progress scrub bar pinned to the bottom border (`#4F5CD8` fill over `#181C38` base).
- **Featured Billboard (21:9 or 16:9 Dynamic):** Hero canvas card featuring seamless right-and-bottom opacity mask bleeding into `#000000`.

### Chips & Badges
- **Technical Badges (4K, HDR, Dolby):** Frosted capsule with 1px border (`rgba(255, 255, 255, 0.12)`), uppercase `label-caps` typography, `space-xs` vertical and `space-sm` horizontal padding.
- **Editorial Chips (Genres, Moods):** Interactive pill shapes, low-contrast slate background, transforming to electric indigo on selection.

### Form Inputs & Search
- **Search Bar:** Pill-shaped glass container (`rgba(18, 21, 40, 0.8)`) with `1px` border (`rgba(255, 255, 255, 0.1)`), glowing electric indigo hairline on focus.
- **Checkboxes & Radios:** `20px` squircle (`4px` radius) or circle, solid `#121528` background with an active indigo fill and check glyph.

### Scrubbers & Sliders
- Minimal `4px` height track in deep obsidian (`#181C38`), active timeline highlighted in electric indigo (`#4F5CD8`), and an elevated `12px` circular white scrubbing thumb with glow accent.