# SURVEY ALGORITHM - EXAMPLE RUN

## Survey Collected Data

```json
{
  "q1": 120,                    // 2 hours visit
  "q2": "balanced",             // Balanced freedom level
  "q3": "focused",              // Go deep on one topic
  "q4": "ceramic",              // Prefers ceramic materials
  "q5": "stone",                // Also drawn to stone/jade
  "q6": "910524",               // Selected: Korean porcelain jar with peonies
  "q7": ["42246", "45553"],     // Selected 2 ceramic pieces from different periods
  "q8": "207",                  // Prefers Gallery 207
  "q9": ["Subtle", "Smooth", "Ancient", "Vibrant", "Intricate"]
}
```

## Question Flow Summary

### Q1: Duration (Static)
- **Answer:** 2 hours (120 minutes)
- **Impact:** Generates 10-12 stops

### Q2: Freedom Level (Static)
- **Answer:** Balanced
- **Impact:** Suggested route with flexibility, mix of highlights and discoveries

### Q3: Depth vs Breadth (Static)
- **Answer:** Focused (Go Deep)
- **Impact:** Focus on single theme with deep connections

### Q4: Material Texture 1 (Random Sample)
**Options Generated:**
1. ✓ **Ceramic** - Object #50342: "Small Dish (Kozara) with Three Jars" (Japan, Gallery 223)
2. **Metal** - Object #38945: "Hanuman Conversing" (India, Gallery 240)

**Answer:** Ceramic

### Q5: Material Texture 2 (Random Sample)
**Options Generated:**
1. ✓ **Stone/Jade** - Object #38314: "Standing Shiva" (Vietnam, Gallery 249)
2. **Wood** - Object #856282: "Table screen with landscape" (China, Gallery 220)

**Answer:** Stone

### Q6: GenAI Question (Ceramic + Stone)
**Generated Question:** "You're drawn to smooth, crafted surfaces. Which refined piece speaks to you?"

**GenAI Logic:**
- Detected material combination: ceramic + stone
- Applied template: smooth crafted surfaces
- Filtered for: porcelain OR jade objects
- Preferred: highlights only

**Options Generated:**
1. ✓ Object #910524: "Openwork jar with peonies" (Korea, late 18th c., Gallery 233)
2. Object #50342: "Small Dish with Three Jars" (Japan, 1680s, Gallery 223)
3. Object #42229: "Vase with peach-bloom glaze" (China, 1713-22, Gallery 200)

**Answer:** Korean porcelain jar (#910524)

### Q7: Complex GenAI (Freedom + Depth + Material)
**Generated Question:** "Explore ceramic evolution. Pick 2 from different styles."

**GenAI Logic:**
- Freedom = balanced → show variety
- Depth = focused → keep same material (ceramic)
- Material = ceramic → filter porcelain objects
- Strategy: Different cultures/time periods, same material

**Options Generated:**
1. ✓ Object #42246: Celadon vase (China, 1678-88, Gallery 200)
2. ✓ Object #45553: Freshwater jar with Seven Sages (Japan, 18th c., Gallery 227)
3. Object #52220: Small jar with flowers (Japan, 1640s, Gallery 227)
4. Object #63699: Set of everyday vessels (Japan, late 18th c., Gallery 229)

**Answer:** Objects #42246 and #45553 (Chinese and Japanese ceramics)

### Q8: Gallery Preference (Specific Galleries)
**Options Generated:**
- ✓ Gallery 207 (246 pieces) - Featured: Dish shaped like a leaf (China)
- Gallery 222 (123 pieces) - Featured: Bowl (India)
- Gallery 219 (118 pieces) - Featured: Vase shaped like flower (China)
- Gallery 247 (90 pieces) - Featured: Buddha Vairochana (Indonesia)

**Answer:** Gallery 207

### Q9: Emotion Words (Rapid Fire - 15 seconds)
**Word Cloud Generated (30 words):**
Pure, Harmonious, Tranquil, Majestic, Elegant, Mysterious, Vibrant, Serene, Striking, Powerful, Playful, Intricate, Contemplative, Smooth, Luminous, Peaceful, Subtle, Delicate, Bold, Ancient

**Selected (5 words):**
- Subtle
- Smooth
- Ancient
- Vibrant
- Intricate

**Mapped to Keywords:**
glaze, underglaze, monochrome, jade, nephrite, stone, polished, dynasty, bronze, color, polychrome, enamels, carved, decoration, inlay

---

## Recommendation Engine Input Summary

Based on collected survey data:

### User Profile
- **Duration:** 120 minutes → 10-12 stops
- **Experience Style:** Balanced freedom + Focused depth
- **Primary Interest:** Ceramic art (porcelain, glazed)
- **Secondary Interest:** Stone/jade work
- **Aesthetic Preferences:** Subtle, smooth, ancient, vibrant, intricate
- **Preferred Gallery:** 207 (Chinese art)

### Selected Objects (High Weight)
1. #910524 - Korean openwork jar (chosen in Q6)
2. #42246 - Chinese celadon vase (chosen in Q7)
3. #45553 - Japanese freshwater jar (chosen in Q7)

### Recommendation Strategy

**FOCUSED DEPTH Applied:**
Since user chose "focused" depth:
- **80% of stops:** Ceramic objects (porcelain, glazed)
- **20% related:** Jade/stone objects
- **Route:** 2-3 adjacent galleries (focus on 207, 200, maybe 219)
- **Learning connections:** Deep - ceramic evolution across cultures
- **Time period:** Mix of 17th-19th century (as shown in selections)

**BALANCED FREEDOM Applied:**
- Mix of highlights (famous) and lesser-known pieces
- Suggested order but allow flexibility
- Include 1-2 surprise discoveries

**Keyword Boosts:**
- High weight: porcelain, glaze, ceramic, jade, stone
- Medium weight: carved, decorated, intricate, polished
- Culture weight: China (primary), Japan, Korea
- Time period: 17th-19th century preferred

### Scavenger Hunt Design

**Learning Content Level:** Medium-Deep
- 150-200 word descriptions
- Focus on ceramic glazing techniques
- Cross-cultural comparisons (Chinese vs Japanese vs Korean ceramics)
- Evolution of porcelain styles

**Stop Examples:**
1. Chinese celadon vase (Gallery 200) - "How was this jade-like glaze created?"
2. Korean moon jar (Gallery 233) - "Compare this to Chinese white porcelain"
3. Japanese Imari bowl (Gallery 227) - "Notice the decorative differences"
4. Jade carving (Gallery 207) - "Surprise! See how jade influenced ceramic glazes"
...

**Route:**
Gallery 207 → 200 → 219 → 233 → 227
(Optimized for ceramic focus, includes preferred gallery)

---

## Data Sources Used

All data pulled from:
- `asian_art_on_view.csv` - 1,859 objects
- `text_embeddings.json` - 50 keywords + object mappings
- `collection_analysis.json` - Gallery statistics

**No external data used - 100% from dataset**
