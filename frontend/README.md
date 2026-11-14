# Frontend

The React 19 + Vite website for BingeBox.

| Path | Contents |
| --- | --- |
| `src/main.jsx` | App shell, routes and the viewer pages: discover/search, title, sign-in, plans, profiles, account, player |
| `src/Admin.jsx` | Staff Studio (catalogue management, accounts and renewals, reports), loaded only when opened |
| `src/api.js` | The single helper that sends requests to the backend under `/api` |
| `src/Stitch.jsx`, `src/DiscoveryMotion.jsx`, `src/*.css` | Home-page design, scroll effects and styles |
| `src/assets/` | Cover images and fonts |
| `nginx.conf`, `Dockerfile` | Web server settings and the container build used by `docker compose` |
| `tests/` | Playwright browser tests (run through `scripts/run_browser_checks.py`) |

Normally the website is built and served by Docker (`docker compose up`, see the main README). For development, `npm ci` then `npm run dev` starts Vite, which forwards `/api` to the backend on port 18000.
