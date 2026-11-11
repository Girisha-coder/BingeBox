### BingeBox — Cinematic Discovery & Viewing Architecture

Here is the high-fidelity desktop discovery and viewing experience created for **BingeBox** (BingeBox - Cinematic Desktop Discovery & Viewing), along with the foundational design system (**Cinematic Obsidian** [Design_System]).

---

### 1. Original Concept & Information Architecture

- **Visual Storytelling & Palette Philosophy:**
  - **Dominant Black (`#000000`, `#0C0E18`):** Deep, true-black canvas creates an OLED-optimized theatrical immersion, eliminating screen glare and focusing attention entirely on media art.
  - **Crisp Editorial White (`#FFFFFF`):** High typographic contrast using geometric hierarchy for instant legibility from viewing distance.
  - **Electric Indigo & Sapphire Highlights (`#2C3480`, `#4F5CD8`):** Applied purposefully to focus states, active filter chips, hero CTAs, and ranked numbers—infusing prestige without visual distraction.
- **Header & Guest/Member Architecture:**
  - Clear **Simulated Educational Sandbox** disclosure banner running continuously along the top.
  - Dual access state: Guests can search, inspect metadata, filter by 5 distinct criteria, and view preview reels. Quick switcher toggles between **Adult Mode** and **Kids Safe View** (which dynamically filters mature ratings like TV-MA).
- **Interactive Multi-Criteria Filter Bar (162 Titles Catalogue):**
  - Instant live filter chips: Genre tags (`Sci-Fi`, `Psychological Thriller`, `Neo-Noir`, etc.).
  - Secondary dropdowns: Audio track filtering (with explicit fallback: titles with unrecorded original audio are labeled `"Unknown"` rather than guessed), multi-lingual subtitles, and IMDb rating thresholds (`7.5+`).
- **Discovery Hierarchy:**
  - **Hero Feature Spotlight:** *Chronos: Zero* with rich metadata chips (4K UHD, HDR10, Dolby Atmos 7.1, TV-MA, IMDb 8.9), direct dual actions (*Watch Preview Reel* & *Resume Ep. 3*), and an "Up Next in Queue" card.
  - **Continue Watching Rail:** Progress indicators with exact runtime remaining (e.g., *Kowloon Drift*, *Solitude Point*).
  - **Top 10 in North America:** Custom metallic typography ranks (#1 to #5) paired with cinematic poster frames.
  - **Multi-Language Cinema Spotlight:** Flagged audio provenance badges (Japanese original audio, Spanish Castilian Atmos, French Criterion master) prioritizing authentic international cinema.

---

### 2. Motion, Interaction & Accessibility Specifications

#### A. Implemented in the Live Prototype
- **Subtle Ambient Breathing Glow (`animation: pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite`):** Soft luminous sapphire backdrop beneath primary actions.
- **Card Lift & Focus Micro-Interactions (`transform: translateY(-4px) scale(1.02)`, `transition: all 250ms cubic-bezier(0.16, 1, 0.3, 1)`):** Elevation feedback on poster cards with ambient drop-shadow expansion.
- **Tactile Button Press Feedback (`active:scale-95`, `transition: transform 120ms ease`):** Instant physical tactile response for filter pills and playback buttons.
- **Accessibility Guarantee (`@media (prefers-reduced-motion: reduce)`):** All continuous transforms and pulses are neutralized to clean static borders and opacities, avoiding sensory strain or vestibular disruption.

#### B. Proposed Motion Choreography for Full Platform
1. **Scroll-Driven Parallax Depth:** Hero artwork translating at `0.35x` scroll velocity while typography remains anchored at `1.0x` for 300px before dissolving smoothly to black via `linear` opacity ramp.
2. **Title Detail Slide-Over Drawer:** Spring transition (`stiffness: 320, damping: 28, mass: 0.8`, approx. 360ms) sliding from right edge with an obsidian glass backdrop backdrop blur (`backdrop-filter: blur(24px)`).
3. **Carousel Momentum Rail:** Horizontal snap-scrolling on trackpad gesture with friction damping (`deceleration-rate: normal`), accompanied by progressive fade-out edges.

---

### 3. System Extension Across the Product Ecosystem

- **Title Details Page:**
  - Hero header expands to trailer viewport with playback state controls (seek scrubber, quality selector 4K/1080p, audio language channel selector, and plan-based error toasts such as *"Device limit reached: 2/2 active streams"*).
  - Watched status gate: Review and star-rating eligibility only unlocks if title shows `>90% watched` in simulated history.
- **Mobile Responsive Adaptation:**
  - Top navigation collapses into a sticky frosted bottom tab bar (*Discover, Search, Watchlist, Profile*).
  - Filter pills convert into a horizontally scrolling thumb-accessible chip carousel.
  - Top 10 rankings switch from a 4-column horizontal card grid into a portrait vertical snap-rail with large left-anchored numeral badges.
- **Plans & Device Management:**
  - Card comparison (Standard HD vs. Cinema Tier 4K HDR) with simulated renewal preferences and active registered hardware revoking (e.g., Living Room TV, iPad Pro, MacBook).
- **Staff Administration Portal:**
  - Seamlessly reuses the same dark obsidian tokens (`#0A0C16`, `#121528`), substituting discovery rails with tabular catalog management (metadata batch-tagging, audio stream ingest status, and report telemetry).