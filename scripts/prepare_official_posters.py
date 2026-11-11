"""Use title/year-matched Wikipedia promotional posters; retain unique fallbacks.

An image is accepted only for a matching screen title, matching release year,
and an infobox caption (or file name) explicitly identifying a poster.
No search-result image is accepted without those checks.
"""

import hashlib
import io
import json
from pathlib import Path
import re
import time
import unicodedata

from PIL import Image
import requests

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "frontend/src/assets/catalogue"
EVIDENCE = ROOT / "docs/evidence"
HEADERS = {"User-Agent": "BingeBoxAcademicDemo/1.0 (local catalogue attribution research)"}
API = "https://en.wikipedia.org/w/api.php"


def normalize(name):
    name = re.sub(r"\s*\([^)]*\)$", "", name)
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower())


def get_pages(names):
    params = {
        "action": "query", "titles": "|".join(names), "redirects": 1,
        "prop": "pageimages|extracts|revisions", "piprop": "original|name",
        "pilicense": "any", "exintro": 1, "explaintext": 1,
        "rvprop": "content", "rvslots": "main", "format": "json", "formatversion": 2,
    }
    for attempt in range(4):
        r = requests.get(API, headers=HEADERS, params=params, timeout=45)
        if r.status_code != 429:
            break
        delay = int(r.headers.get("Retry-After", "30"))
        print(f"Poster service rate limit; respecting {delay}s retry delay", flush=True)
        time.sleep(delay)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("query", {}).get("pages", [])


def main():
    titles = json.loads((EVIDENCE / "catalogue-art-titles.json").read_text())
    manifest = json.loads((EVIDENCE / "catalogue-art-manifest.json").read_text())
    by_id = {x["title_id"]: x for x in manifest}
    candidates = []
    for title in titles[12:]:
        name, year = title["name"], title["release_year"]
        variants = [name, name.title()] if name.isupper() else [name]
        for n in variants:
            candidates.extend([n, f"{n} ({year} film)", f"{n} (film)", f"{n} (TV series)", f"{n} ({year} TV series)"])
    candidates = list(dict.fromkeys(candidates))
    cache_path = EVIDENCE / "poster-page-cache.json"
    cached = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for start in range(0, len(candidates), 40):
        batch = candidates[start:start + 40]
        key = "|".join(batch)
        if key not in cached:
            cached[key] = get_pages(batch)
            cache_path.write_text(json.dumps(cached), encoding="utf-8")
            time.sleep(2)
        print(f"Poster metadata: {min(start + 40, len(candidates))}/{len(candidates)} candidates", flush=True)
    pages = {p.get("pageid"): p for group in cached.values() for p in group if "missing" not in p}
    accepted = []
    audit = []
    used = set()
    for title in titles[12:]:
        matches = []
        for page in pages.values():
            if normalize(page["title"]) != normalize(title["name"]):
                continue
            intro = page.get("extract", "").split("\n")[0]
            if not re.search(rf"\b{title['release_year']}\b", intro[:700]):
                continue
            screen_type = r"\bfilm\b" if title["title_type"] == "M" else r"\b(series|television|show)\b"
            if not re.search(screen_type, intro[:700], re.I):
                continue
            revisions = page.get("revisions", [])
            wiki = revisions[0].get("slots", {}).get("main", {}).get("content", "") if revisions else ""
            caption = re.search(r"\|\s*caption\s*=([^\n]*)", wiki, re.I)
            caption = caption.group(1).strip() if caption else ""
            if not re.search(r"poster", caption + " " + page.get("pageimage", ""), re.I):
                continue
            original = page.get("original", {})
            if not original.get("source") or original.get("height", 0) < original.get("width", 1):
                continue
            if original["source"] in used:
                continue
            matches.append((page, intro, caption))
        if len(matches) == 1:
            page, intro, caption = matches[0]
            used.add(page["original"]["source"])
            accepted.append((title, page, intro, caption))
        else:
            audit.append({"title_id": title["title_id"], "title": title["name"], "status": "illustrative fallback", "reason": "No unambiguous title/year-matched portrait poster in queried pages"})

    def download(match):
        title, page, intro, caption = match
        if by_id[title["title_id"]]["official_poster"]:
            return {"title_id": title["title_id"], "title": title["name"], "status": "verified poster", "page": page["title"]}
        try:
            target = ART / f"title-{title['title_id']}.webp"
            entry = by_id[title["title_id"]]
            for attempt in range(3):
                r = requests.get(page["original"]["source"].split("?")[0], headers=HEADERS, timeout=35)
                if r.status_code != 429:
                    break
                delay = int(r.headers.get("Retry-After", "10"))
                print(f"Poster image rate limit; respecting {delay}s retry delay", flush=True)
                time.sleep(delay)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            im.thumbnail((600, 900), Image.Resampling.LANCZOS)
            im.save(target, "WEBP", quality=88, method=6)
            entry.update({"source": "https://en.wikipedia.org/wiki/" + page["title"].replace(" ", "_"),
                "image_source": page["original"]["source"], "source_id": f"wikipedia:{page['pageid']}",
                "author": "Original film/series poster rights holder; see source file page",
                "kind": "official poster", "official_poster": True,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size,
                "matched_page": page["title"], "matched_release_year": title["release_year"],
                "verification_intro": intro[:700], "poster_caption": caption,
                "file_page": "https://en.wikipedia.org/wiki/File:" + page["pageimage"].replace(" ", "_")})
            # Checkpoint successful downloads before another external request.
            (EVIDENCE / "catalogue-art-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            (ART / "manifest.json").write_text(json.dumps({str(x["title_id"]): {"file": x["file"], "official": x["official_poster"]} for x in manifest}, indent=2), encoding="utf-8")
            return {"title_id": title["title_id"], "title": title["name"], "status": "verified poster", "page": page["title"]}
        except (requests.RequestException, OSError) as exc:
            return {"title_id": title["title_id"], "title": title["name"], "status": "illustrative fallback", "reason": f"HTTP {exc.response.status_code}" if isinstance(exc, requests.HTTPError) else type(exc).__name__}

    consecutive_limits = 0
    for index, match in enumerate(accepted):
        result = download(match)
        audit.append(result)
        consecutive_limits = consecutive_limits + 1 if result.get("reason") == "HTTP 429" else 0
        print(f"Poster {index + 1}/{len(accepted)}: {result['status']}", flush=True)
        if consecutive_limits >= 3:
            audit.extend({"title_id": rest[0]["title_id"], "title": rest[0]["name"], "status": "illustrative fallback", "reason": "Image service rate limit; stopped requests after repeated HTTP 429"} for rest in accepted[index + 1:])
            break
        time.sleep(2)
    assert len({x["sha256"] for x in manifest}) == len(titles)
    (EVIDENCE / "catalogue-art-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (EVIDENCE / "poster-match-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (ART / "manifest.json").write_text(json.dumps({str(x["title_id"]): {"file": x["file"], "official": x["official_poster"]} for x in manifest}, indent=2), encoding="utf-8")
    official = sum(x["official_poster"] for x in manifest)
    print(f"Verified {official} posters; {len(titles) - official} unique illustrative covers; {len(titles)} distinct file hashes.")


if __name__ == "__main__":
    main()
