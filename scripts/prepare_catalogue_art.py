"""Create a persistent, unique photographic cover assignment for the demo catalogue."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import random

from PIL import Image, ImageOps
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend/src/assets/catalogue"
OUT.mkdir(parents=True, exist_ok=True)
titles = json.loads((ROOT / "docs/evidence/catalogue-art-titles.json").read_text(encoding="utf-8"))


def difference_hash(image):
    pixels = list(image.convert("L").resize((9, 8)).getdata())
    return sum((pixels[y * 9 + x] > pixels[y * 9 + x + 1]) << (y * 8 + x) for y in range(8) for x in range(8))


def download(entry):
    try:
        url = f"https://picsum.photos/id/{entry['id']}/600/900"
        response = requests.get(url, timeout=35)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        return entry, image, url
    except (requests.RequestException, OSError):
        return None


def save(title, image, source, author, source_id):
    filename = f"title-{title['title_id']}.webp"
    # Keep the original photo; the UI applies its own restrained dark vignette.
    image = ImageOps.fit(image, (480, 720), method=Image.Resampling.LANCZOS)
    image.save(OUT / filename, "WEBP", quality=84, method=6)
    content = (OUT / filename).read_bytes()
    return {
        "title_id": title["title_id"], "title": title["name"], "file": filename,
        "source": source, "author": author, "source_id": source_id,
        "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
        "kind": "illustrative", "official_poster": False,
    }


def main():
    manifest = []
    stitch_files = ["orbital", "coast", "teahouse", "observatory", "particles", "city"]
    stitch_sources = {Path(x["file"]).stem: x for x in json.loads((ROOT / "docs/evidence/stitch-assets.json").read_text())}
    hashes = []
    for title, name in zip(titles[:6], stitch_files):
        im = Image.open(ROOT / f"frontend/src/assets/stitch/{name}.webp").convert("RGB")
        hashes.append(difference_hash(im))
        manifest.append(save(title, im, stitch_sources[name]["source"], "Stitch concept generation", f"stitch:{name}"))

    candidates = []
    for page in [2, 3, 4]:
        r = requests.get(f"https://picsum.photos/v2/list?page={page}&limit=100", timeout=30)
        r.raise_for_status()
        candidates.extend(r.json())
    # Stable selection without an external request whenever the application is viewed.
    random.Random(20261021).shuffle(candidates)
    for start in range(0, len(candidates), 12):
        if len(manifest) == len(titles):
            break
        with ThreadPoolExecutor(max_workers=6) as pool:
            batch = list(pool.map(download, candidates[start:start + 12]))
        for result in batch:
            if result is None or len(manifest) == len(titles):
                continue
            entry, image, url = result
            fingerprint = difference_hash(image)
            if any((fingerprint ^ old).bit_count() < 8 for old in hashes):
                continue
            hashes.append(fingerprint)
            manifest.append(save(titles[len(manifest)], image, entry["url"], entry["author"], f"picsum:{entry['id']}"))
        print(f"Distinct catalogue covers: {len(manifest)}/{len(titles)}", flush=True)
    assert len(manifest) == len(titles), "Insufficient distinct photos; catalogue assignment not published"
    assert len({x["sha256"] for x in manifest}) == len(manifest)
    assert len({x["source_id"] for x in manifest}) == len(manifest)
    (OUT / "manifest.json").write_text(json.dumps({str(x["title_id"]): {"file": x["file"], "official": False} for x in manifest}, indent=2), encoding="utf-8")
    (ROOT / "docs/evidence/catalogue-art-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Verified {len(manifest)} unique sources and file hashes; {sum(x['bytes'] for x in manifest):,} bytes.")


if __name__ == "__main__":
    main()
