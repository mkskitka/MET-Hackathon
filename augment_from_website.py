"""
Augment on-view Asian Art objects by scraping the Met website.
Extracts: classification, dimensions, period, curatorial description,
and all image URLs from the embedded Next.js data.
"""

import json
import csv
import re
import time
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path("data")


def fetch_page(object_id):
    url = f"https://www.metmuseum.org/art/collection/search/{object_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def extract_tombstone_field(html, field_name):
    """Extract a field from the tombstone section like 'Classification:-Ceramics'"""
    pattern = rf'{re.escape(field_name)}:-([^"]*?)"'
    match = re.search(pattern, html)
    if match:
        val = match.group(1).rstrip("\\")
        val = val.replace("\\u003cbr/\\u003e", " | ")
        return val
    return ""


def extract_description(html):
    """Extract the og:description / curatorial description from meta tags"""
    match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    if match:
        return match.group(1)
    return ""


def extract_period(html):
    """Extract period from tombstone"""
    return extract_tombstone_field(html, "Period")


def extract_dimensions(html):
    """Extract dimensions from tombstone"""
    return extract_tombstone_field(html, "Dimensions")


def extract_classification(html):
    """Extract classification from tombstone"""
    return extract_tombstone_field(html, "Classification")


def extract_image_urls(html):
    """Extract all image URLs from the embedded data (handles escaped quotes)"""
    urls = re.findall(r'originalImageUrl[\\"]+"?:?[\\"]+(https://images\.metmuseum\.org/[^"\\]+)', html)
    # Dedupe while preserving order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def extract_map_url(html):
    """Extract the gallery map URL"""
    match = re.search(r'"href":"(https://maps\.metmuseum\.org/[^"]+)"', html)
    if match:
        return match.group(1).replace("\\u0026", "&")
    return ""


def scrape_object(object_id):
    try:
        html = fetch_page(object_id)
        return {
            "object_id": object_id,
            "period": extract_period(html),
            "dimensions": extract_dimensions(html),
            "classification": extract_classification(html),
            "curatorial_description": extract_description(html),
            "all_image_urls": extract_image_urls(html),
            "map_url": extract_map_url(html),
        }
    except Exception as e:
        print(f"  Error for {object_id}: {e}")
        return None


def main():
    # Load on-view object IDs
    import pandas as pd
    df = pd.read_csv(OUTPUT_DIR / "asian_art_on_view.csv")
    object_ids = df.object_id.tolist()
    print(f"Augmenting {len(object_ids)} on-view objects from Met website...")

    # Check for existing progress
    progress_file = OUTPUT_DIR / "augment_progress.json"
    results = []
    done_ids = set()

    if progress_file.exists():
        with open(progress_file) as f:
            results = json.load(f)
        done_ids = {r["object_id"] for r in results}
        print(f"Resuming: {len(done_ids)} already done")

    remaining = [oid for oid in object_ids if oid not in done_ids]
    print(f"{len(remaining)} remaining")

    for i, oid in enumerate(remaining):
        result = scrape_object(oid)
        if result:
            results.append(result)

        if (i + 1) % 20 == 0 or i == len(remaining) - 1:
            pct = (i + 1) / len(remaining) * 100
            print(f"  {i+1}/{len(remaining)} ({pct:.0f}%) - {len(results)} total")

        # Save progress every 100
        if (i + 1) % 100 == 0:
            with open(progress_file, "w") as f:
                json.dump(results, f)

        # Be gentle: ~2 requests per second
        time.sleep(0.5)

    # Final save
    with open(progress_file, "w") as f:
        json.dump(results, f)

    # Save as CSV for easy merging
    rows = []
    for r in results:
        rows.append({
            "object_id": r["object_id"],
            "period": r["period"],
            "dimensions": r["dimensions"],
            "classification": r["classification"],
            "curatorial_description": r["curatorial_description"],
            "num_images": len(r["all_image_urls"]),
            "all_image_urls": "|".join(r["all_image_urls"]),
            "map_url": r["map_url"],
        })

    with open(OUTPUT_DIR / "augmented_fields.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Saved {len(rows)} augmented records to data/augmented_fields.csv")

    # Quick stats
    has_class = sum(1 for r in rows if r["classification"])
    has_dims = sum(1 for r in rows if r["dimensions"])
    has_period = sum(1 for r in rows if r["period"])
    has_desc = sum(1 for r in rows if r["curatorial_description"])
    print(f"  With classification: {has_class}")
    print(f"  With dimensions: {has_dims}")
    print(f"  With period: {has_period}")
    print(f"  With curatorial description: {has_desc}")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"Completed in {time.time() - start:.0f}s")
