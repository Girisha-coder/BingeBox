# Media

Video files served by the backend live here.

- `placeholder/` holds the generated placeholder videos: dark, labelled "BINGEBOX - DEMO PLACEHOLDER", one file per distinct runtime (named by length in seconds, e.g. `7080.mp4`). They are not committed to Git. The backend generates a missing one with ffmpeg the first time a title of that length is played, and `scripts/prepare_media.py` pre-generates all of them and records their verified lengths in `manifest.json`.
- A real, permitted MP4 can be placed under this folder and registered by catalogue staff in Studio as a full video, using its path relative to `media/`. The backend checks its length against the movie or episode runtime.

No licensed films are included.
