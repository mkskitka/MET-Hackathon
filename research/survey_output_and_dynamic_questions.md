# Survey Output Format & Dynamic Question Generation

## Part 1: Survey Output Example

This is what the server receives when a user completes the survey. Everything downstream (Claude ranking, routing, narration) works from this object.

### Complete Survey Response

```json
{
  "session_id": "abc123",
  "timestamp": "2026-04-16T14:30:00Z",
  
  "q1_duration_minutes": 60,
  
  "q2_freedom_level": "balanced",
  
  "q3_depth_preference": "variety",
  
  "q4_material_preference": {
    "selected": "ceramic",
    "options_shown": ["ceramic", "metal"],
    "images_shown": [42229, 42183]
  },
  
  "q5_material_preference": {
    "selected": "stone",
    "options_shown": ["stone", "wood"],
    "images_shown": [49369, 44858]
  },
  
  "q6_genai_selection": {
    "selected_object_id": 39666,
    "options_shown": [39666, 39496, 42229],
    "prompt_context": "Based on your interest in ceramics and stone"
  },
  
  "q7_genai_selection": {
    "selected_object_ids": [63532, 50799],
    "options_shown": [63532, 50799, 65095, 39346],
    "prompt_context": "Balanced tour with variety depth, ceramic + stone focus"
  },
  
  "q8_gallery_preference": {
    "selected_gallery": 207,
    "options_shown": [207, 231, 247, 252],
    "images_shown": [42183, 47258, 63532, 50799]
  },
  
  "q9_emotion_keywords": ["peaceful", "ancient", "surprising", "intricate", "spiritual"]
}
```

### Derived Profile (computed from survey, sent to Claude)

```json
{
  "session_id": "abc123",
  "time_budget_minutes": 60,
  "num_galleries": 12,
  "freedom": "balanced",
  "depth": "variety",
  
  "weights": {
    "culture": {
      "east_asia": 0.7,
      "japan": 0.4,
      "south_asia": 0.5,
      "southeast_asia": 0.6,
      "korea": 0.3,
      "himalayan": 0.4
    },
    "classification": {
      "ceramics": 0.9,
      "jade_hardstone": 0.8,
      "sculpture": 0.6,
      "metalwork": 0.4,
      "paintings": 0.3,
      "prints": 0.2,
      "furnishings": 0.2
    },
    "era": {
      "ancient": 0.7,
      "classical": 0.5,
      "medieval": 0.6,
      "early_modern": 0.5,
      "late_imperial": 0.4,
      "modern": 0.2
    }
  },
  
  "selected_object_ids": [39666, 63532, 50799],
  "emotion_keywords": ["peaceful", "ancient", "surprising", "intricate", "spiritual"],
  "preferred_gallery": 207,
  "open_text": null,
  
  "content_style": {
    "description_length": "short",
    "tone": "fun_facts",
    "connections": "visual_callouts"
  }
}
```

### How Weights Are Computed

```
Q4 selected "ceramic" → ceramics += 0.5, metal types += 0.0
Q5 selected "stone" → jade_hardstone += 0.5, furnishings += 0.0
Q6 selected object 39666 (Chinese porcelain jar, early 15th c, Gallery 202)
   → east_asia += 0.2, ceramics += 0.2, early_modern += 0.2
Q7 selected objects 63532 (Thai Buddha) + 50799 (Nepali Tara)
   → southeast_asia += 0.2, south_asia += 0.2, sculpture += 0.3
Q8 selected gallery 207 (ancient Chinese bronzes/ceramics)
   → east_asia += 0.1, ancient += 0.3, medieval += 0.2
Q9 keywords "peaceful, ancient, spiritual"
   → sculpture += 0.1 (spiritual → Buddhist sculpture)
   → ancient += 0.2, medieval += 0.1
```

Base weights start at 0.3 for everything, then get boosted by each answer. Final weights are normalized to 0-1 range.

---

## Part 2: Dynamic Question Generation

Questions Q6, Q7, and Q8 are **dynamic** — the images shown depend on previous answers. Here's how to generate them.

### Architecture

```
Q1-Q5 (static)
  ↓ answers
Dynamic Question Engine
  ↓ selects images
Q6-Q8 (dynamic, images chosen per user)
```

The engine needs:
1. Previous answers as input
2. The precomputed artwork catalog
3. Logic to select diverse, relevant images

