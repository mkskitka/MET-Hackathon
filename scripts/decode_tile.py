#!/usr/bin/env python3
"""
Download and decode a Mapbox Vector Tile from the Met's Living Map tile server.
This reveals the actual room polygon geometry embedded in the tiles.

Requires: pip install mapbox-vector-tile (or we fall back to raw protobuf parsing)
"""

import urllib.request
import json
import math
import sys
import struct

# The Met Fifth Avenue center: 40.779448, -73.963517
# Mapbox token from the config
TILE_URL = "https://prod.cdn.livingmap.com/tiles/the_met/{z}/{x}/{y}.pbf?lang=en-GB"

def lat_lng_to_tile(lat, lng, zoom):
    """Convert lat/lng to tile x/y at given zoom."""
    n = 2 ** zoom
    x = int((lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def fetch_tile(z, x, y):
    url = TILE_URL.format(z=z, x=x, y=y)
    print(f"Fetching tile: z={z} x={x} y={y}")
    print(f"URL: {url}")
    req = urllib.request.Request(url)
    req.add_header("Accept", "*/*")
    req.add_header("Referer", "https://maps.metmuseum.org/")
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        content_type = resp.headers.get("Content-Type", "")
        content_encoding = resp.headers.get("Content-Encoding", "")
        print(f"Response size: {len(data)} bytes, type: {content_type}, encoding: {content_encoding}")
        return data

def try_decode_mvt(data):
    """Try to decode as Mapbox Vector Tile using the mapbox_vector_tile library."""
    try:
        import mapbox_vector_tile
        result = mapbox_vector_tile.decode(data)
        return result
    except ImportError:
        print("mapbox_vector_tile not installed, trying manual protobuf decode...")
        return None
    except Exception as e:
        # Maybe gzipped
        import gzip
        try:
            decompressed = gzip.decompress(data)
            import mapbox_vector_tile
            result = mapbox_vector_tile.decode(decompressed)
            return result
        except Exception as e2:
            print(f"Failed to decode (tried gzip too): {e2}")
            return None

def try_raw_decode(data):
    """Try to decompress and show raw protobuf structure."""
    import gzip
    try:
        data = gzip.decompress(data)
        print(f"Decompressed to {len(data)} bytes")
    except:
        print("Not gzipped, using raw data")

    # Simple protobuf field extraction - look for strings
    strings = []
    i = 0
    while i < len(data):
        # protobuf: field_number << 3 | wire_type
        # wire_type 2 = length-delimited (strings, bytes, sub-messages)
        if i < len(data):
            byte = data[i]
            wire_type = byte & 0x07
            if wire_type == 2:
                # Read varint for length
                i += 1
                length = 0
                shift = 0
                while i < len(data):
                    b = data[i]
                    length |= (b & 0x7F) << shift
                    shift += 7
                    i += 1
                    if not (b & 0x80):
                        break
                if 1 < length < 200 and i + length <= len(data):
                    chunk = data[i:i+length]
                    try:
                        text = chunk.decode('utf-8')
                        if text.isprintable() and len(text) > 1:
                            strings.append(text)
                    except:
                        pass
                i += max(length, 0)
            else:
                i += 1

    return strings

def main():
    # Try multiple zoom levels to see what data is available
    lat, lng = 40.779448, -73.963517

    for zoom in [15, 16, 17, 18, 19]:
        x, y = lat_lng_to_tile(lat, lng, zoom)
        print(f"\n{'='*60}")
        print(f"Zoom {zoom}: tile ({x}, {y})")
        print(f"{'='*60}")

        try:
            tile_data = fetch_tile(zoom, x, y)
        except Exception as e:
            print(f"Failed to fetch: {e}")
            continue

        # Save raw tile
        tile_path = f"research/tile_z{zoom}_{x}_{y}.pbf"
        with open(tile_path, "wb") as f:
            f.write(tile_data)
        print(f"Saved raw tile to {tile_path}")

        # Try decoding
        decoded = try_decode_mvt(tile_data)
        if decoded:
            print(f"\nDecoded layers: {list(decoded.keys())}")
            for layer_name, layer_data in decoded.items():
                features = layer_data.get("features", [])
                print(f"\n  Layer '{layer_name}': {len(features)} features")
                if features:
                    # Show first few features
                    for feat in features[:3]:
                        props = feat.get("properties", {})
                        geom_type = feat.get("geometry", {}).get("type", "?")
                        print(f"    - type={geom_type} props={json.dumps(props, default=str)[:200]}")

            # Save decoded tile as JSON
            json_path = f"research/tile_z{zoom}_{x}_{y}.json"
            with open(json_path, "w") as f:
                json.dump(decoded, f, indent=2, default=str)
            print(f"  Saved decoded tile to {json_path}")
        else:
            # Try raw string extraction
            strings = try_raw_decode(tile_data)
            if strings:
                unique = sorted(set(strings))
                print(f"\nExtracted {len(unique)} unique strings from tile:")
                for s in unique[:50]:
                    print(f"  '{s}'")

        if zoom >= 17:
            break  # Don't need all zoom levels

if __name__ == "__main__":
    main()
