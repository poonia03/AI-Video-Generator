"""
services/script_generator.py
Generates promotional scripts and captions for the property video.

Priority:
1. Google Gemini API (if GEMINI_API_KEY is set and valid)
2. Template-based fallback (always works, no API needed)
"""

import os
import json
import logging
import re
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()


# ---------------------------------------------------------------------------
# Template-based generation (fallback — always available)
# ---------------------------------------------------------------------------

def _template_script(data: dict) -> dict:
    """
    Builds a structured script from property data using string templates.
    No AI or external API is used here.
    """
    name = data.get('property_name', 'This Property')
    location = data.get('location', 'Prime Location')
    price = data.get('price', 'Contact for Price')
    prop_type = data.get('property_type', 'Property')
    features = data.get('features', [])
    contact = data.get('contact', 'Contact us for more information')

    # Build feature bullets (max 6 for clean visuals)
    feature_lines = features[:6] if features else ['Modern Design', 'Prime Location', 'Ready to Move']

    # Scene captions — one per image scene (up to 6)
    scene_captions = []
    for i, feat in enumerate(feature_lines):
        scene_captions.append(feat.strip())
    # Pad to at least 4 captions if fewer features
    while len(scene_captions) < 4:
        scene_captions.append(f'Discover {name}')

    opening_title = name
    opening_subtitle = f'{prop_type}  ·  {location}'

    intro = (
        f"Welcome to {name}, an exceptional {prop_type} located in {location}. "
        f"Offering a lifestyle of comfort and elegance, this property is available at {price}."
    )

    highlights_caption = f'{price}  |  {location}'

    closing_cta = contact

    narration_lines = [
        intro,
        f"Step inside and experience {', '.join(feature_lines[:3])}.",
        f"Priced at {price}, {name} is the perfect choice for discerning buyers.",
        f"Don't miss this opportunity. {contact}",
    ]

    return {
        'source': 'template',
        'opening_title': opening_title,
        'opening_subtitle': opening_subtitle,
        'intro': intro,
        'scene_captions': scene_captions,
        'highlights_caption': highlights_caption,
        'closing_cta': closing_cta,
        'narration': ' '.join(narration_lines),
        'narration_lines': narration_lines,
    }


# ---------------------------------------------------------------------------
# Gemini AI generation
# ---------------------------------------------------------------------------

GEMINI_PROMPT_TEMPLATE = """
You are a professional real estate copywriter. Generate a promotional video script for the following property.

Property Details:
- Name: {property_name}
- Type: {property_type}
- Location: {location}
- Price: {price}
- Features: {features}
- Contact / CTA: {contact}

IMPORTANT RULES:
1. Use ONLY the facts provided above. Do NOT invent any features, amenities, dimensions, or claims not listed.
2. Keep language professional, positive, and concise.
3. Return ONLY valid JSON — no markdown, no explanation.

Return this exact JSON structure:
{{
  "opening_title": "Property name as headline",
  "opening_subtitle": "Type · Location",
  "intro": "2-3 sentence introduction",
  "scene_captions": ["caption1", "caption2", "caption3", "caption4", "caption5", "caption6"],
  "highlights_caption": "Price | Location one-liner",
  "closing_cta": "Call to action text",
  "narration": "Full narration script for voice-over (3-5 sentences)",
  "narration_lines": ["line1", "line2", "line3", "line4"]
}}
"""


def _validate_ai_output(ai_data: dict, property_data: dict) -> dict:
    """
    Validates AI output:
    - Ensures all required keys exist
    - Checks scene_captions is a non-empty list
    - Strips any text longer than reasonable limits (prevents prompt injection)
    Returns the validated dict or raises ValueError.
    """
    required_keys = [
        'opening_title', 'opening_subtitle', 'intro',
        'scene_captions', 'highlights_caption', 'closing_cta',
        'narration', 'narration_lines'
    ]
    for key in required_keys:
        if key not in ai_data:
            raise ValueError(f"AI response missing required key: '{key}'")

    if not isinstance(ai_data['scene_captions'], list) or len(ai_data['scene_captions']) < 2:
        raise ValueError("AI scene_captions must be a list with at least 2 items")

    if not isinstance(ai_data['narration_lines'], list):
        raise ValueError("AI narration_lines must be a list")

    # Truncate overly long fields to prevent layout issues
    ai_data['opening_title'] = str(ai_data['opening_title'])[:80]
    ai_data['opening_subtitle'] = str(ai_data['opening_subtitle'])[:100]
    ai_data['highlights_caption'] = str(ai_data['highlights_caption'])[:120]
    ai_data['closing_cta'] = str(ai_data['closing_cta'])[:150]
    ai_data['scene_captions'] = [str(c)[:100] for c in ai_data['scene_captions'][:8]]

    ai_data['source'] = 'gemini'
    return ai_data


def _gemini_script(data: dict) -> dict:
    """
    Calls the Gemini API to generate the script.
    Returns validated dict or raises an exception.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai package not installed")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = GEMINI_PROMPT_TEMPLATE.format(
        property_name=data.get('property_name', ''),
        property_type=data.get('property_type', ''),
        location=data.get('location', ''),
        price=data.get('price', ''),
        features=', '.join(data.get('features', [])),
        contact=data.get('contact', ''),
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=1024,
        ),
        request_options={"timeout": 30},
    )

    raw_text = response.text.strip()

    # Strip markdown code fences if present
    raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
    raw_text = re.sub(r'\s*```$', '', raw_text)

    ai_data = json.loads(raw_text)
    return _validate_ai_output(ai_data, data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_script(property_data: dict) -> dict:
    """
    Main entry point. Tries Gemini API first, falls back to template.

    Args:
        property_data: dict with keys: property_name, location, price,
                       property_type, features (list), contact

    Returns:
        dict with keys: source, opening_title, opening_subtitle, intro,
                        scene_captions, highlights_caption, closing_cta,
                        narration, narration_lines
    """
    if GEMINI_API_KEY and GEMINI_API_KEY != 'your_gemini_api_key_here':
        try:
            logger.info("Attempting Gemini API script generation...")
            result = _gemini_script(property_data)
            logger.info("Gemini script generated successfully.")
            return result
        except Exception as e:
            logger.warning(f"Gemini API failed ({e}), using template fallback.")

    logger.info("Using template-based script generation.")
    return _template_script(property_data)