### Precomputed: Image Candidate Pools

Build these once at startup. Each pool is a list of objects pre-filtered and ready to sample from.

```json
{
  "by_classification": {
    "ceramics": [42229, 39496, 39666, ...],
    "sculpture": [63532, 65095, 50799, ...],
    "metalwork": [42183, 39325, 39346, ...],
    "jade_hardstone": [49369, 39844, ...],
    "paintings": [42716, 44858, 40055, ...],
    "prints": [...],
    "furnishings": [...]
  },
  "by_culture": {
    "east_asia": [...],
    "japan": [...],
    "south_asia": [...],
    "southeast_asia": [...],
    "korea": [...],
    "himalayan": [...]
  },
  "by_era": {
    "ancient": [...],
    "classical": [...],
    "medieval": [...],
    "early_modern": [...],
    "late_imperial": [...],
    "modern": [...]
  },
  "highlights": [42229, 39496, 63532, 50799, 42716, ...]
}
```

**Priority order for image selection:**
1. `is_highlight = True` objects first (they're the best/most striking)
2. Has a good `output_alt_text` (so we can show a caption)
3. Has `source_image_url` (obviously)
4. Diverse gallery numbers (don't show 3 images from the same room)

### Q6: GenAI Combo Question (material-based)

**Input:** Q4 answer (ceramic vs metal) + Q5 answer (stone vs wood)

**Logic:**
```python
def generate_q6(q4_choice, q5_choice):
    # Map choices to classification groups
    material_map = {
        "ceramic": "ceramics",
        "metal": "metalwork", 
        "stone": "jade_hardstone",
        "wood": "furnishings"
    }
    
    primary_class = material_map[q4_choice]   # e.g. "ceramics"
    secondary_class = material_map[q5_choice]  # e.g. "jade_hardstone"
    
    # Select 3 images:
    # 1 from primary classification
    # 1 from secondary classification  
    # 1 that combines both or is a stretch pick
    candidates = []
    candidates += sample_from_pool("by_classification", primary_class, n=1)
    candidates += sample_from_pool("by_classification", secondary_class, n=1)
    
    # Third image: pick from a DIFFERENT culture than the first two
    used_cultures = {get_culture(c) for c in candidates}
    stretch = sample_excluding_cultures("highlights", used_cultures, n=1)
    candidates += stretch
    
    return {
        "question": f"Which of these catches your eye?",
        "context": f"Based on your interest in {q4_choice} and {q5_choice}",
        "options": candidates  # [{id, title, image_url, alt_text}, ...]
    }
```

### Q7: GenAI Combo Question (freedom + depth + material)

**Input:** Q2 (freedom_level) + Q3 (depth_preference) + Q4 (material)

**Logic:**
```python
def generate_q7(freedom_level, depth_preference, q4_choice):
    material_class = material_map[q4_choice]
    
    if depth_preference == "focused":
        # Show 4 objects from SAME classification but different cultures
        candidates = sample_diverse_cultures(material_class, n=4)
    elif depth_preference == "variety":
        # Show 4 objects from DIFFERENT classifications
        all_classes = ["ceramics", "sculpture", "metalwork", "jade_hardstone", "paintings"]
        candidates = [sample_from_pool("by_classification", c, n=1)[0] for c in all_classes[:4]]
    else:  # mixed
        # 2 from preferred class, 2 from different classes
        candidates = sample_from_pool("by_classification", material_class, n=2)
        other_classes = [c for c in all_classes if c != material_class]
        candidates += [sample_from_pool("by_classification", c, n=1)[0] for c in random.sample(other_classes, 2)]
    
    if freedom_level == "curated":
        # Bias toward highlights
        candidates = sort_highlights_first(candidates)
    elif freedom_level == "free":
        # Bias toward hidden gems
        candidates = sort_non_highlights_first(candidates)
    
    return {
        "question": "Pick 2 artworks you'd love to see in person",
        "context": f"Curating a {depth_preference} experience with {material_class}",
        "options": candidates,  # show 4, user picks 2
        "select_count": 2
    }
```

### Q8: Gallery Preference (image-based)

**Input:** All previous answers

**Logic:**
```python
def generate_q8(profile_so_far):
    # Pick 4 galleries that represent different experiences
    # Each gallery image should be its top highlight
    
    gallery_candidates = [
        {"gallery": 207, "vibe": "Ancient Chinese bronzes & tomb art"},
        {"gallery": 231, "vibe": "Japanese ceramics & woodblock prints"},
        {"gallery": 247, "vibe": "Southeast Asian sculpture"},
        {"gallery": 252, "vibe": "Himalayan Buddhist art"},
        {"gallery": 222, "vibe": "Chinese jade collection"},
        {"gallery": 210, "vibe": "Chinese paintings & scrolls"},
        {"gallery": 234, "vibe": "South Asian sculpture"},
        {"gallery": 244, "vibe": "Southeast Asian bronzes"},
    ]
    
    # Select 4 that maximize diversity relative to what user already picked
    selected = select_diverse_galleries(gallery_candidates, profile_so_far, n=4)
    
    # For each gallery, pick its most visually striking object as the preview
    for g in selected:
        g["preview_object"] = get_best_image_in_gallery(g["gallery"])
    
    return {
        "question": "Which gallery vibe calls to you?",
        "options": selected  # [{gallery, vibe, preview_image, alt_text}, ...]
    }
```

### Q9: Emotion Keywords

This one is static — show the same word grid to everyone. But the words should be drawn from what actually exists in the data.

**Suggested word grid (pick 5):**

| | | | |
|---|---|---|---|
| peaceful | powerful | playful | mysterious |
| ancient | intricate | spiritual | surprising |
| colorful | monumental | intimate | earthy |
| elegant | fierce | whimsical | haunting |

These map to mood/aesthetic dimensions in the data vocabulary and help Claude write the right tone of descriptions.

---

## Part 3: Using This With Claude

### Dynamic Question Generation — Do We Need Claude?

**No.** The dynamic questions are best handled with deterministic code:
- Image selection is a filtering + sampling problem
- The pools are precomputed
- Randomness makes each survey feel fresh
- It's instant (no API latency in the middle of the survey)

### Where Claude Comes In

Claude enters AFTER the survey is complete:

```
Survey complete → profile JSON
                       ↓
              Claude Call 1 (SELECT)
              "Given this profile, pick the top 30 artworks
               from this catalog of 1,859 objects.
               Tag each as affinity/stretch/wildcard.
               Consider gallery diversity."
                       ↓
              Code: route optimization
              (gallery selection, ordering, diversity)
                       ↓
              Claude Call 2 (NARRATE)
              "For these 30 artworks, write personalized
               1-2 sentence descriptions matching the
               visitor's depth_preference and emotion_keywords.
               Style: {variety → fun facts, focused → scholarly,
               mixed → conversational}"
                       ↓
              Final route JSON → mobile app
```

### Claude Prompt for Call 1 (cached catalog)

```
System (CACHED — same for all users):
You are a Met Museum tour guide selecting artworks for a visitor.

Here is the catalog of 1,859 on-view Asian Art objects:
[{id, title, gallery, culture_group, era, class_group, alt_text, highlight}, ...]

Rules:
- Select exactly 30 objects
- Tag each: "affinity" (matches preferences), "stretch" (adjacent/surprising), "wildcard" (hidden gem)
- Ratio: ~20 affinity, ~7 stretch, ~3 wildcard
- DISTRIBUTE across at least 8 different galleries
- No more than 4 objects from any single gallery
- Prefer highlights but include hidden gems
- Include objects near Gallery 217 (Chinese Garden — mandatory stop)

User (per-request):
Visitor profile:
{profile JSON}

Return JSON array: [{id, tag, reason}]
```

### Claude Prompt for Call 2 (narration)

```
System:
You are writing a personalized museum guide for a visitor.
Depth: {variety|focused|mixed}
Emotion keywords: {keywords}
Tone: {fun_facts|scholarly|conversational}

User:
Here are the 30 selected artworks with full details:
[{id, title, culture, date, medium, curatorial_description, classification, alt_text, tag, reason}]

Gallery route order: [207, 210, 217, 231, ...]

For each artwork, write:
- A 1-2 sentence personalized description matching the tone
- For "stretch" picks: explain the unexpected connection
- For "wildcard" picks: frame as a delightful surprise

Also write:
- A one-line intro for each gallery ("Welcome to Gallery 207 — here the ancient world comes alive in bronze")
- 2-3 "wander prompts" to insert between galleries

Return JSON.
```
