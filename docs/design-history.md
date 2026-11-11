# Retired BingeBox design experiments

Direction approved by the user: **simple, minimal, luxurious and warm**. Preserve the earlier preference for a dark interface.

Reference: [Oura design analysis on getdesign.md](https://getdesign.md/oura/design-md), inspected 20 October 2026. The reference pairs an editorial serif with a neutral sans and warm earth tones. BingeBox adapts those principles to a dark film catalogue; this is an independent design, not Oura branding or a copied template.

## Visual language

- Warm charcoal canvas `#191715`; slightly elevated espresso surfaces `#211e1b`.
- Ivory text `#f3ece1`; muted text `#b4aaa0`; bronze primary action `#d3b48a`.
- Quiet borders `#39332c`. Feedback colours remain distinguishable and include text.
- Locally bundled Fraunces 300 for headings; Inter 400–600 for readable interface text. Fonts retain their package licences.
- Compact navigation, consistent spacing and a restrained introductory area. No animated backgrounds, decorative arches, gradients or artificial poster photography.
- Catalogue covers are original typographic placeholders in muted earth colours. They are never presented as official movie artwork.
- Primary actions use a solid bronze pill; secondary actions use a fine outline. Forms use modest rounded corners and visible labels.
- Display type is reserved for page and section headings. Tables and staff forms remain compact and legible.
- Desktop content is centred within 1,360 pixels. Catalogue columns reduce from six to four, three and two. Account sections and forms stack on narrow screens.

## Interaction

Keep all existing viewing, account and staff workflows. Show helpful empty/loading/error states, keyboard focus, labelled controls and reduced-motion support. Do not hide required project functionality to simplify the appearance. Show placeholder-video and payment-demo qualifications where users make the corresponding decision.

## Separate black, white and indigo version

Added at the user's request on 20 October 2026: `/black-white/` uses dominant `#000000`, secondary `#FFFFFF`, and `#2C3480` for buttons, selected navigation and decorative highlights. Muted text and borders use white transparency over black. Text on indigo buttons stays white; keyboard focus uses white outlines.

The same minimal layout, typography and application workflows are retained. Scoped rules in `frontend/src/black-white.css` activate only in this URL namespace. The original stylesheet and warm default at `/` are preserved. A footer link returns to the original design. Both versions share the existing API, session and database.

## Separate cinematic version

Added 21 October 2026 at `/cinematic/`, following the user's [Bingwatch reference](https://bing-watch.preview.emergentagent.com/?utm_source=share). The reference was inspected in the browser, independently of the Stitch exploration. This version uses a full-width artwork hero, bold Unbounded headings, DM Sans body text, near-black surfaces, cyan accents and image-backed catalogue cards. Fonts are bundled locally. The earlier warm and black/white/indigo versions remain unchanged.

Four locally optimized WebP images come from the public photo URLs displayed by the supplied reference; their URLs and sizes are recorded in `docs/evidence/cinematic-assets.json`. They are labelled illustrative atmosphere and are not represented as official artwork for BingeBox titles. Catalogue names, genres, years and ratings come from the API. The hero offers explicit title selection without automatic rotation; its title links lead into the existing age/subscription-protected detail and playback flow.

Motion consists of 520ms feature-copy entry, 700ms artwork crossfade, native-scroll depth capped at 110px, 500ms viewport reveals staggered by 45ms, 320ms card lift, 600ms image zoom, and 180ms button feedback. Scroll handlers are passive and scheduled through requestAnimationFrame. IntersectionObserver reveals content; no wheel interception is used. Keyboard focus reveals pending content, and reduced-motion preferences disable entry, depth and hover transforms. All routes, forms and staff workflows share the existing React application under the new route prefix.

Verification: three focused browser journeys passed against a temporary 840-row database, including search, featured selection, direct-route reload, theme isolation, mobile widths 320/390/768, reduced motion, keyboard interaction, authentication, profile selection and real video playback. Screenshots are saved in `docs/evidence/cinematic-*.png`.


These experiments are historical. The user selected Stitch as the only interface on 21 October 2026. See ../DESIGN.md for the current rules.
