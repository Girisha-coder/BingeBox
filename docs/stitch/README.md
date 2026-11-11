# Independent Stitch exploration

[Open the private Stitch project](https://stitch.withgoogle.com/projects/10648150967291044792).

The user requested independent design ideas with motion and scroll interactions, without giving Stitch any existing frontend layouts. The exact submitted brief is [requirements-brief.md](requirements-brief.md); `generate-request.json` records the tool arguments.

Only functional product requirements, the user's palette/aesthetic preferences, and motion/accessibility requirements were sent. No application source, screenshots, existing design-system files, design reference links, credentials, database records or local frontend URLs were included in the prompt. The MCP credential is read from the user's external Codex configuration and sent only as an authentication header to the configured Stitch endpoint.

This directory preserves the original design exploration artifacts. The integrated implementation is now the sole running interface at [BingeBox](http://localhost:18080), implemented in `frontend/src/Stitch.jsx` and its stylesheets. The raw generated HTML remains a historical design reference.

Start with [reviewed ideas and motion status](reviewed-ideas.md). The [first concept](original-concept.png) and [Stitch's explanation](stitch-explanation.md) are saved. The user approved its palette. Although the remote refinement call failed, the local implementation adds scroll depth, section reveals, reduced-motion handling and accessible quick-look interactions using real application data.
