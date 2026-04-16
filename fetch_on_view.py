"""
Fetch all on-view objects from the Met Museum Open Access API,
grouped by gallery number. Uses only stdlib (no aiohttp).

Saves progress incrementally so it can resume if interrupted.
"""

import json
import time
import urllib.request
import concurrent.futures
from pathlib import Path

API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
OUTPUT_DIR = Path("data")
BATCH_SIZE = 10
DELAY_BETWEEN_BATCHES = 2.0  # seconds — conservative to avoid 403s
PROGRESS_FILE = OUTPUT_DIR / "fetch_progress.json"


def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MetHackathon/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt < retries - 1:
                wait = (attempt + 1) * 3
                time.sleep(wait)
            else:
                raise


def fetch_object(object_id):
    try:
        return fetch_json(f"{API_BASE}/objects/{object_id}")
    except Exception:
        return None


def save_progress(all_objects, done_ids, failed_ids):
    with open(OUTPUT_DIR / "on_view_objects.json", "w") as f:
        json.dump(all_objects, f)
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"done": list(done_ids), "failed": list(failed_ids)}, f)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Step 1: Get all on-view object IDs
    print("Fetching on-view object IDs...")
    search_data = fetch_json(f"{API_BASE}/search?isOnView=true&q=*")
    object_ids = search_data.get("objectIDs", [])
    total = search_data.get("total", 0)
    print(f"Found {total} objects on view")

    with open(OUTPUT_DIR / "on_view_ids.json", "w") as f:
        json.dump({"total": total, "objectIDs": object_ids}, f)

    # Check for existing progress to resume
    all_objects = []
    done_ids = set()
    failed_ids = set()

    if PROGRESS_FILE.exists():
        progress = json.load(open(PROGRESS_FILE))
        done_ids = set(progress.get("done", []))
        failed_ids = set(progress.get("failed", []))

        if (OUTPUT_DIR / "on_view_objects.json").exists():
            all_objects = json.load(open(OUTPUT_DIR / "on_view_objects.json"))

        remaining = [oid for oid in object_ids if oid not in done_ids]
        print(f"Resuming: {len(done_ids)} done, {len(failed_ids)} failed, {len(remaining)} remaining")
    else:
        remaining = object_ids

    # Step 2: Fetch in controlled batches
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_start in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            results = list(executor.map(fetch_object, batch))

        batch_success = 0
        for oid, r in zip(batch, results):
            if r:
                all_objects.append(r)
                done_ids.add(oid)
                batch_success += 1
            else:
                failed_ids.add(oid)

        # Print progress every 10 batches or at end
        if batch_num % 10 == 0 or batch_num == 1 or batch_start + BATCH_SIZE >= len(remaining):
            pct = min(100, (batch_start + len(batch)) / len(remaining) * 100)
            print(f"  Batch {batch_num}/{total_batches} ({pct:.0f}%) - {len(all_objects)} fetched, {len(failed_ids)} failed")

        # Save progress every 50 batches
        if batch_num % 50 == 0:
            save_progress(all_objects, done_ids, failed_ids)
            print(f"  [saved progress]")

        time.sleep(DELAY_BETWEEN_BATCHES)

    # Step 3: Final save
    save_progress(all_objects, done_ids, failed_ids)
    size_mb = (OUTPUT_DIR / "on_view_objects.json").stat().st_size / 1024 / 1024
    print(f"\nFetched {len(all_objects)} objects ({len(failed_ids)} failed)")
    print(f"Saved raw data ({size_mb:.0f} MB)")

    # Step 4: Build gallery summary
    by_gallery = {}
    no_gallery = []
    for obj in all_objects:
        gallery = obj.get("GalleryNumber", "")
        if gallery:
            by_gallery.setdefault(gallery, []).append({
                "objectID": obj.get("objectID"),
                "title": obj.get("title"),
                "artistDisplayName": obj.get("artistDisplayName"),
                "department": obj.get("department"),
                "classification": obj.get("classification"),
                "medium": obj.get("medium"),
                "culture": obj.get("culture"),
                "objectDate": obj.get("objectDate"),
                "objectBeginDate": obj.get("objectBeginDate"),
                "objectEndDate": obj.get("objectEndDate"),
                "tags": obj.get("tags"),
                "primaryImageSmall": obj.get("primaryImageSmall"),
                "objectURL": obj.get("objectURL"),
                "isHighlight": obj.get("isHighlight"),
            })
        else:
            no_gallery.append(obj.get("objectID"))

    sorted_galleries = dict(
        sorted(by_gallery.items(), key=lambda x: x[0].zfill(10))
    )

    summary = {
        "total_on_view": len(all_objects),
        "total_with_gallery": sum(len(v) for v in by_gallery.values()),
        "total_without_gallery": len(no_gallery),
        "num_galleries": len(by_gallery),
        "galleries": sorted_galleries,
    }

    with open(OUTPUT_DIR / "galleries_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary:")
    print(f"  Objects with gallery number: {summary['total_with_gallery']}")
    print(f"  Objects without gallery number: {summary['total_without_gallery']}")
    print(f"  Unique galleries: {summary['num_galleries']}")

    print(f"\nSample galleries:")
    for gallery, objects in list(sorted_galleries.items())[:15]:
        print(f"  Gallery {gallery}: {len(objects)} objects")


if __name__ == "__main__":
    start = time.time()
    main()
    print(f"\nDone in {time.time() - start:.1f}s")
