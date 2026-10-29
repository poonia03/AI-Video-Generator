"""
services/image_processor.py
Handles image validation, resizing, and enhancement for video scenes.
"""

import os
import logging
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np

logger = logging.getLogger(__name__)

# Target video resolution
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720
TARGET_SIZE = (TARGET_WIDTH, TARGET_HEIGHT)
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


def validate_image(file_path: str) -> dict:
    """
    Validates that a file is a usable image.
    Returns {'valid': True/False, 'error': 'reason if invalid'}
    """
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'File does not exist'}

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {'valid': False, 'error': f'Unsupported format: {ext}. Use JPG, PNG, WEBP, or BMP.'}

    if os.path.getsize(file_path) == 0:
        return {'valid': False, 'error': 'File is empty'}

    try:
        with Image.open(file_path) as img:
            img.verify()  # Check for corruption
        # Re-open after verify (verify closes the file)
        with Image.open(file_path) as img:
            w, h = img.size
            if w < 100 or h < 100:
                return {'valid': False, 'error': f'Image too small ({w}x{h}). Minimum 100x100.'}
    except Exception as e:
        return {'valid': False, 'error': f'Cannot open image: {str(e)}'}

    return {'valid': True, 'error': None}


def resize_and_crop(img: Image.Image, target_size: tuple = TARGET_SIZE) -> Image.Image:
    """
    Resizes image to fill target_size without distortion.
    Uses smart crop (center) to avoid letterboxing black bars.
    """
    tw, th = target_size
    img = img.convert('RGB')
    iw, ih = img.size

    # Scale so the image fills the target fully (cover mode)
    scale = max(tw / iw, th / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    img = img.crop((left, top, left + tw, top + th))
    return img


def apply_cinematic_grade(img: Image.Image, strength: float = 0.3) -> Image.Image:
    """
    Applies a subtle cinematic colour grade:
    - Slight brightness boost
    - Slight contrast boost
    - Slight saturation boost
    """
    img = ImageEnhance.Brightness(img).enhance(1.0 + strength * 0.15)
    img = ImageEnhance.Contrast(img).enhance(1.0 + strength * 0.25)
    img = ImageEnhance.Color(img).enhance(1.0 + strength * 0.2)
    return img


def apply_dark_overlay(img: Image.Image, opacity: float = 0.45) -> Image.Image:
    """
    Applies a semi-transparent dark gradient overlay at the bottom
    so that white text is always readable over any background.
    """
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img.size
    gradient_height = int(h * 0.55)  # gradient covers bottom 55%

    for y in range(gradient_height):
        # Linear fade from transparent (top) to dark (bottom)
        alpha = int(255 * opacity * (y / gradient_height))
        draw.line([(0, h - gradient_height + y), (w, h - gradient_height + y)],
                  fill=(0, 0, 0, alpha))

    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    return img.convert('RGB')


def process_images(image_paths: list, output_dir: str) -> list:
    """
    Processes a list of raw image paths:
    1. Validates each image
    2. Resizes to 1280x720 with smart crop
    3. Applies cinematic grade + dark overlay
    4. Saves processed image to output_dir

    Returns list of processed image file paths in order.
    Raises ValueError if any image fails validation.
    """
    os.makedirs(output_dir, exist_ok=True)
    processed = []

    for i, path in enumerate(image_paths):
        result = validate_image(path)
        if not result['valid']:
            raise ValueError(f"Image {i+1} ({os.path.basename(path)}): {result['error']}")

        try:
            with Image.open(path) as img:
                img = resize_and_crop(img)
                img = apply_cinematic_grade(img)
                img = apply_dark_overlay(img)

                out_path = os.path.join(output_dir, f'scene_{i+1:02d}.jpg')
                img.save(out_path, 'JPEG', quality=95)
                processed.append(out_path)
                logger.info(f"Processed image {i+1}: {out_path}")

        except Exception as e:
            raise ValueError(f"Failed to process image {i+1}: {str(e)}")

    return processed


def create_solid_frame(color: tuple, size: tuple = TARGET_SIZE) -> Image.Image:
    """Creates a solid colour frame — used for title/end cards."""
    return Image.new('RGB', size, color)
