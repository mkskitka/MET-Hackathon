# Precomputation, Routing & Claude Strategy

## Can We Just Throw Everything Into Claude?

**Yes, with a caveat on size.**

| Catalog version | Size | Tokens | Fits in prompt? |
|----------------|------|--------|-----------------|
| Compact (no descriptions) | 542K chars | ~135K tokens | Yes — fits in Claude's context with room for reasoning |
| With truncated descriptions | 852K chars | ~213K tokens | Yes but tight — less room for reasoning |
| With full descriptions | ~2M chars | ~500K tokens | Too big for a single call |

**Recommended approach:** Send Claude the compact catalog (135K tokens) as a cached system prompt. This includes for each object: id, title, gallery, culture, date, classification, period, alt_text, and highlight status. That's enough for Claude to reason about matching.

For the ~30 objects Claude selects as recommendations, do a **second call** with their full curatorial descriptions to generate personalized justifications and tour narration.

### Two-Call Pipeline

```
Call 1: SELECT (cached catalog + user profile)
  System: [1,859 objects, compact format — CACHED]
  User: [survey results as JSON]
  Output: ranked list of ~30 object IDs with affinity/stretch/wildcard tags

Call 2: NARRATE (small, just the 30 selected objects with full descriptions)
  System: You are a museum guide. Generate personalized descriptions.
  User: [30 objects with full curatorial text + user profile]
  Output: per-object "why you'll love this" + route narrative
```

**Cost estimate per user:** ~135K cached input tokens ($0.04) + ~2K output ($0.02) = **~$0.06/user**

---

## What to Precompute (Before Claude Sees It)

### 1. Object Dimension Tags

Every object gets tagged with matchable dimensions. This is deterministic — no LLM needed.

```json
{
  "id": 49587,
  "title": "Mirror with Grapes and Fantastic Sea Animals",
  "gallery": 207,
  "culture_group": "east_asia",    // from culture field
  "era": "medieval",               // from object_begin_date
  "class_group": "metalwork",      // from classification
  "highlight": false,
  "alt_text": "Circular bronze mirror with relief carvings..."
}
```

**Culture groups:**
| Group | Count | Key cultures |
|-------|-------|-------------|
| east_asia | 896 | China |
| south_asia | 301 | India, Nepal, Pakistan, Sri Lanka |
| japan | 287 | Japan |
| southeast_asia | 282 | Thailand, Cambodia, Indonesia, Vietnam |
| korea | 42 | Korea |
| himalayan | 36 | Tibet |

**Era buckets:**
| Era | Count | Date range |
|-----|-------|------------|
| late_imperial | 748 | 1600–1900 (Qing, Edo) |
| medieval | 480 | 600–1300 (Tang, Song, Angkor) |
| early_modern | 213 | 1300–1600 (Yuan, Ming, Mughal) |
| ancient | 201 | pre-200 BCE (Shang, Zhou) |
| classical | 195 | 200 BCE–600 CE (Han, Gupta) |
| modern | 22 | 1900+ |

**Classification groups:**
| Group | Count | Types |
|-------|-------|-------|
| ceramics | 595 | Ceramics, Tomb Pottery, Glass |
| sculpture | 504 | Sculpture, Ivories, Horn |
| metalwork | 361 | Metalwork, Cloisonné, Enamels, Mirrors, Jewelry |
| jade_hardstone | 206 | Jade, Hardstone, Snuff Bottles |
| paintings | 88 | Paintings, Calligraphy |
| prints | 46 | Prints, Illustrated Books |
| furnishings | 34 | Furniture, Lacquer, Wood |

### 2. Gallery Profiles

Each gallery gets a precomputed profile so Claude (or the filter step) knows what's in each room without scanning all objects:

```json
{
  "207": {
    "count": 246,
    "highlights": 1,
    "floor": 2,
    "name": "Chinese Art: Ancient to Tang Dynasty",
    "primary_types": ["metalwork", "ceramics", "sculpture"],
    "primary_cultures": ["east_asia"],
    "primary_eras": ["medieval", "ancient"],
    "neighbors": ["210", "216", "215", "218"]
  }
}
```

Key gallery personalities:
| Gallery | Objects | Vibe |
|---------|---------|------|
| 200 | 52 | Chinese ceramics, late imperial, all porcelain |
| 204 | 63 | Chinese ceramics, early modern (Ming dynasty) |
| 207 | 246 | Ancient Chinese metalwork + ceramics (biggest gallery) |
| 219 | 118 | Jade & hardstone, Qing dynasty |
| 222 | 123 | Jade collection (largest jade gallery) |
| 231 | 76 | Japanese ceramics, Edo period |
| 234 | 51 | South Asian sculpture, ancient |
| 244 | 69 | Southeast Asian metalwork, ancient bronze |
| 247 | 90 | Southeast Asian sculpture, medieval |

### 3. Gallery Adjacency Graph

Built from center coordinates of the map data. Each gallery maps to its 4 nearest neighbors:

