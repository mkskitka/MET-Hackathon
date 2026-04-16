#!/usr/bin/env python3
"""
Extract keywords and text embeddings from the Asian art dataset
"""

import csv
import json
import re
from collections import Counter

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    return text.strip().strip('"').strip()

def extract_keywords_from_text(text):
    """Extract meaningful keywords from text"""
    # Remove common articles and prepositions
    stop_words = {'with', 'and', 'the', 'of', 'in', 'on', 'a', 'an', 'for', 'to', 'from', 'by'}

    # Split and clean
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

    # Filter out stop words and short words
    keywords = [w for w in words if w not in stop_words and len(w) > 3]

    return keywords

def analyze_text_embeddings(csv_path):
    """Analyze all text content to extract keyword embeddings"""

    # Collectors
    title_keywords = Counter()
    medium_keywords = Counter()
    all_descriptive_words = Counter()

    # Object-level data for sampling
    objects_by_keyword = {}
    objects_by_material = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            obj_id = row.get('object_id', '')

            # Extract from title
            title = clean_text(row.get('title', ''))
            if title:
                keywords = extract_keywords_from_text(title)
                title_keywords.update(keywords)
                all_descriptive_words.update(keywords)

                # Store objects by keyword for sampling
                for kw in keywords:
                    if kw not in objects_by_keyword:
                        objects_by_keyword[kw] = []
                    objects_by_keyword[kw].append({
                        'object_id': obj_id,
                        'title': title,
                        'culture': clean_text(row.get('culture', '')),
                        'gallery': clean_text(row.get('gallery_number', '')),
                        'is_highlight': row.get('is_highlight', 'False')
                    })

            # Extract from medium
            medium = clean_text(row.get('medium', ''))
            if medium:
                med_keywords = extract_keywords_from_text(medium)
                medium_keywords.update(med_keywords)
                all_descriptive_words.update(med_keywords)

                # Store objects by material
                for kw in med_keywords:
                    if kw not in objects_by_material:
                        objects_by_material[kw] = []
                    objects_by_material[kw].append(obj_id)

    # Get top keywords that appear frequently enough to be meaningful
    top_keywords = [kw for kw, count in all_descriptive_words.most_common(100) if count >= 10]

    # Categorize keywords
    material_words = ['porcelain', 'jade', 'bronze', 'wood', 'silk', 'lacquer', 'stone',
                      'ceramic', 'metal', 'iron', 'gold', 'silver', 'clay', 'glass',
                      'terracotta', 'marble', 'ivory']

    subject_words = ['buddha', 'dragon', 'bird', 'flower', 'landscape', 'mountain',
                     'deity', 'bodhisattva', 'phoenix', 'horse', 'lotus', 'cloud',
                     'scholar', 'garden', 'water', 'tree', 'figure', 'animal']

    object_type_words = ['vase', 'bowl', 'dish', 'bottle', 'jar', 'plate', 'cup',
                         'sculpture', 'statue', 'painting', 'scroll', 'screen',
                         'box', 'vessel', 'plaque', 'panel', 'robe', 'textile']

    decorative_words = ['floral', 'decorated', 'painted', 'carved', 'engraved',
                        'inlaid', 'enameled', 'glazed', 'polished', 'relief']

    return {
        'top_keywords': top_keywords[:50],
        'keyword_counts': dict(all_descriptive_words.most_common(50)),
        'categorized_keywords': {
            'materials': [kw for kw in top_keywords if kw in material_words],
            'subjects': [kw for kw in top_keywords if kw in subject_words],
            'object_types': [kw for kw in top_keywords if kw in object_type_words],
            'decorative': [kw for kw in top_keywords if kw in decorative_words]
        },
        'objects_by_keyword': {kw: objects_by_keyword[kw][:20] for kw in top_keywords if kw in objects_by_keyword},
        'sample_size': {kw: len(objects_by_keyword.get(kw, [])) for kw in top_keywords}
    }

if __name__ == '__main__':
    result = analyze_text_embeddings('../data/asian_art_on_view.csv')

    with open('../data/text_embeddings.json', 'w') as f:
        json.dump(result, f, indent=2)

    print("✓ Text embedding analysis complete!")
    print(f"\n📊 Extracted {len(result['top_keywords'])} top keywords")
    print(f"\n🎨 Categorized Keywords:")
    print(f"  Materials: {len(result['categorized_keywords']['materials'])} words")
    print(f"  Subjects: {len(result['categorized_keywords']['subjects'])} words")
    print(f"  Object Types: {len(result['categorized_keywords']['object_types'])} words")
    print(f"  Decorative: {len(result['categorized_keywords']['decorative'])} words")

    print(f"\n🔑 Top 20 Keywords by Frequency:")
    for kw, count in list(result['keyword_counts'].items())[:20]:
        print(f"  {kw}: {count}")

    print(f"\n✓ Saved to data/text_embeddings.json")
