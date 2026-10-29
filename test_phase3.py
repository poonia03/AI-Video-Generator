r"""
test_phase3.py - Phase 3 smoke test.
Generates a test MP4 without Flask, using synthetic solid-colour images.
Run: .\venv\Scripts\python test_phase3.py
Expected: outputs/test_video.mp4 created (~15-25 seconds)
"""

import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from services.image_processor import process_images
from services.script_generator import generate_script
from services.video_generator import generate_video

# ── 1. Create 4 synthetic test images ────────────────────────
print("Creating synthetic test images...")
test_img_dir = os.path.join('uploads', '_test_images')
os.makedirs(test_img_dir, exist_ok=True)

COLOURS = [
    (70,  130, 180),   # Steel Blue
    (46,  139,  87),   # Sea Green
    (178,  34,  34),   # Firebrick
    (148,   0, 211),   # Dark Violet
]

raw_paths = []
for i, colour in enumerate(COLOURS):
    path = os.path.join(test_img_dir, f'test_{i+1}.jpg')
    img = Image.new('RGB', (1200, 800), colour)
    img.save(path, 'JPEG', quality=95)
    raw_paths.append(path)
    print(f"  Created: {path}")

# ── 2. Load sample property data ─────────────────────────────
print("\nLoading sample property data...")
with open('sample_data/property.json', 'r', encoding='utf-8') as f:
    property_data = json.load(f)
print(f"  Property: {property_data['property_name']}")

# ── 3. Generate script ────────────────────────────────────────
print("\nGenerating script (template mode expected)...")
script = generate_script(property_data)
print(f"  Script source: {script['source']}")
print(f"  Opening title: {script['opening_title']}")
print(f"  Scene captions ({len(script['scene_captions'])}): {script['scene_captions'][:2]}...")

# ── 4. Process images ─────────────────────────────────────────
print("\nProcessing images...")
processed_dir = os.path.join('uploads', '_test_processed')
processed = process_images(raw_paths, processed_dir)
print(f"  Processed {len(processed)} images.")

# ── 5. Generate video ─────────────────────────────────────────
print("\nGenerating video (this may take 30–90 seconds)...")
output_path = os.path.join('outputs', 'test_video.mp4')
temp_dir    = os.path.join('uploads', '_test_temp')

generate_video(
    processed_images=processed,
    script=script,
    property_data=property_data,
    output_path=output_path,
    temp_dir=temp_dir,
    add_voiceover=False,
)

# ── 6. Verify ─────────────────────────────────────────────────
if os.path.exists(output_path) and os.path.getsize(output_path) > 10_000:
    size_kb = os.path.getsize(output_path) // 1024
    print(f"\n✅ SUCCESS! Video created: {output_path} ({size_kb} KB)")
    print("   Open this file in VLC or any media player to verify.")
else:
    print(f"\n❌ FAILED: Video file not created or is too small.")
    sys.exit(1)