```
200 → [201, 202, 203, 204]       (Chinese ceramics cluster)
205 → [206, 234, 233, 204]       (bridge to South Asian)
210 → [217, 218, 232, 215]       (near Chinese Garden!)
217 → [210, 216, 215, 218]       (Chinese Garden - MUST VISIT)
231 → [224, 232, 230, 223]       (Japanese wing)
234 → [235, 233, 206, 236]       (South Asian sculpture)
244 → [245, 216, 253, 241]       (Southeast Asian wing)
247 → [252, 245, 253, 246]       (Southeast Asian sculpture)
```

**Saved to `data/gallery_adjacency.json`**

### 4. Survey Image Sets

Pre-curated sets of images for the survey questions. Select based on:
- `is_highlight = True` (104 total across 31 galleries)
- Visual diversity (different classifications, cultures, eras)
- Image quality (has `source_image_url` from HuggingFace)

---

## Routing: How Paths Work

### Time Budget → Gallery Count

| Time | Galleries | Coverage |
|------|-----------|----------|
| 30 min | 6 rooms | ~205 objects accessible |
| 1 hour | 12 rooms | ~410 objects accessible |
| 2 hours | 24 rooms | ~820 objects accessible |
| 3 hours | 36 rooms | ~1230 objects accessible |

### Distribution Problem

Art is clustered by type and culture. If someone says "I love jade," naive matching sends them to galleries 219 and 222 for 2 hours of nothing but jade. Bad experience.

**Solution: Gallery-level scoring with diversity constraints**

```
For each gallery, compute:
  match_score = how well its objects match the user profile
  diversity_bonus = penalty if profile already covers this type/culture
  highlight_bonus = extra weight for highlight objects
  adjacency_bonus = bonus if gallery is near already-selected galleries

Select galleries using a greedy algorithm:
  1. Pick highest-scoring gallery
  2. Re-score remaining galleries with diversity penalty
     (reduce score for galleries with same culture_group/class_group as already selected)
  3. Pick next highest
  4. Repeat until gallery count reached
  5. Insert Chinese Garden (217) if not already in path
```

### Route Ordering

Once galleries are selected, order them into a walking path:

```
1. Start at Gallery 200 (entrance to Asian Art wing)
2. Use nearest-neighbor through selected galleries via adjacency graph
3. Insert Gallery 217 (Chinese Garden) as a waypoint
4. For each gallery on path, select 2-4 "featured" objects:
   - 1-2 affinity picks (matches their interests)
   - 1 stretch pick (adjacent interest)
   - 0-1 wildcard (highlight or serendipity)
```

### Example Routes

**30-minute "Highlights" route (6 galleries):**
```
200 → 204 → 207 → 217 (Garden) → 231 → 247
 ↓      ↓      ↓                    ↓      ↓
 Qing   Ming   Ancient            Japanese  SE Asian
 porcelain ceramics bronzes        ceramics  sculpture
```

**1-hour "Culture Explorer" route (12 galleries):**
```
200 → 204 → 207 → 210 → 217 (Garden) → 219 → 222 → 231 → 234 → 244 → 247 → 252
  China ──────────────────────────────   Jade    Japan   India    SE Asia
```

### Per-Gallery Output

For each gallery on the route, the user sees:

```json
{
  "gallery": 207,
  "name": "Chinese Art: Ancient to Tang Dynasty",
  "time_estimate": "5 minutes",
  "featured_objects": [
    {
      "id": 49381,
      "title": "Set of twelve zodiac animals",
      "image": "https://images.metmuseum.org/CRDImages/as/mobile-large/...",
      "why": "These Tang dynasty tomb figures bring Chinese zodiac mythology to life — each animal wears court robes.",
      "tag": "affinity"
    },
    {
      "id": 49587,
      "title": "Mirror with Grapes and Sea Animals",
      "why": "While you're here, look for this — the bronze casting technique is extraordinary.",
      "tag": "stretch"
    }
  ],
  "wander_prompt": "Take a moment to look at the cases in the center of the room. What catches your eye?"
}
```

---

## Summary: What To Build

### Precompute once (data scripts):
1. ✅ Merged artwork dataset with all fields
2. ✅ Culture/era/classification group tags per object
3. ✅ Gallery profiles (what's in each room)
4. ✅ Gallery adjacency graph
5. [ ] Survey image sets (curate from highlights)
6. [ ] Compact catalog JSON for Claude prompt cache

### Per-user request (server):
1. Parse survey answers into profile weights
2. **Call 1 to Claude:** Select top ~30 objects from cached catalog
3. Apply gallery diversity constraints + routing algorithm
4. **Call 2 to Claude:** Generate per-object justifications + wander prompts
5. Return ordered route with featured objects per gallery

### What Claude handles vs what we handle:

| Task | Who | Why |
|------|-----|-----|
| Object selection & ranking | **Claude** | Needs semantic understanding of art + user intent |
| Gallery selection with diversity | **Code** | Deterministic optimization, no LLM needed |
| Route ordering | **Code** | Graph traversal, no LLM needed |
| Justification text | **Claude** | Creative writing, personalized |
| Wander prompts | **Claude** or precomputed | Could go either way |
| Image URL construction | **Code** | Just string replacement |
