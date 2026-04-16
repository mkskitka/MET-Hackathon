# System Design: Survey → Recommendation → Route

## Overview

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Survey     │────▶│  User Profile │────▶│  Match &     │────▶│  Route      │
│   (Mobile)   │     │  (Embedding)  │     │  Rank Art    │     │  Generator  │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                                                                      │
                                                               ┌──────▼──────┐
                                                               │  Gallery    │
                                                               │  Map + Path │
                                                               └─────────────┘
```

## Phase 1: Survey (~5 minutes on mobile)

### Survey Sections

**Section A: Logistics (30 seconds)**
- "How much time do you have?" → slider: 30min / 1hr / 2hr / 3hr+ 
- This determines how many galleries we target (roughly 1 gallery per 5-10 min)

**Section B: Vibe Check (1 minute)**
Quick binary choices to establish broad preferences:
- "Ancient or Modern?"
- "Spiritual or Everyday?"  
- "Grand & monumental or Small & intricate?"
- "Familiar cultures or New-to-you?"
- "Colorful or Subdued?"
- "Story-driven or Pure aesthetics?"

Each answer shifts weights in the user profile vector.

**Section C: Category Interest (1 minute)**
Rate interest (skip / maybe / love) for each category:
- Ceramics & Pottery
- Sculpture & Statues
- Paintings & Scrolls
- Metalwork & Jewelry
- Jade & Hardstone
- Textiles & Costumes
- Furniture & Lacquer
- Prints & Calligraphy

Maps directly to `classification` field in our data.

**Section D: Culture Interest (1 minute)**
Rate interest for regions:
- China
- Japan
- Korea
- India & South Asia
- Southeast Asia (Thailand, Cambodia, Indonesia)
- Tibet & Nepal
- "Surprise me" toggle

Maps directly to `culture` field in our data.

**Section E: Image Selection (1.5 minutes)**
Show 12-16 curated artwork images (selected to represent diversity across classification, period, culture, and visual style). User taps the ones that appeal to them. This is the richest signal.

How to select the 12-16 images:
- Pre-curate ~4 sets of images, each emphasizing different aesthetics
- Include a mix: a bold sculpture, a delicate scroll painting, ornate ceramics, minimal ink work, colorful textiles, ancient bronze, etc.
- Use `is_highlight=True` objects and high visual quality (large images)

### Survey Output: User Profile

```json
{
  "time_budget_minutes": 90,
  "preferences": {
    "era": {"ancient": 0.3, "medieval": 0.5, "early_modern": 0.8, "modern": 0.6},
    "classification": {"Ceramics": 0.9, "Sculpture": 0.7, "Paintings": 0.4, ...},
    "culture": {"China": 0.8, "Japan": 0.6, "India": 0.3, ...},
    "vibe": {"spiritual": 0.7, "intricate": 0.8, "colorful": 0.4, ...}
  },
  "selected_image_ids": [49381, 63532, 45673, ...]
}
```

---

## Phase 2: Building the Profile Embedding

We do NOT need to pre-compute embeddings for every artwork. Instead, we use Claude to do the matching. Here's why:

### Why Claude, not vector search

- We have **rich text** for every object: curatorial descriptions, AI visual descriptions, metadata
- We need **reasoning** not just similarity: "you said you like intricate things, this jade carving has extraordinary detail work"
- We need to generate **justifications** for each recommendation
- 1,859 objects is small enough to work with directly
- The HuggingFace dataset already has pre-computed visual similarity (neighbors.csv) for the "if you liked X" use case

### The Matching Pipeline

```
User Profile
     │
     ▼
┌─────────────────────────────────────────┐
│  Step 1: FILTER                         │
│  Narrow 1,859 → ~300-500 candidates     │
│  using structured fields:               │
│  - classification preferences           │
│  - culture preferences                  │
│  - era preferences                      │
│  Simple weighted scoring, no LLM needed │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Step 2: EXPAND via neighbors           │
│  For each selected_image_id from survey │
│  look up neighbors.csv → add similar    │
│  objects to candidate pool              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Step 3: RANK with Claude               │
│  Send Claude the user profile +         │
│  candidate objects (title, description, │
│  curatorial text, classification, etc.) │
│                                         │
│  Ask Claude to:                         │
│  - Score each candidate 1-10            │
│  - Tag as: affinity / stretch / wild    │
│  - Write a 1-sentence "why" for top 30  │
│  - Consider gallery clustering          │
│                                         │
│  Prompt caching: cache the artwork data │
│  so only the user profile varies        │
└─────────────────┬───────────────────────┘
                  │
                  ▼
        Top 20-40 artworks
        with justifications
```

### Step 1 Detail: Weighted Scoring

For each artwork, compute a simple affinity score:

```python
score = (
    culture_weight[obj.culture] * 0.3 +
    classification_weight[obj.classification] * 0.3 +
    era_weight[obj.era_bucket] * 0.2 +
    (1.0 if obj.is_highlight else 0.0) * 0.1 +
    vibe_match(obj, user_vibes) * 0.1
)
```

Keep top ~400 candidates. This is fast, no API calls.

### Step 2 Detail: Neighbor Expansion

```python
# For each image the user selected in the survey
for selected_id in user.selected_image_ids:
    neighbors = neighbors_df[neighbors_df.query_object_id == selected_id]
    top_5 = neighbors.nsmallest(5, 'neighbor_rank')
    # Add these to candidate pool with a boost
    candidates.update(top_5.neighbor_object_id)
