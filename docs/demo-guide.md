# End-to-end demonstration

Use [BingeBox](http://localhost:18080) and the public fictional password `BingeBox-Demo-2026!`. These interactive demonstrations intentionally create activity. The automated browser runner instead uses a disposable test database.

## W1 — Subscription lifecycle

1. Sign in as `kabir.malhotra@bingebox.example`. The Duo account has Kabir and Ananya.
2. Try adding a third profile: the plan limit is shown as a readable error.
3. Open Plans and choose Basic: the downgrade is refused because two profiles remain. The old subscription is unchanged.
4. Choose Family: the change succeeds, the old subscription is cancelled and existing streams close. Add another profile.
5. Open Account, toggle auto-renew, and inspect membership history and live devices.
6. Sign out; sign in as `billing@staff.bingebox.example` with “Staff account” checked. Process renewals through the relevant end date. Auto-renewing accounts extend; opted-out subscriptions expire and lose their streams.
7. Suspend and reinstate a demo account. Suspension records the staff member and prevents playback. Reinstatement does not revive old sessions.

## W2 — Discovery and reporting

1. As a guest, search for “Monsoon” or a close misspelling. Fuzzy search can return related matches as well as the exact title.
2. Combine genre/language filters; expand More filters for runtime and IMDb score. Missing Kaggle language/IMDb values are not invented.
3. Open a title: guests see a short teaser and preview fields. Sign in and choose a profile to see full details, episodes and reviews.
4. With an existing viewer, inspect continue watching, up next, genre rankings and recommendations. A new viewer may have no history-based recommendations yet.
5. In Studio, billing/super staff can select active subscriptions, lapsing subscriptions, binge activity and rating comparison reports.
6. Catalogue staff can add a trailer to the correct title using a real YouTube ID. The title page embeds it without consuming a stream slot. External availability, embedding permission and connectivity belong to YouTube; the baseline deliberately has no fabricated trailer links.

## W3 — Playback and integrity

1. Sign in as `dev.menon@bingebox.example`, choose Dev, search for **A Minute of Rain** and play it. The original generated placeholder lasts 60 seconds.
2. Seek to around 24 seconds, pause, and use Save & close. Play again: the video resumes. Start again creates a new attempt.
3. Reach at least 54 seconds (90%), save, and post a rating/review. Earlier attempts to review are rejected. Ratings can be updated or removed.
4. Use two independent tabs/windows on a Basic account. Each tab has its own opaque device identifier. The second simultaneous stream is refused. Account → Stop stream frees the slot.
5. Sign in as `rohan.desai@bingebox.example`, choose Tara, and search for **Midnight Signal**. It is excluded from the kids catalogue; direct requests are rejected too.
6. To leave kids mode, select the profile navigation link and enter the account password. A wrong password leaves the restriction in place.
7. A staff suspension, expiry or plan change revokes the stream. Subsequent media requests/progress checks reject it; the browser pauses when it receives the rejection. Already buffered bytes cannot be recalled.

## Staff create/update/delete

- Catalogue: titles and their movie/series subtype are created atomically; maintain episodes, genres, audio/subtitle lists and assets.
- Full files must be under `media/`, have matching actual/declared duration, and pass the database’s runtime tolerance. Placeholders must be SD. Never enter a filesystem path outside that directory.
- Titles/episodes with watch history cannot be deleted or have their runtime changed through Studio. Foreign keys prevent unsafe plan/genre deletion. In-use plan limit reductions are refused.
- Super: maintain plans. Billing: accounts, renewals and reports. Catalogue staff cannot change billing state; billing staff cannot edit the catalogue.
