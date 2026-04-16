# Data Vocabulary — Matching Dimensions

All values derived from the 1,859 on-view Asian Art objects.

## Geographic Origin (from `culture`)

| Group | Cultures | Object Count |
|-------|----------|-------------|
| **China** | China | 885 |
| **Japan** | Japan | 287 |
| **Southeast Asia** | Indonesia (Java +), Thailand (+variants), Vietnam, Cambodia, Burma | ~180 |
| **South Asia** | India (+regions), Nepal, Sri Lanka, Bangladesh, Pakistan (Gandhara) | ~130 |
| **Korea** | Korea | 42 |
| **Himalayan** | Tibet, Central Asia, Afghanistan | ~30 |

## Time Period (from `period` + `object_begin_date`)

| Group | Dates | Key Periods | Object Count |
|-------|-------|-------------|-------------|
| **Ancient** | pre-200 BCE | Shang, Zhou, Neolithic | ~100 |
| **Classical** | 200 BCE–600 CE | Han, Gupta, Kushan, Kofun | ~200 |
| **Medieval** | 600–1300 CE | Tang, Song, Angkor, Goryeo, Heian, Chola, Pala | ~425 |
| **Early Modern** | 1300–1600 CE | Yuan, Ming, Muromachi, Joseon, Mughal | ~210 |
| **Late Imperial** | 1600–1900 CE | Qing (~400), Edo (~215) | ~540 |
| **Modern** | 1900+ | Small handful | ~20 |

Biggest cluster: **1700s (343 objects)** — Qing China + Edo Japan.

## Object Type (from `classification`)

| Group | Classifications | Count |
|-------|----------------|-------|
| **Ceramics** | Ceramics, Tomb Pottery, Glass | ~595 |
| **Sculpture** | Sculpture, Ivories, Horn, Stone | ~500 |
| **Metalwork** | Metalwork, Cloisonné, Enamels, Mirrors, Jewelry | ~380 |
| **Jade & Hardstone** | Jade, Hardstone, Snuff Bottles, Bamboo | ~200 |
| **Paintings & Scrolls** | Paintings, Calligraphy, Manuscripts | ~90 |
| **Prints** | Prints, Illustrated Books, Rubbing | ~45 |
| **Furnishings** | Furniture, Lacquer, Wood | ~30 |

## Subject Matter (from visual descriptions)

| Category | Frequency | Examples |
|----------|-----------|---------|
| **Vessels & Decorative** | Largest overall | Porcelain vases, cloisonné, lacquer boxes |
| **Religious & Deity** | Very common in sculpture | Buddha, Bodhisattva, Shiva, Ganesha |
| **Landscape & Nature** | ~25-30% of paintings | Mountains, rivers, pine trees, plum blossoms |
| **Animals & Mythical** | Common across media | Dragons, horses, phoenix, makara |
| **Human Figures** | Moderate | Court portraits, scholars, narrative scenes |
| **Calligraphy & Text** | Small but distinct | Hanging scrolls, rubbings, seals |
| **Geometric & Abstract** | Mostly ancient | Incised patterns, bronze mirrors, openwork |

## Mood / Aesthetic (derived from descriptions)

| Mood | Typical Objects |
|------|----------------|
| **Serene / Contemplative** | Monochrome ink landscapes, celadon bowls, Buddha sculptures |
| **Ornate / Lush** | Cloisonné vessels, lacquer boxes, Mughal jewelry, Tang gold |
| **Powerful / Divine** | Multi-armed deities, fierce bronze figures, monumental stone |
| **Intimate / Scholarly** | Album leaves, calligraphy fans, scholar's objects |
| **Ancient / Earthly** | Shang bronzes, prehistoric pottery, tomb figures |
| **Narrative / Festive** | Court scene scrolls, processions, figural lacquer |

## Survey → Dimension Mapping

| Survey Question | Maps To |
|----------------|---------|
| "How much time?" | Number of galleries to visit |
| "Ancient or Modern?" | Time period weight |
| "Spiritual or Everyday?" | Subject matter (religious vs decorative/vessels) |
| "Grand or Intimate?" | Mood (powerful vs intimate/scholarly) |
| "Colorful or Subdued?" | Mood (ornate vs serene) + color data |
| Rate categories | Classification weight |
| Rate cultures | Culture weight |
| Pick images | Neighbor expansion + all-dimension inference |
