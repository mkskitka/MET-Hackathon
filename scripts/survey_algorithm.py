#!/usr/bin/env python3
"""
Complete Survey Algorithm - Generates dynamic questions from dataset
"""

import csv
import json
import random
from collections import defaultdict

class SurveyEngine:
    def __init__(self, csv_path, embeddings_path):
        self.objects = []
        self.embeddings = {}
        self.load_data(csv_path, embeddings_path)

        # Survey state
        self.answers = {}

    def load_data(self, csv_path, embeddings_path):
        """Load Asian art data and text embeddings"""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.objects = [row for row in reader]

        with open(embeddings_path, 'r', encoding='utf-8') as f:
            self.embeddings = json.load(f)

        print(f"✓ Loaded {len(self.objects)} artworks")
        print(f"✓ Loaded {len(self.embeddings['top_keywords'])} keywords\n")

    def clean_text(self, text):
        """Clean text field"""
        return text.strip().strip('"').strip() if text else ""

    # ==================== QUESTION 1: DURATION ====================
    def question_1_duration(self):
        """Q1: How long do you have?"""
        return {
            'id': 'q1',
            'type': 'single_choice',
            'question': 'How long do you have at the MET today?',
            'options': [
                {'value': 30, 'label': '⏱️ Quick Visit (30 min)', 'stops': '3-4 stops'},
                {'value': 60, 'label': '🚶 Focused Tour (1 hour)', 'stops': '5-6 stops'},
                {'value': 120, 'label': '🎨 Deep Dive (2 hours)', 'stops': '10-12 stops'},
                {'value': 180, 'label': '🏛️ Full Experience (3+ hours)', 'stops': '15+ stops'}
            ]
        }

    # ==================== QUESTION 2: FREEDOM LEVEL ====================
    def question_2_freedom(self):
        """Q2: How free do you want to be?"""
        return {
            'id': 'q2',
            'type': 'single_choice',
            'question': 'How do you want to experience the museum today?',
            'options': [
                {
                    'value': 'curated',
                    'label': '🎯 Guide me - I want a curated journey',
                    'description': 'Structured path with detailed information'
                },
                {
                    'value': 'balanced',
                    'label': '🗺️ Balance - Direction with room to explore',
                    'description': 'Suggested route with flexibility'
                },
                {
                    'value': 'free',
                    'label': '🦋 Free spirit - I want to wander',
                    'description': 'Loose suggestions, maximum serendipity'
                }
            ]
        }

    # ==================== QUESTION 3: DEPTH VS BREADTH ====================
    def question_3_depth(self):
        """Q3: Depth or breadth?"""
        return {
            'id': 'q3',
            'type': 'single_choice',
            'question': 'How do you like to explore art?',
            'options': [
                {
                    'value': 'focused',
                    'label': '🎯 Go Deep - Immerse me in one story',
                    'description': 'Focus on single theme with deep connections'
                },
                {
                    'value': 'mixed',
                    'label': '🌈 Mix It Up - Variety with connections',
                    'description': 'Balanced journey through related themes'
                },
                {
                    'value': 'variety',
                    'label': '🎨 Surprise Me - Maximum variety',
                    'description': 'Different cultures, periods, styles at every stop'
                }
            ]
        }

    # ==================== QUESTION 4: MATERIAL SWATCHES 1 ====================
    def question_4_material_1(self):
        """Q4: Material preference - Ceramic vs Metal"""
        # Sample ceramic objects
        ceramic_objects = [obj for obj in self.objects
                          if 'porcelain' in obj['medium'].lower() or 'ceramic' in obj['medium'].lower()]
        ceramic_sample = random.choice([obj for obj in ceramic_objects if obj['is_highlight'] == 'True'] or ceramic_objects)

        # Sample metal objects
        metal_objects = [obj for obj in self.objects
                        if 'bronze' in obj['medium'].lower() or 'copper' in obj['medium'].lower()]
        metal_sample = random.choice([obj for obj in metal_objects if obj['is_highlight'] == 'True'] or metal_objects)

        return {
            'id': 'q4',
            'type': 'image_choice',
            'question': 'Which material texture speaks to you?',
            'instruction': '(Imagine zooming into the surface detail)',
            'options': [
                {
                    'value': 'ceramic',
                    'label': 'Glazed Ceramic',
                    'object_id': ceramic_sample['object_id'],
                    'title': self.clean_text(ceramic_sample['title']),
                    'culture': self.clean_text(ceramic_sample['culture']),
                    'medium': self.clean_text(ceramic_sample['medium']),
                    'gallery': ceramic_sample['gallery_number']
                },
                {
                    'value': 'metal',
                    'label': 'Metal/Bronze',
                    'object_id': metal_sample['object_id'],
                    'title': self.clean_text(metal_sample['title']),
                    'culture': self.clean_text(metal_sample['culture']),
                    'medium': self.clean_text(metal_sample['medium']),
                    'gallery': metal_sample['gallery_number']
                }
            ]
        }

    # ==================== QUESTION 5: MATERIAL SWATCHES 2 ====================
    def question_5_material_2(self):
        """Q5: Material preference - Stone vs Wood"""
        # Sample stone/jade objects
        stone_objects = [obj for obj in self.objects
                        if 'jade' in obj['medium'].lower() or 'stone' in obj['medium'].lower() or 'nephrite' in obj['medium'].lower()]
        stone_sample = random.choice([obj for obj in stone_objects if obj['is_highlight'] == 'True'] or stone_objects)

        # Sample wood/lacquer objects
        wood_objects = [obj for obj in self.objects
                       if 'wood' in obj['medium'].lower() or 'lacquer' in obj['medium'].lower()]
        wood_sample = random.choice([obj for obj in wood_objects if obj['is_highlight'] == 'True'] or wood_objects)

        return {
            'id': 'q5',
            'type': 'image_choice',
            'question': 'And between these textures?',
            'instruction': '(Focus on the material surface)',
            'options': [
                {
                    'value': 'stone',
                    'label': 'Jade/Stone',
                    'object_id': stone_sample['object_id'],
                    'title': self.clean_text(stone_sample['title']),
                    'culture': self.clean_text(stone_sample['culture']),
                    'medium': self.clean_text(stone_sample['medium']),
                    'gallery': stone_sample['gallery_number']
                },
                {
                    'value': 'wood',
                    'label': 'Wood/Lacquer',
                    'object_id': wood_sample['object_id'],
                    'title': self.clean_text(wood_sample['title']),
                    'culture': self.clean_text(wood_sample['culture']),
                    'medium': self.clean_text(wood_sample['medium']),
                    'gallery': wood_sample['gallery_number']
                }
            ]
        }

    # ==================== QUESTION 6: GENAI - MATERIAL COMBO ====================
    def question_6_genai_material_combo(self, material_q4, material_q5):
        """Q6: GenAI question based on material combination"""

        # Define combination templates
        templates = {
            ('ceramic', 'stone'): {
                'question': "You're drawn to smooth, crafted surfaces. Which refined piece speaks to you?",
                'keywords': ['porcelain', 'jade', 'nephrite'],
                'boost': ['polished', 'carved', 'decorated']
            },
            ('ceramic', 'wood'): {
                'question': "You appreciate decorative artistry. Which ornate work captures your eye?",
                'keywords': ['porcelain', 'lacquer'],
                'boost': ['painted', 'decorated', 'inlay']
            },
            ('metal', 'stone'): {
                'question': "Ancient materials call to you. Which historical piece resonates?",
                'keywords': ['bronze', 'jade', 'stone'],
                'boost': ['ancient', 'dynasty', 'ritual']
            },
            ('metal', 'wood'): {
                'question': "You love contrast and fusion. Which mixed-media work intrigues you?",
                'keywords': ['bronze', 'wood', 'gilt'],
                'boost': ['decorated', 'inlay']
            }
        }

        template = templates.get((material_q4, material_q5), templates[('ceramic', 'stone')])

        # Filter objects by keywords
        filtered = []
        for obj in self.objects:
            medium_lower = obj['medium'].lower()
            if any(kw in medium_lower for kw in template['keywords']):
                filtered.append(obj)

        # Prefer highlights
        highlights = [obj for obj in filtered if obj['is_highlight'] == 'True']
        sample_pool = highlights if len(highlights) >= 3 else filtered

        # Sample 3 objects
        samples = random.sample(sample_pool, min(3, len(sample_pool)))

        return {
            'id': 'q6',
            'type': 'image_choice_multi',
            'question': template['question'],
            'instruction': 'Choose the one that draws you in',
            'genai_source': f"Generated from materials: {material_q4} + {material_q5}",
            'options': [
                {
                    'value': obj['object_id'],
                    'object_id': obj['object_id'],
                    'title': self.clean_text(obj['title']),
                    'culture': self.clean_text(obj['culture']),
                    'medium': self.clean_text(obj['medium']),
                    'date': self.clean_text(obj['object_date']),
                    'gallery': obj['gallery_number']
                }
                for obj in samples
            ]
        }

    # ==================== QUESTION 7: GENAI - FREEDOM + DEPTH + MATERIAL ====================
    def question_7_genai_complex(self, freedom_level, depth_preference, material_q4):
        """Q7: GenAI combining freedom, depth, and material"""

        # Get objects matching primary material
        material_keywords = {
            'ceramic': ['porcelain', 'ceramic'],
            'metal': ['bronze', 'copper', 'gilt'],
            'stone': ['jade', 'stone', 'nephrite'],
            'wood': ['wood', 'lacquer']
        }

        keywords = material_keywords.get(material_q4, ['porcelain'])
        filtered = [obj for obj in self.objects
                   if any(kw in obj['medium'].lower() for kw in keywords)]

        # Apply freedom and depth logic
        if depth_preference == 'focused':
            if freedom_level == 'curated':
                question = f"Let's go deep into {material_q4}. Pick 2 masterpieces to study closely."
                sample_pool = [obj for obj in filtered if obj['is_highlight'] == 'True']
            elif freedom_level == 'balanced':
                question = f"Explore {material_q4} evolution. Pick 2 from different styles."
                sample_pool = filtered
            else:  # free
                question = f"Deep dive into {material_q4} surprises. Pick 2 hidden gems."
                sample_pool = [obj for obj in filtered if obj['is_highlight'] == 'False']

        elif depth_preference == 'mixed':
            question = f"A mix of {material_q4} pieces. Pick 2 that intrigue you."
            sample_pool = filtered

        else:  # variety
            question = f"Different {material_q4} styles. Pick 2 that surprise you."
            # Mix different cultures
            cultures = list(set([obj['culture'] for obj in filtered if obj['culture']]))
            sample_pool = []
            for culture in cultures[:4]:
                culture_objs = [obj for obj in filtered if obj['culture'] == culture]
                if culture_objs:
                    sample_pool.append(random.choice(culture_objs))

        # Sample 4 objects
        sample_pool = sample_pool if sample_pool else filtered
        samples = random.sample(sample_pool, min(4, len(sample_pool)))

        return {
            'id': 'q7',
            'type': 'image_choice_multi',
            'question': question,
            'instruction': 'Select 2 artworks',
            'select_count': 2,
            'genai_source': f"Generated from freedom={freedom_level}, depth={depth_preference}, material={material_q4}",
            'options': [
                {
                    'value': obj['object_id'],
                    'object_id': obj['object_id'],
                    'title': self.clean_text(obj['title']),
                    'culture': self.clean_text(obj['culture']),
                    'medium': self.clean_text(obj['medium']),
                    'date': self.clean_text(obj['object_date']),
                    'gallery': obj['gallery_number']
                }
                for obj in samples
            ]
        }

    # ==================== QUESTION 8: GALLERY PREFERENCE ====================
    def question_8_gallery(self):
        """Q8: Gallery preference"""
        # Top galleries from analysis
        galleries = ['207', '222', '219', '247']

        options = []
        for gallery_num in galleries:
            gallery_objects = [obj for obj in self.objects if obj['gallery_number'] == gallery_num]
            highlights = [obj for obj in gallery_objects if obj['is_highlight'] == 'True']
            sample = random.choice(highlights if highlights else gallery_objects) if gallery_objects else None

            if sample:
                options.append({
                    'value': gallery_num,
                    'label': f'Gallery {gallery_num}',
                    'object_id': sample['object_id'],
                    'title': self.clean_text(sample['title']),
                    'culture': self.clean_text(sample['culture']),
                    'count': len(gallery_objects)
                })

        return {
            'id': 'q8',
            'type': 'image_choice',
            'question': 'Which gallery space calls to you?',
            'instruction': 'Choose the one that appeals most',
            'options': options
        }

    # ==================== QUESTION 9: EMOTION WORDS ====================
    def question_9_emotions(self):
        """Q9: Rapid fire emotion words"""

        # Curated word cloud from embeddings
        emotion_words = {
            # Materials (aesthetic qualities)
            'Delicate': ['porcelain', 'flowers', 'painted'],
            'Smooth': ['jade', 'nephrite', 'polished'],
            'Ancient': ['bronze', 'stone', 'dynasty'],
            'Luminous': ['gold', 'gilt', 'silver'],
            'Elegant': ['silver', 'decorated', 'refined'],

            # Subjects (emotional)
            'Peaceful': ['buddha', 'bodhisattva', 'seated'],
            'Powerful': ['dragon', 'deity', 'standing'],
            'Tranquil': ['landscape', 'water', 'garden'],
            'Playful': ['bird', 'animal', 'flowers'],

            # Colors
            'Serene': ['blue', 'white', 'celadon'],
            'Vibrant': ['color', 'polychrome', 'enamels'],
            'Pure': ['white', 'jade', 'porcelain'],

            # Techniques
            'Intricate': ['carved', 'decoration', 'inlay'],
            'Bold': ['bronze', 'large', 'standing'],
            'Subtle': ['glaze', 'underglaze', 'monochrome'],

            # Moods
            'Mysterious': ['ancient', 'ritual', 'deity'],
            'Harmonious': ['landscape', 'garden', 'scholar'],
            'Majestic': ['dragon', 'emperor', 'imperial'],
            'Contemplative': ['buddha', 'scholar', 'meditation'],
            'Striking': ['dragon', 'phoenix', 'bold']
        }

        # Get random 30 words
        all_words = list(emotion_words.keys())
        random.shuffle(all_words)
        selected_words = all_words[:30]

        return {
            'id': 'q9',
            'type': 'multi_select',
            'question': 'Quick! Pick 5 words that excite you',
            'instruction': '(15 seconds - go with your gut!)',
            'timer': 15,
            'max_select': 5,
            'options': [
                {
                    'value': word,
                    'label': word,
                    'keywords': emotion_words[word]
                }
                for word in selected_words
            ]
        }

    # ==================== RUN SURVEY ====================
    def run_example_survey(self):
        """Run an example survey with simulated answers"""
        print("=" * 80)
        print("EXAMPLE SURVEY GENERATION")
        print("=" * 80)
        print()

        # Q1
        q1 = self.question_1_duration()
        print(f"Q1: {q1['question']}")
        for opt in q1['options']:
            print(f"  • {opt['label']} - {opt['stops']}")
        # Simulate answer
        self.answers['q1'] = 120  # 2 hours
        print(f"\n  → USER SELECTS: 2 hours (120 min)\n")

        # Q2
        q2 = self.question_2_freedom()
        print(f"Q2: {q2['question']}")
        for opt in q2['options']:
            print(f"  • {opt['label']}")
            print(f"    {opt['description']}")
        self.answers['q2'] = 'balanced'
        print(f"\n  → USER SELECTS: Balanced\n")

        # Q3
        q3 = self.question_3_depth()
        print(f"Q3: {q3['question']}")
        for opt in q3['options']:
            print(f"  • {opt['label']}")
            print(f"    {opt['description']}")
        self.answers['q3'] = 'focused'
        print(f"\n  → USER SELECTS: Focused (Go Deep)\n")

        # Q4
        q4 = self.question_4_material_1()
        print(f"Q4: {q4['question']}")
        print(f"    {q4['instruction']}")
        for opt in q4['options']:
            print(f"\n  • {opt['label']}:")
            print(f"    Object ID: {opt['object_id']}")
            print(f"    Title: {opt['title']}")
            print(f"    Culture: {opt['culture']}")
            print(f"    Gallery: {opt['gallery']}")
        self.answers['q4'] = q4['options'][0]['value']  # Select first option
        print(f"\n  → USER SELECTS: {q4['options'][0]['label']}\n")

        # Q5
        q5 = self.question_5_material_2()
        print(f"Q5: {q5['question']}")
        print(f"    {q5['instruction']}")
        for opt in q5['options']:
            print(f"\n  • {opt['label']}:")
            print(f"    Object ID: {opt['object_id']}")
            print(f"    Title: {opt['title']}")
            print(f"    Culture: {opt['culture']}")
            print(f"    Gallery: {opt['gallery']}")
        self.answers['q5'] = q5['options'][0]['value']
        print(f"\n  → USER SELECTS: {q5['options'][0]['label']}\n")

        # Q6 - GenAI
        print("=" * 80)
        print("🤖 GENAI QUESTION GENERATION")
        print("=" * 80)
        q6 = self.question_6_genai_material_combo(self.answers['q4'], self.answers['q5'])
        print(f"\nQ6: {q6['question']}")
        print(f"    {q6['instruction']}")
        print(f"    [GenAI: {q6['genai_source']}]")
        for i, opt in enumerate(q6['options'], 1):
            print(f"\n  {i}. {opt['title']}")
            print(f"     Culture: {opt['culture']} | Date: {opt['date']}")
            print(f"     Medium: {opt['medium']}")
            print(f"     Gallery: {opt['gallery']} | Object ID: {opt['object_id']}")
        self.answers['q6'] = q6['options'][0]['object_id']
        print(f"\n  → USER SELECTS: Option 1\n")

        # Q7 - GenAI Complex
        q7 = self.question_7_genai_complex(
            self.answers['q2'],  # freedom
            self.answers['q3'],  # depth
            self.answers['q4']   # material
        )
        print(f"Q7: {q7['question']}")
        print(f"    {q7['instruction']}")
        print(f"    [GenAI: {q7['genai_source']}]")
        for i, opt in enumerate(q7['options'], 1):
            print(f"\n  {i}. {opt['title']}")
            print(f"     Culture: {opt['culture']} | Date: {opt['date']}")
            print(f"     Medium: {opt['medium']}")
            print(f"     Gallery: {opt['gallery']} | Object ID: {opt['object_id']}")
        self.answers['q7'] = [q7['options'][0]['object_id'], q7['options'][1]['object_id']]
        print(f"\n  → USER SELECTS: Options 1 and 2\n")

        # Q8
        q8 = self.question_8_gallery()
        print(f"Q8: {q8['question']}")
        print(f"    {q8['instruction']}")
        for opt in q8['options']:
            print(f"\n  • {opt['label']} ({opt['count']} pieces)")
            print(f"    Featured: {opt['title']}")
            print(f"    Culture: {opt['culture']}")
            print(f"    Object ID: {opt['object_id']}")
        self.answers['q8'] = q8['options'][0]['value']
        print(f"\n  → USER SELECTS: Gallery {q8['options'][0]['value']}\n")

        # Q9
        q9 = self.question_9_emotions()
        print(f"Q9: {q9['question']}")
        print(f"    {q9['instruction']} [Timer: {q9['timer']}s]")
        print(f"\n    Word Cloud ({len(q9['options'])} words):")
        # Display in rows
        words = [opt['label'] for opt in q9['options']]
        for i in range(0, len(words), 5):
            print(f"    {' | '.join(words[i:i+5])}")

        # Simulate selection
        selected = random.sample(q9['options'], 5)
        self.answers['q9'] = [opt['value'] for opt in selected]
        print(f"\n  → USER SELECTS: {', '.join([opt['label'] for opt in selected])}")

        # Map to keywords
        all_keywords = []
        for opt in selected:
            all_keywords.extend(opt['keywords'])
        print(f"\n    Mapped to keywords: {', '.join(set(all_keywords))}\n")

        # Summary
        print("=" * 80)
        print("SURVEY COMPLETE - COLLECTED DATA")
        print("=" * 80)
        print(json.dumps(self.answers, indent=2))
        print()

        return self.answers


if __name__ == '__main__':
    # Initialize survey engine
    engine = SurveyEngine(
        csv_path='../data/asian_art_on_view.csv',
        embeddings_path='../data/text_embeddings.json'
    )

    # Run example survey
    results = engine.run_example_survey()

    # Save results
    with open('../data/example_survey_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("✓ Saved survey results to data/example_survey_results.json")
