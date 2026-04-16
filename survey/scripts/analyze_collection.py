#!/usr/bin/env python3
"""
Analyze the Asian art collection to extract categories for survey questions
"""

import csv
import json
import re
from collections import Counter, defaultdict

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    return text.strip().strip('"').strip()

def analyze_collection(csv_path):
    """Analyze the collection and extract categories"""

    cultures = Counter()
    mediums = Counter()
    periods = Counter()
    galleries = Counter()
    themes = defaultdict(list)

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Track cultures
            culture = clean_text(row.get('culture', ''))
            if culture and len(culture) < 50:  # Filter out malformed data
                cultures[culture] += 1

            # Track mediums
            medium = clean_text(row.get('medium', ''))
            if medium:
                # Extract main medium type
                medium_lower = medium.lower()
                if 'porcelain' in medium_lower or 'ceramic' in medium_lower:
                    mediums['Ceramics & Porcelain'] += 1
                if 'painting' in medium_lower or 'handscroll' in medium_lower or 'scroll' in medium_lower:
                    mediums['Paintings & Scrolls'] += 1
                if 'bronze' in medium_lower or 'metal' in medium_lower:
                    mediums['Metalwork & Bronze'] += 1
                if 'wood' in medium_lower or 'lacquer' in medium_lower:
                    mediums['Wood & Lacquer'] += 1
                if 'jade' in medium_lower or 'stone' in medium_lower:
                    mediums['Jade & Stone'] += 1
                if 'silk' in medium_lower or 'textile' in medium_lower:
                    mediums['Textiles & Silk'] += 1
                if 'ink' in medium_lower and 'paper' in medium_lower:
                    mediums['Ink on Paper'] += 1

            # Track time periods
            date_str = clean_text(row.get('object_date', ''))
            if date_str:
                if 'century' in date_str.lower():
                    # Extract century references
                    if any(x in date_str.lower() for x in ['18th', '19th', '20th']):
                        periods['Modern Era (18-20th century)'] += 1
                    elif any(x in date_str.lower() for x in ['15th', '16th', '17th']):
                        periods['Late Imperial (15-17th century)'] += 1
                    elif any(x in date_str.lower() for x in ['11th', '12th', '13th', '14th']):
                        periods['Classical Period (11-14th century)'] += 1
                    elif any(x in date_str.lower() for x in ['5th', '6th', '7th', '8th', '9th', '10th']):
                        periods['Ancient Period (5-10th century)'] += 1

            # Track galleries
            gallery = clean_text(row.get('gallery_number', ''))
            if gallery and gallery.isdigit():
                galleries[gallery] += 1

            # Track themes in titles
            title = clean_text(row.get('title', '')).lower()
            if title:
                if any(word in title for word in ['buddha', 'deity', 'bodhisattva', 'shrine']):
                    themes['Religious & Spiritual'].append(row.get('object_id', ''))
                if any(word in title for word in ['landscape', 'mountain', 'river', 'nature']):
                    themes['Landscapes & Nature'].append(row.get('object_id', ''))
                if any(word in title for word in ['dragon', 'phoenix', 'bird', 'animal', 'horse']):
                    themes['Animals & Mythology'].append(row.get('object_id', ''))
                if any(word in title for word in ['vase', 'bowl', 'jar', 'dish', 'bottle']):
                    themes['Vessels & Containers'].append(row.get('object_id', ''))
                if any(word in title for word in ['figure', 'sculpture', 'statue']):
                    themes['Figures & Sculpture'].append(row.get('object_id', ''))

    return {
        'cultures': dict(cultures.most_common(10)),
        'mediums': dict(mediums.most_common(10)),
        'periods': dict(periods.most_common(10)),
        'galleries': dict(galleries.most_common(15)),
        'themes': {k: len(v) for k, v in themes.items()},
        'theme_objects': {k: v[:50] for k, v in themes.items()}  # Sample objects for each theme
    }

def generate_survey_config(analysis):
    """Generate survey configuration from analysis"""

    # Create interest categories
    interests = []

    # Add culture-based interests
    for culture, count in list(analysis['cultures'].items())[:5]:
        if count > 20:  # Only include cultures with significant representation
            interests.append({
                'id': culture.lower().replace(' ', '_').replace('(', '').replace(')', ''),
                'label': f'{culture} Art',
                'type': 'culture',
                'keywords': [culture.lower()],
                'count': count
            })

    # Add medium-based interests
    for medium, count in analysis['mediums'].items():
        if count > 20:
            interests.append({
                'id': medium.lower().replace(' ', '_').replace('&', 'and'),
                'label': medium,
                'type': 'medium',
                'keywords': medium.lower().split(),
                'count': count
            })

    # Add theme-based interests
    for theme, count in analysis['themes'].items():
        if count > 20:
            interests.append({
                'id': theme.lower().replace(' ', '_').replace('&', 'and'),
                'label': theme,
                'type': 'theme',
                'keywords': theme.lower().split(),
                'count': count
            })

    return {
        'interests': interests,
        'galleries': analysis['galleries'],
        'summary': {
            'total_cultures': len(analysis['cultures']),
            'total_mediums': len(analysis['mediums']),
            'total_themes': len(analysis['themes']),
            'total_galleries': len(analysis['galleries'])
        }
    }

if __name__ == '__main__':
    # Analyze the collection
    analysis = analyze_collection('../data/asian_art_on_view.csv')

    # Generate survey config
    config = generate_survey_config(analysis)

    # Save results
    with open('../data/collection_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)

    with open('../data/survey_config.json', 'w') as f:
        json.dump(config, f, indent=2)

    print("✓ Collection analysis complete!")
    print(f"  - {len(analysis['cultures'])} cultures identified")
    print(f"  - {len(analysis['mediums'])} medium types")
    print(f"  - {len(analysis['themes'])} themes")
    print(f"  - {len(analysis['galleries'])} galleries")
    print(f"\n✓ Generated {len(config['interests'])} survey interest categories")
    print(f"\nSaved to:")
    print(f"  - data/collection_analysis.json")
    print(f"  - data/survey_config.json")
