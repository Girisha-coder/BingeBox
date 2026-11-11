# BingeBox: Stitch design ideas and motion review

Date: 21 October 2026.

**Implementation update:** Stitch is now the only interface at `/`. The original export review below is historical. The local integration implements scroll depth, viewport reveals, hover/focus feedback, a native quick-look dialog with keyboard focus containment/restoration, mobile layouts and reduced-motion support. It retains the real application workflows and removes unsupported concept claims. See [current design rules](../../DESIGN.md).

[Stitch project](https://stitch.withgoogle.com/projects/10648150967291044792) · [Concept image](original-concept.png) · [Raw prototype HTML](original-concept.html) · [Full Stitch explanation](stitch-explanation.md)

## Approved direction

The user approved the color theme after seeing the first Stitch concept. Retain that dark blue/obsidian, white and luminous indigo direction for future work. The original prompt specified #000000 / #FFFFFF / #2C3480; Stitch introduced additional dark surfaces and #4F5CD8 accents. The user's later approval is the current direction. The exact generated token set is preserved in [approved-stitch-design.md](approved-stitch-design.md).

The initial concept was generated from product requirements alone. No existing layouts, source code, screenshots, copy, typography or design reference sites were supplied. The user subsequently selected this design as the sole interface.

## Useful ideas from Stitch

1. A cinematic featured title with atmospheric artwork, clear metadata and immediate discovery/playback actions.
2. Landscape continue-watching cards with visible progress and time remaining, followed by a ranked discovery rail. Rankings must be by genre to match the actual application.
3. Layered translucent navigation and controls over dark surfaces, using the approved indigo for selected states.
4. Quick title details in an overlay so viewers retain their discovery context. This needs proper keyboard focus management before adoption.
5. Mobile adaptation with reachable navigation, swipeable rails and condensed filters. The generated desktop export does not establish that mobile behavior works.

## Motion: evidence versus proposal

The generated HTML was inspected directly. Stitch's prose sometimes describes more than its code implements; the following table reflects the code, not those claims.

| Interaction | Export status | Suggested implementation target |
| --- | --- | --- |
| Poster/image hover zoom | Present, generally 300ms Tailwind transitions | Add equivalent focus feedback; avoid hiding essential metadata |
| Button hover/press response | Present, typically 150–200ms with active scale | 120–200ms transform/opacity response |
| Ambient pulse | Present on a small status indicator | Optional; remove under reduced motion |
| Details overlay | Open/close and Escape handlers present | Add focus trapping, focus restoration, dialog semantics and a 250–360ms transition |
| Scroll-linked hero depth | Proposed only; no scroll-linked implementation found | Small transform range driven by native scroll; stop when off screen |
| Staggered section reveals | Requested, not implemented in first export | 400–550ms opacity/translate, 40–60ms stagger; reveal once |
| Horizontal discovery rail | Native overflow exists | Touch/trackpad scrolling, keyboard-accessible buttons and optional scroll snap |
| Reduced motion | CSS override present | Also gate any future JS animation and keep all content visible |

Stitch suggested a 0.35x hero parallax rate and a spring-like details transition. These remain ideas to tune, not verified animation behavior. Do not intercept wheel events or prevent native scrolling. Favor transform/opacity, avoid continuous layout work, and ensure a complete static alternative.

## Scope corrections before implementation

The concept is an exploratory mockup, not production-ready UI. Remove unsupported watchlist actions, regional rankings, HDR/Dolby/Atmos claims, offline downloads, invented plans and advanced staff features. Use real API metadata, preserve Unknown values, and keep simulated-payment/placeholder-media labels. Kids-mode exit requires the account password; the export's cosmetic toggle is not a valid security workflow. Completion eligibility is >=90%, not >90%. Search, filters and pagination need actual integration; many exported controls are decorative.

The raw HTML also relies on external Tailwind, font and image URLs. It is retained as received for inspection, not installed into the running application. Generated imagery has not been assessed for production rights or quality.

## Refinement outcome

A follow-up requested functional scroll motion, accessible interactions and scope corrections. The call returned `isError: true` with “The service is currently unavailable.” No successful revised prototype was received. Its prompt was sent before the user approved the broader first-concept palette, so its request to restore the earlier exact colors is superseded by that approval.

Stitch's suggested next explorations were a title-details drawer, a mobile discovery version, and a plan/device-management screen. These are optional design follow-ups; none has been generated or deployed here.
