# Met Museum Survey - Interactive Question System

Dynamic survey system that generates personalized museum tours based on user preferences.

## Features

- ✅ 9 interactive questions
- 🤖 2 AI-generated questions (Q6, Q7) that adapt based on previous answers
- 🖼️ Multi-image selection from real Met Museum collection
- 📊 Real-time data from 1,859 Asian art objects
- ⚡ Keyword extraction and text embeddings
- 🎯 Personalized recommendations

## Quick Start

### Run Locally

1. Start a local web server:
```bash
cd MET-Hackathon
python3 -m http.server 8000
```

2. Open in browser:
```
http://localhost:8000/survey/survey_test.html
```

## Survey Flow

```
Q1: Duration → Q2: Freedom → Q3: Depth → Q4: Materials (multi-select) →
Q5: Subjects (multi-select) → Q6: AI-Generated → Q7: AI-Generated →
Q8: Gallery → Q9: Emotion Words
```

## Data Files

- **asian_art_on_view.csv** - 1,859 artworks
- **text_embeddings.json** - 50 keywords
- **collection_analysis.json** - Statistics
- **survey_config.json** - Categories

## Example Output

```json
{
  "q1": 120,
  "q2": "balanced",
  "q3": "focused",
  "q4": ["ceramic", "stone"],
  "q5": ["religious", "nature"],
  "q6": "910524",
  "q7": ["42246", "45553"],
  "q8": "207",
  "q9": ["Subtle", "Smooth", "Ancient", "Vibrant", "Intricate"]
}
```

Built for MET Hackathon 2026
