# Met API Data Shape & Profile Design Research

## Data Shape Per Object

Each object from the Met Open Access API returns the following fields relevant to our project:

| Field | Type | Example | Profile Use |
|---|---|---|---|
| `tags` | array of `{term, AAT_URL, Wikidata_URL}` | `[{term: "Lakes"}, {term: "Mountains"}]` | **Primary matching signal** — subject matter preferences |
| `department` | string | `"Asian Art"` | Broad interest area |
| `classification` | string | `"Sculpture"`, `"Paintings"` | Medium/form preference |
| `medium` | string | `"Oil on canvas"` | Granular material preference |
| `culture` | string | `"American"`, `"Italian"` | Cultural/geographic interest |
| `objectBeginDate` / `objectEndDate` | int | `-3600` to `1909` | Era preference |
| `objectDate` | string | `"late 16th century"` | Human-readable era |
| `GalleryNumber` | string | `"737"` | **Routing** — physical location |
| `primaryImageSmall` | URL | `https://images.metmuseum.org/...` | **Survey** — show images for selection |
| `isHighlight` | bool | | Prioritize famous works |

### Sample Object

```json
{
  "objectID": 10381,
  "title": "Mountain Lake Scene",
  "artistDisplayName": "John William Casilear",
  "department": "The American Wing",
  "classification": "",
  "medium": "Oil on canvas",
  "culture": "American",
  "objectDate": "1883",
  "objectBeginDate": 1883,
  "objectEndDate": 1883,
  "tags": [
    {
      "term": "Lakes",
      "AAT_URL": "http://vocab.getty.edu/page/aat/300008680",
      "Wikidata_URL": "https://www.wikidata.org/wiki/Q23397"
    },
    {
      "term": "Mountains",
      "AAT_URL": "http://vocab.getty.edu/page/aat/300008795",
      "Wikidata_URL": "https://www.wikidata.org/wiki/Q8502"
    },
    {
      "term": "Boats",
      "AAT_URL": "http://vocab.getty.edu/page/aat/300178749",
      "Wikidata_URL": "https://www.wikidata.org/wiki/Q35872"
    }
  ],
  "GalleryNumber": "737",
  "primaryImageSmall": "https://images.metmuseum.org/CRDImages/ad/web-large/APS1620.jpg"
}
```

### Tag Structure

Tags are the richest signal for profile matching. Each tag includes:
- `term` — human-readable subject label (e.g. "Men", "Flowers", "Buddhism")
- `AAT_URL` — link to Getty Art & Architecture Thesaurus (structured art vocabulary)
- `Wikidata_URL` — link to Wikidata entity (enables semantic expansion)

From our sample of 107 on-view objects:
- **50% have tags** (expect similar ratio across full 45k dataset)
- **69 unique tag terms** in sample alone
- Top tags: Men (17), Women (10), Christ (7), Birds (6), Flowers (4), Houses (4)

### Field Coverage (from 107-object sample)

| Field | Coverage | Notes |
|---|---|---|
| `GalleryNumber` | 100% | All on-view objects had this (since we filtered by `isOnView`) |
| `primaryImageSmall` | 81% | Most have images, some don't |
| `tags` | 50% | Half have structured tags |
| `department` | 100% | Always present |
| `classification` | 80% | Usually present but sometimes empty |
| `culture` | 46% | Often empty, especially for well-known European art |
| `artistDisplayName` | 40% | Many objects are unattributed |
| `medium` | 95% | Almost always present |

### Departments (19 total in Met)

From our sample: European Sculpture and Decorative Arts (39), The American Wing (39), Robert Lehman Collection (12), Asian Art (10), Musical Instruments (4), Egyptian Art (2), Arms and Armor (1)

### Gallery Numbers

Gallery numbers are strings, ranging from low hundreds to 950s. They appear to map roughly to:
- 100-200s: Egyptian, Ancient Near Eastern
- 300s: Arms and Armor, Medieval
- 500s: European Sculpture and Decorative Arts
- 600-700s: American Wing, European Paintings
- 800s: Modern and Contemporary
- 900s: Robert Lehman Collection

---

## Profile Design

### Dimensions

Based on the available data, a visitor profile can be modeled as a weighted vector across these dimensions:

1. **Subject matter** (from `tags`) — nature, portraits, religion, mythology, animals, war, domestic life, etc.
2. **Era** (from date fields) — ancient (-3600 to 0), medieval (0-1400), renaissance (1400-1600), baroque/early modern (1600-1800), modern (1800-1900), contemporary (1900+)
3. **Culture/region** (from `culture`) — European, Asian, American, Egyptian, African, etc.
4. **Form** (from `classification`) — paintings, sculpture, ceramics, textiles, metalwork, furniture, etc.
5. **Vibe** (derived/inferred by Claude) — contemplative, dramatic, decorative, monumental, intimate, etc.

### Survey Approach

~5 minutes, designed to extract preferences across these dimensions:

- **Direct questions** — "What draws you to a museum?" (learning, beauty, escapism, social)
- **Image selection** — Show curated sets of artwork images, ask visitors to pick favorites. Infer preferences from selections.
- **Binary/swipe choices** — "Ancient or Modern?", "Grand or Intimate?", abstract vs. representational
- **Open-ended** — "Describe your ideal afternoon" (Claude can extract latent preferences)

### Matching Strategy: The Middle Ground

For matching profiles to gallery routes:

| Category | Weight | Description |
|---|---|---|
| **Affinity** | 70% | Things that match their stated interests — the "you'll love this" picks |
| **Stretch** | 20% | Adjacent to their interests but new territory — the "you might not expect this" picks |
| **Wildcard** | 10% | Completely random high-quality objects along the route — the "serendipity" picks |

### Justification Layer

For each recommended artwork, we can generate a short explanation:
- **Affinity picks**: "Based on your love of [landscapes], this [Hudson River School painting] is a must-see"
- **Stretch picks**: "You gravitate toward [sculpture], so you might be surprised by how [this ceramic piece] plays with similar ideas of form"
- **Wildcard picks**: "This is one of the Met's hidden gems — we thought you'd enjoy stumbling upon it"

### Spontaneity Mechanics

To build in wandering and discovery:
- **Loose routing**: Don't prescribe a strict path. Give a set of "anchor" galleries with suggested detours
- **Gallery clusters**: Group nearby galleries so visitors naturally flow between them
- **"If you have time" picks**: Optional stops near the main route
- **Surprise prompts**: "Take the next left and see what catches your eye before heading to Gallery 737"
- **No time pressure**: Frame as "highlights to find" rather than "stops on a tour"