```

This leverages the pre-computed DINOv2 visual similarity from HuggingFace.

### Step 3 Detail: Claude Ranking

Send a single prompt with:
- The user profile (compact JSON)
- ~400 candidate objects (title + classification + culture + 1-line description)
- Ask for top 30 ranked recommendations with tags and justifications

Use **prompt caching**: the artwork catalog is static, cache it as a system prompt. Only the user profile changes per request. This makes each request fast and cheap.

---

## Phase 3: Route Generation

### Input
- Top 20-40 recommended artworks, each tagged with gallery_number
- Time budget
- Fixed waypoints (e.g., "always pass through Chinese Garden")
- Gallery adjacency graph

### Gallery Grouping

Our 69 galleries cluster into a contiguous block (200-253) plus a few outliers:

| Range | Count | Area |
|-------|-------|------|
| 200-253 | 53 galleries | Main Asian Art wing (2nd floor) |
| 352-463 | ~8 galleries | Scattered (other wings) |
| 520-899 | ~8 galleries | Far-flung |

For the hackathon, focus on galleries 200-253 — that's where 96% of the objects are.

### Route Algorithm

```
1. Group recommended artworks by gallery
2. Score each gallery:
   gallery_score = sum(artwork_scores) + highlight_bonus + must_see_bonus
3. Select top N galleries based on time_budget:
   - 30 min → 4-5 galleries
   - 1 hr → 8-10 galleries  
   - 2 hr → 15-20 galleries
   - 3 hr → all relevant galleries
4. Order galleries into a walking path:
   - Start from entrance (Gallery 200)
   - Use nearest-neighbor heuristic through selected galleries
   - Insert fixed waypoints (Chinese Garden, etc.)
   - Add 1-2 "wander" galleries between stops
5. For each gallery on path, highlight:
   - "Must see" pieces (affinity picks)
   - "Look for" pieces (stretch picks)  
   - "Wander" suggestion (wildcard / serendipity)
```

### Fixed Waypoints

Hardcode a few must-visit spots:
- **Astor Court / Chinese Garden (Gallery 217)** — always route through
- Any current special exhibitions
- Iconic highlights the user hasn't explicitly chosen

### Spontaneity Layer

For each gallery transition, occasionally insert:
- "Take a detour through Gallery X on your way" (adjacent gallery not on main route)
- "Pause here and look around — what catches your eye?"
- "Ask someone nearby what their favorite piece in this room is"

---

## Phase 4: System Architecture

### Stack

```
┌─────────────────────────────────────┐
│         Mobile Web App              │
│   (React / Next.js, PWA)            │
│   - Survey UI                       │
│   - Route display with map          │
│   - Artwork cards with images       │
└──────────────┬──────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────┐
│         Server (Node/Python)        │
│   - POST /api/survey                │
│   - POST /api/recommend             │
│   - GET  /api/artwork/:id           │
│   - GET  /api/route/:session_id     │
└──────┬──────────────┬───────────────┘
       │              │
┌──────▼─────┐  ┌─────▼──────────────┐
│ Static Data│  │  Claude API        │
│ (JSON/CSV) │  │  - Ranking         │
│ - artworks │  │  - Justifications  │
│ - galleries│  │  - Route narration │
│ - neighbors│  └────────────────────┘
└────────────┘
```

### API Endpoints

**POST /api/survey**
- Receives survey answers
- Returns user profile + session_id

**POST /api/recommend**  
- Receives user profile
- Runs filter → expand → Claude rank pipeline
- Returns ranked artworks with justifications

**GET /api/route/:session_id**
- Returns ordered gallery path with artworks per gallery
- Includes timing estimates, map links, spontaneity prompts

### Data at Rest (loaded into memory on server start)

All pre-processed and stored as JSON:

```
data/
  artworks.json        — merged: metadata + descriptions + augmented fields
  galleries.json       — gallery_number → {objects, floor, adjacency}  
  neighbors.json       — object_id → [similar_object_ids]
  survey_images.json   — curated image sets for survey
```

### Key Optimization: Prompt Caching

The artwork catalog (~1,859 objects × ~200 chars each ≈ 370KB) fits easily in a Claude prompt. Cache this as the system prompt so it persists across requests. Each user request only sends the small user profile as the human message.

```python
# Cached system prompt (stays warm across users)
system = f"""You are a Met Museum tour guide AI. 
Here is the catalog of on-view Asian Art:
{artwork_catalog_json}

For each recommendation, provide:
- object_id
- category: affinity | stretch | wildcard  
- reason: 1 sentence why this person would enjoy it
"""

# Per-user request (small, fast)
user_msg = f"Here is the visitor profile: {user_profile_json}. 
Select the top 30 artworks and generate a gallery route."
```

---

## Data Prep Needed Before Building

1. **Merge all data into one artworks.json**
   - Join: metadata + descriptions + augmented_fields + colors
   - One record per object with all fields

2. **Build gallery adjacency map**
   - For galleries 200-253, determine which connect to which
   - Can approximate from gallery numbers or use Met floor plan

3. **Curate survey image sets**
   - Select 16 diverse, visually striking images
   - Ensure coverage across classification, culture, era, mood

4. **Create era buckets**
   - Map object_begin_date to: Ancient (<0), Medieval (0-1400), Early Modern (1400-1800), Modern (1800+)

5. **Create culture groups**  
   - Map 198 culture values to ~7 groups: China, Japan, Korea, South Asia, Southeast Asia, Tibet/Nepal, Other
