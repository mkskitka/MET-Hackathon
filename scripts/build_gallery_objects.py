#!/usr/bin/env python3
"""
Build a per-gallery object summary for the map viewer.
Combines on_view_objects.json, asian_art_on_view.csv, and augment_progress.json.
Output: data/gallery_objects.json keyed by gallery_number.
"""

import json
import csv

def main():
    with open("data/on_view_objects.json") as f:
        ov_objects = json.load(f)

    with open("data/asian_art_on_view.csv") as f:
        asian_objects = list(csv.DictReader(f))

    with open("data/augment_progress.json") as f:
        augment_data = json.load(f)

    # Index augment by object_id
    aug_by_id = {}
    for a in augment_data:
        aug_by_id[a["object_id"]] = a
        aug_by_id[str(a["object_id"])] = a

    galleries = {}
    seen_ids = set()

    # Process on_view_objects first (richer API data with images)
    for obj in ov_objects:
        gnum = obj.get("GalleryNumber", "")
        if not gnum:
            continue
        oid = obj["objectID"]
        seen_ids.add(str(oid))
        if gnum not in galleries:
            galleries[gnum] = {"objects": [], "departments": set()}
        galleries[gnum]["departments"].add(obj.get("department", ""))

        # Merge augment data
        aug = aug_by_id.get(oid, aug_by_id.get(str(oid), {}))

        # Pick best image: augment has full-res, API has small
        images = aug.get("all_image_urls", [])
        if not images and obj.get("primaryImage"):
            images = [obj["primaryImage"]]
            if obj.get("additionalImages"):
                images.extend(obj["additionalImages"])

        galleries[gnum]["objects"].append({
            "id": oid,
            "title": obj.get("title", ""),
            "artist": obj.get("artistDisplayName", ""),
            "date": obj.get("objectDate", ""),
            "medium": obj.get("medium", ""),
            "culture": obj.get("culture", ""),
            "department": obj.get("department", ""),
            "period": aug.get("period", obj.get("period", "")),
            "classification": aug.get("classification", obj.get("classification", "")),
            "dimensions": aug.get("dimensions", obj.get("dimensions", "")),
            "description": aug.get("curatorial_description", ""),
            "image": obj.get("primaryImageSmall", ""),
            "images": images,
            "url": obj.get("objectURL", ""),
            "highlight": obj.get("isHighlight", False),
        })

    # Add asian art objects (avoid duplicates)
    for obj in asian_objects:
        gnum = obj.get("gallery_number", "")
        oid = obj.get("object_id", "")
        if not gnum or oid in seen_ids:
            continue
        seen_ids.add(oid)
        if gnum not in galleries:
            galleries[gnum] = {"objects": [], "departments": set()}
        galleries[gnum]["departments"].add(obj.get("department", ""))

        aug = aug_by_id.get(oid, aug_by_id.get(int(oid) if oid.isdigit() else oid, {}))

        images = aug.get("all_image_urls", [])
        # Use first image as thumbnail
        thumb = images[0] if images else ""
        # Convert original URLs to small thumbnails for the list view
        thumb_small = thumb.replace("/original/", "/web-large/") if thumb else ""

        galleries[gnum]["objects"].append({
            "id": int(oid) if oid.isdigit() else oid,
            "title": obj.get("title", ""),
            "artist": "",
            "date": obj.get("object_date", ""),
            "medium": obj.get("medium", ""),
            "culture": obj.get("culture", ""),
            "department": obj.get("department", ""),
            "period": aug.get("period", ""),
            "classification": aug.get("classification", ""),
            "dimensions": aug.get("dimensions", ""),
            "description": aug.get("curatorial_description", ""),
            "image": thumb_small,
            "images": images,
            "url": f"https://www.metmuseum.org/art/collection/search/{oid}",
            "highlight": obj.get("is_highlight", "") == "True",
        })

    # Build output
    output = {}
    for gnum, data in galleries.items():
        objects = data["objects"]
        objects.sort(key=lambda o: (not o["highlight"], o["title"]))
        output[gnum] = {
            "count": len(objects),
            "departments": sorted(data["departments"] - {""}),
            "has_images": sum(1 for o in objects if o["image"] or o["images"]),
            "has_descriptions": sum(1 for o in objects if o["description"]),
            "objects": objects,
        }

    with open("data/gallery_objects.json", "w") as f:
        json.dump(output, f)

    total = sum(g["count"] for g in output.values())
    with_imgs = sum(g["has_images"] for g in output.values())
    with_desc = sum(g["has_descriptions"] for g in output.values())
    print(f"Built gallery_objects.json:")
    print(f"  {len(output)} galleries")
    print(f"  {total} objects total")
    print(f"  {with_imgs} with images")
    print(f"  {with_desc} with descriptions")

    print("\nTop galleries:")
    for gnum, data in sorted(output.items(), key=lambda x: -x[1]["count"])[:10]:
        imgs = data["has_images"]
        desc = data["has_descriptions"]
        print(f"  Gallery {gnum:>5}: {data['count']:>4} objects, {imgs} imgs, {desc} descs")

if __name__ == "__main__":
    main()
