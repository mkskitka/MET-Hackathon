# HuggingFace Dataset Findings

## Source

Dataset: `metmuseum/met-asian-art-open-access-hackathon` (gated, requires HF token)

## What We Downloaded

| File | Rows | Size | HF Config |
|---|---|---|---|
| `asian_art_full.csv` | 31,535 | 5.5 MB | `metadata` |
| `asian_art_on_view.csv` | 1,859 | 390 KB | filtered from metadata (has gallery_number) |
| `descriptions.csv` | 31,599 | 39 MB | `generations_agentic_vision` |
| `color_annotations.csv` | 31,454 | 44 MB | `annotations_google_vision_image_properties` |
| `neighbors.csv` | 314,540 | 59 MB | `neighbors_facebook_dinov2_base` (top 10 per object) |

## Coverage for On-View Objects

All 1,859 on-view objects have near-complete coverage across datasets:

- Descriptions: **1,859/1,859** (100%)
- Color data: **1,843/1,859** (99%)
- Visual neighbors: **1,843/1,859** (99%)

## Metadata Fields (`asian_art_full.csv`)

```
object_number, is_highlight, is_public_domain, object_id, gallery_number,
department, title, culture, object_date, object_begin_date, object_end_date,
medium, credit_line
```

- 69 unique galleries for on-view objects
- 198 unique cultures
- Gallery sizes range from 1 to 246 objects (median: 19)
- Date range spans thousands of years of Asian art

## Descriptions (`descriptions.csv`)

AI-generated (agentic-vision) descriptions for every object. Two useful fields:

- `output_alt_text` — short, one-line summary (good for quick display)
  - Example: *"Landscape on a gold folding fan featuring a tall tree, central pavilion, and red bridge"*
- `output_visual_description` — detailed multi-sentence description of what's visually in the artwork (good for semantic matching)
  - Example: *"Landscape painting on an arc-shaped gold paper surface with visible vertical fold lines. On the left, a tall, gnarled tree with clusters of green needles rises beside a small, thatched-roof gate..."*

### How This Helps Profile Matching

The visual descriptions can be embedded or fed to Claude to match against visitor preferences. Instead of relying only on sparse metadata tags, we have rich natural language descriptions of what each artwork actually looks like. This enables matching on:
- Visual mood ("serene", "dramatic", "intricate")
- Subject matter at much finer grain than tags
- Color and composition preferences
- Artistic technique descriptions

## Color Annotations (`color_annotations.csv`)

Dominant colors per artwork image via Google Vision API:

- `dominant_colors` — array of up to 10 colors with hex, RGB, pixel_fraction, and score
- `dominant_color_hexes` — flat list of hex values
- Example: `['#a99c87', '#cbbeaa', '#857a69', '#cac3b8', ...]`

### How This Helps Profile Matching

- Survey could include color preference questions ("pick palettes you're drawn to")
- Route could balance color variety — don't send someone to 10 monochrome ink paintings in a row
- "Warm tones" vs "cool tones" preference maps directly to this data

## Visual Neighbors (`neighbors.csv`)

Pre-computed visual similarity using DINOv2 embeddings. Top 10 nearest neighbors per object.

- `query_object_id` → `neighbor_object_id` with `score` (0-1, higher = more similar)
- Mean similarity score: 0.717
- Range: 0.192 to 1.006

### How This Helps Profile Matching

This is the "if you liked X, you'll also like Y" engine — already computed for us:
- Visitor selects artworks in survey → follow neighbor graph to find more they'd like
- Can chain neighbors to create thematic "threads" through galleries
- Can also use it for the **stretch picks** — find objects that are neighbors-of-neighbors (related but not obvious)

## Configs We Haven't Downloaded Yet

Available if needed:

| Config | What It Is | Potential Use |
|---|---|---|
| `embeddings_agentic_vision_gemini` | Gemini embeddings of AI descriptions | Semantic search over descriptions |
| `embeddings_image_gemini_2` | Gemini embeddings of images | Image-based similarity |
| `embeddings_google_siglip2_so400m_patch14_384` | SigLIP2 image embeddings | Alternative visual similarity |
| `embeddings_facebook_dinov2_base` | DINOv2 image embeddings | Raw vectors behind neighbors.csv |
| `embeddings_qwen3_0_6b_visual_description` | Qwen3 embeddings of descriptions | Text-based similarity |
| `embeddings_qwen3_0_6b_metadata` | Qwen3 embeddings of metadata | Metadata-based similarity |
| `neighbors_google_siglip2_so400m_patch14_384` | SigLIP2 neighbor graph | Alternative neighbor ranking |
| `layouts_*` | 2D UMAP projections | Could visualize collection as a 2D map |

## Key Takeaway

We don't need the Met API at all for Asian Art. The HuggingFace dataset gives us richer data than the API provides — especially the visual descriptions, color analysis, and pre-computed similarity graph. The **1,859 on-view objects across 69 galleries** are our working set for route generation.
