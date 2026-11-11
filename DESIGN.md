# BingeBox design

Stitch is the only application interface, selected by the user on 21 October 2026. Open http://localhost:18080. Saved variant URLs normalize to the corresponding root route, preserving query strings and fragments.

## Visual language

- Obsidian canvas `#0c0e18`, elevated surfaces `#191b26`, light text `#e1e1f0`, muted text `#a7aabc`, indigo actions `#4f5cd8` and light indigo highlights `#bdc2ff`.
- Locally bundled Syne for headings and Plus Jakarta Sans for interface text. No remote font requests.
- Featured title with atmospheric backdrop, a secondary discovery card, restrained pill controls and spacious catalogue sections. Real API titles, genres, years and ratings replace generated prototype claims.
- Each catalogue title has a stable local cover. Verified promotional posters retain their aspect ratio; unavailable matches use distinct, labelled illustrative covers. New administrator-created titles get a deterministic numbered gradient until artwork is supplied. See [artwork provenance](docs/catalogue-artwork.md).
- The first six fictional spotlight titles have their own wide illustrative images. Each belongs to one title; no modulo rotation across the catalogue.

## Interaction and accessibility

Use native scrolling with a passive requestAnimationFrame depth effect capped at 90px. IntersectionObserver reveals sections and cards with a short stagger. Hover and keyboard focus share feedback. Keyboard focus reveals pending content. Reduced-motion preferences disable animation, transforms and smooth scrolling.

Quick look uses a native dialog with Tab/Shift+Tab containment, Escape closing, backdrop close and focus restoration. Featured-title changes are explicit; there is no auto-rotating carousel or wheel interception. Responsive layouts cover 320px, 390px, 768px and desktop widths.

Preserve guest previews, search/filters, profiles/kids mode, subscriptions, playback, reviews and all staff workflows. State simulated payments and placeholder videos at the relevant decisions. Do not add unsupported watchlists, match percentages or unverified quality claims.

## Design provenance

Stitch received a fresh requirements-only brief. No existing BingeBox layouts, source code, screenshots or reference sites were supplied. The user approved the resulting palette. Generated artifacts remain in [docs/stitch](docs/stitch/README.md); the local React integration corrects scope, accessibility and functionality gaps in the raw export.

Earlier warm, monochrome and reference-inspired variants are retired. Their historical decisions and screenshots remain documented in [design history](docs/design-history.md); their alternate components, stylesheets, image assets and unused font packages have been removed from the application.
