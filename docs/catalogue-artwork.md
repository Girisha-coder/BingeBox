# Catalogue artwork

The 162-title catalogue contains **14 verified promotional posters** and **148 distinct illustrative covers**. All are locally bundled WebP assets. No external image service is called when browsing the application.

## Matching and coverage

The 150 real Kaggle titles were checked against Wikipedia metadata. A poster was accepted only when the normalized title, release year in the introduction, screen type, portrait image and an explicit poster caption or filename matched. Ambiguous matches were rejected. This yielded 78 metadata candidates; 14 image downloads succeeded. Repeated HTTP 429 responses limited retrieval, so the remaining candidates retain their illustrative covers. This does not mean official posters do not exist for those films. The 12 fictional titles have illustrative covers.

Each title has a stable filename and a unique SHA-256 hash. Illustrative photo selection also rejected near-duplicate perceptual hashes. The original six Stitch illustrations are assigned once each; there is no cycling of those images across catalogue titles. Wide spotlight artwork is another crop of the same title-specific illustration.

## Provenance

- [Full asset manifest](evidence/catalogue-art-manifest.json): title, filename, source page, source identifier, author, image hash, byte size, poster status and matching evidence.
- [Matching audit](evidence/poster-match-audit.json): result for each real title.
- [Stitch image sources](evidence/stitch-assets.json): original generated artwork.
- Remaining illustrative photographs were retrieved through [Lorem Picsum](https://picsum.photos/); the manifest retains the supplied photographer and original Unsplash page. They are labelled illustrative covers and do not depict or endorse the associated film.
- Promotional posters remain the work of their original rights holders. Each poster entry links its Wikipedia file page and source information. These are identification assets for this local course demo, not a claim of ownership or a licence for film streaming.

## Downloaded posters

| Catalogue title | Year | Poster source |
| --- | --- | --- |
| Once Upon a Time in America | 1984 | [Source and attribution](https://en.wikipedia.org/wiki/File:Once_Upon_a_Time_in_America.png) |
| The Guns of Navarone | 1961 | [Source and attribution](https://en.wikipedia.org/wiki/File:GunsofNavarone.jpg) |
| My Little Pony: A New Generation | 2021 | [Source and attribution](https://en.wikipedia.org/wiki/File:My_Little_Pony_A_New_Generation_film_poster.jpg) |
| Dick Johnson Is Dead | 2020 | [Source and attribution](https://en.wikipedia.org/wiki/File:Dick_Johnson_Is_Dead.jpg) |
| Intrusion | 2021 | [Source and attribution](https://en.wikipedia.org/wiki/File:Intrusion_2021_film_poster.png) |
| The American | 2010 | [Source and attribution](https://en.wikipedia.org/wiki/File:The_American_2010_poster.png) |
| Nightbooks | 2021 | [Source and attribution](https://en.wikipedia.org/wiki/File:Nightbooks_film_poster.jpg) |
| Blood Red Sky | 2021 | [Source and attribution](https://en.wikipedia.org/wiki/File:Blood_Red_Sky.jpg) |
| Bombay | 1995 | [Source and attribution](https://en.wikipedia.org/wiki/File:Bombay_1995_poster.jpg) |
| Boogie Nights | 1997 | [Source and attribution](https://en.wikipedia.org/wiki/File:Boogie_Nights_poster.png) |
| Five Feet Apart | 2019 | [Source and attribution](https://en.wikipedia.org/wiki/File:Five_Feet_Apart_(2019_poster).png) |
| Ragini MMS 2 | 2014 | [Source and attribution](https://en.wikipedia.org/wiki/File:Ragini_MMS_2_Poster.jpg) |
| The Whole Truth | 2016 | [Source and attribution](https://en.wikipedia.org/wiki/File:TheWholeTruth_2016poster.jpg) |
| Nayattu | 2021 | [Source and attribution](https://en.wikipedia.org/wiki/File:Nayattu.jpg) |

## Maintenance

`scripts/prepare_catalogue_art.py` builds a fresh complete fallback set and overwrites existing cover assignments. Do not run it during normal startup. `scripts/prepare_official_posters.py` then attempts title/year-verified posters, reusing cached metadata and retaining downloaded posters. The retrieval scripts use `gpu_env`, Pillow and requests. External availability can change.

Keep the saved asset set for routine builds. The browser suite checks all 162 file hashes and unique assignments, visible catalogue image loads and a verified poster on a title page. New titles created through the catalogue administrator receive a deterministic numbered gradient instead of another title's poster.
