"""
services/video_generator.py

Builds the promotional property video using MoviePy.
Pipeline:
  1. Opening title card
  2. Property image scenes with captions
  3. Highlights scene
  4. Closing CTA scene
  5. Optional: voice-over narration (pyttsx3)
  6. Optional: background music
  7. Export MP4 (H.264 / AAC)
"""

import os
import logging
import textwrap
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Attempt MoviePy import — give clear error if missing
try:
    from moviepy.editor import (
        ImageClip, TextClip, CompositeVideoClip,
        concatenate_videoclips, AudioFileClip, CompositeAudioClip,
        ColorClip
    )
    from moviepy.video.fx.fadein import fadein
    from moviepy.video.fx.fadeout import fadeout
    MOVIEPY_OK = True
except Exception as e:
    MOVIEPY_OK = False
    MOVIEPY_ERROR = str(e)

# Video settings
WIDTH, HEIGHT = 1280, 720
FPS = 24
SCENE_DURATION = 4.5      # seconds per image scene
TITLE_DURATION = 3.5      # opening title duration
CLOSING_DURATION = 4.0    # closing CTA duration
TRANSITION = 0.5          # crossfade duration

# Colour palette
COLOR_DARK = (15, 20, 35)         # near-black navy
COLOR_GOLD = (212, 175, 55)       # premium gold
COLOR_WHITE = (255, 255, 255)
COLOR_LIGHT = (220, 225, 235)

# Font paths (fallback order)
FONT_SEARCH_PATHS = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _find_font(size: int = 36) -> ImageFont.FreeTypeFont:
    """Returns the first available system font at the given size."""
    for path in FONT_SEARCH_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _find_font_bold(size: int = 36) -> ImageFont.FreeTypeFont:
    bold_paths = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in bold_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return _find_font(size)


def _wrap_text(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> list:
    """
    Wraps text so it fits within max_width pixels.
    Returns list of lines.
    """
    dummy = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy)

    words = text.split()
    lines = []
    current = ''

    for word in words:
        test = (current + ' ' + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _pil_to_moviepy(pil_img: Image.Image) -> np.ndarray:
    """Converts a PIL Image to a numpy array for MoviePy."""
    return np.array(pil_img.convert('RGB'))


# ---------------------------------------------------------------------------
# Scene builders — return PIL Image frames
# ---------------------------------------------------------------------------

def _make_title_frame(title: str, subtitle: str) -> Image.Image:
    """Creates the opening title card frame."""
    img = Image.new('RGB', (WIDTH, HEIGHT), COLOR_DARK)
    draw = ImageDraw.Draw(img)

    # Subtle grid overlay for depth
    for x in range(0, WIDTH, 60):
        draw.line([(x, 0), (x, HEIGHT)], fill=(255, 255, 255, 8), width=1)
    for y in range(0, HEIGHT, 60):
        draw.line([(0, y), (WIDTH, y)], fill=(255, 255, 255, 8), width=1)

    # Gold accent bar
    draw.rectangle([(80, HEIGHT // 2 - 5), (WIDTH - 80, HEIGHT // 2 - 2)],
                   fill=COLOR_GOLD)

    # Title
    font_title = _find_font_bold(64)
    title_lines = _wrap_text(title, WIDTH - 160, font_title)
    y = HEIGHT // 2 - 80
    for line in title_lines[:2]:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        # Shadow
        draw.text((x + 2, y + 2), line, font=font_title, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font_title, fill=COLOR_WHITE)
        y += bbox[3] - bbox[1] + 10

    # Gold divider
    draw.rectangle([(WIDTH // 2 - 60, y + 8), (WIDTH // 2 + 60, y + 11)],
                   fill=COLOR_GOLD)
    y += 28

    # Subtitle
    font_sub = _find_font(30)
    sub_lines = _wrap_text(subtitle, WIDTH - 200, font_sub)
    for line in sub_lines[:2]:
        bbox = draw.textbbox((0, 0), line, font=font_sub)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font_sub, fill=COLOR_GOLD)
        y += bbox[3] - bbox[1] + 6

    # Watermark
    font_wm = _find_font(18)
    draw.text((WIDTH - 200, HEIGHT - 35), 'AI Property Video Generator',
              font=font_wm, fill=(180, 180, 180))

    return img


def _make_image_frame(bg_path: str, caption: str, scene_num: int, total: int) -> Image.Image:
    """
    Overlays a caption onto a processed property image.
    bg_path: path to the pre-processed 1280x720 image
    """
    img = Image.open(bg_path).convert('RGB').resize((WIDTH, HEIGHT), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    # Bottom gradient overlay (ensure text legibility)
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for y in range(HEIGHT):
        alpha = int(200 * max(0, (y - HEIGHT * 0.45) / (HEIGHT * 0.55)))
        ov_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Caption text
    font_cap = _find_font_bold(38)
    cap_lines = _wrap_text(caption, WIDTH - 120, font_cap)
    text_y = HEIGHT - 130
    for line in cap_lines[:2]:
        bbox = draw.textbbox((0, 0), line, font=font_cap)
        tw = bbox[2] - bbox[0]
        x = (WIDTH - tw) // 2
        # Shadow
        draw.text((x + 2, text_y + 2), line, font=font_cap, fill=(0, 0, 0))
        draw.text((x, text_y), line, font=font_cap, fill=COLOR_WHITE)
        text_y += bbox[3] - bbox[1] + 6

    # Scene indicator dots
    dot_r = 5
    dot_spacing = 20
    total_dots_w = total * dot_spacing
    dot_x = (WIDTH - total_dots_w) // 2
    dot_y = HEIGHT - 30
    for i in range(total):
        color = COLOR_GOLD if i == scene_num else (150, 150, 150)
        draw.ellipse([(dot_x + i * dot_spacing - dot_r, dot_y - dot_r),
                      (dot_x + i * dot_spacing + dot_r, dot_y + dot_r)],
                     fill=color)

    # Top-right gold accent line
    draw.rectangle([(WIDTH - 180, 20), (WIDTH - 20, 23)], fill=COLOR_GOLD)

    return img


def _make_highlights_frame(highlights_caption: str, features: list) -> Image.Image:
    """Creates the property highlights summary scene."""
    img = Image.new('RGB', (WIDTH, HEIGHT), COLOR_DARK)
    draw = ImageDraw.Draw(img)

    # Left gold accent bar
    draw.rectangle([(60, 60), (65, HEIGHT - 60)], fill=COLOR_GOLD)

    # Section title
    font_title = _find_font_bold(44)
    draw.text((90, 65), 'Property Highlights', font=font_title, fill=COLOR_GOLD)

    # Divider
    draw.rectangle([(90, 120), (700, 123)], fill=(100, 100, 130))

    # Feature bullets
    font_feat = _find_font(30)
    y = 145
    for feat in features[:6]:
        # Bullet
        draw.ellipse([(90, y + 10), (100, y + 20)], fill=COLOR_GOLD)
        draw.text((115, y), feat.strip(), font=font_feat, fill=COLOR_LIGHT)
        y += 48

    # Highlights caption (price/location)
    font_hl = _find_font_bold(32)
    hl_lines = _wrap_text(highlights_caption, WIDTH - 160, font_hl)
    hy = HEIGHT - 100
    for line in hl_lines[:2]:
        bbox = draw.textbbox((0, 0), line, font=font_hl)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, hy), line, font=font_hl, fill=COLOR_GOLD)
        hy += bbox[3] - bbox[1] + 8

    return img


def _make_closing_frame(cta: str, prop_name: str) -> Image.Image:
    """Creates the closing call-to-action scene."""
    img = Image.new('RGB', (WIDTH, HEIGHT), COLOR_DARK)
    draw = ImageDraw.Draw(img)

    # Decorative corners
    corner = 40
    for pts in [
        [(30, 30), (30 + corner, 30), (30, 30 + corner)],
        [(WIDTH - 30, 30), (WIDTH - 30 - corner, 30), (WIDTH - 30, 30 + corner)],
        [(30, HEIGHT - 30), (30 + corner, HEIGHT - 30), (30, HEIGHT - 30 - corner)],
        [(WIDTH - 30, HEIGHT - 30), (WIDTH - 30 - corner, HEIGHT - 30), (WIDTH - 30, HEIGHT - 30 - corner)],
    ]:
        draw.polygon(pts, fill=COLOR_GOLD)

    # "Thank you" heading
    font_ty = _find_font_bold(36)
    draw.text((0, 0), '', font=font_ty, fill=COLOR_WHITE)  # dummy init

    ty_text = 'Thank You for Watching'
    bbox = draw.textbbox((0, 0), ty_text, font=font_ty)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, 160),
              ty_text, font=font_ty, fill=COLOR_LIGHT)

    # Property name
    font_name = _find_font_bold(56)
    name_lines = _wrap_text(prop_name, WIDTH - 160, font_name)
    ny = HEIGHT // 2 - 60
    for line in name_lines[:2]:
        bbox = draw.textbbox((0, 0), line, font=font_name)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, ny),
                  line, font=font_name, fill=COLOR_WHITE)
        ny += bbox[3] - bbox[1] + 8

    # Gold divider
    draw.rectangle([(WIDTH // 2 - 100, ny + 10), (WIDTH // 2 + 100, ny + 13)],
                   fill=COLOR_GOLD)
    ny += 30

    # CTA text
    font_cta = _find_font(28)
    cta_lines = _wrap_text(cta, WIDTH - 160, font_cta)
    for line in cta_lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font_cta)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, ny),
                  line, font=font_cta, fill=COLOR_GOLD)
        ny += bbox[3] - bbox[1] + 8

    return img


# ---------------------------------------------------------------------------
# Voice-over generation (optional)
# ---------------------------------------------------------------------------

def generate_voiceover(narration: str, output_path: str) -> bool:
    """
    Generates a voice-over WAV file using pyttsx3 (offline TTS).
    Returns True if successful, False otherwise.
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 155)    # words per minute
        engine.setProperty('volume', 0.95)

        voices = engine.getProperty('voices')
        # Prefer female voice if available
        for v in voices:
            if 'female' in v.name.lower() or 'zira' in v.name.lower():
                engine.setProperty('voice', v.id)
                break

        engine.save_to_file(narration, output_path)
        engine.runAndWait()
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.warning(f"Voice-over generation failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main video builder
# ---------------------------------------------------------------------------

def generate_video(
    processed_images: list,
    script: dict,
    property_data: dict,
    output_path: str,
    temp_dir: str,
    add_voiceover: bool = False,
    background_music_path: str = None,
) -> str:
    """
    Generates the promotional video MP4.

    Args:
        processed_images: list of paths to 1280x720 processed images
        script: dict from script_generator.generate_script()
        property_data: original property dict (for features, name)
        output_path: full path for the output .mp4 file
        temp_dir: directory for temporary files
        add_voiceover: if True, generates TTS narration
        background_music_path: optional path to background music file

    Returns:
        output_path on success.
    Raises:
        RuntimeError on failure.
    """
    if not MOVIEPY_OK:
        raise RuntimeError(
            f"MoviePy could not be imported: {MOVIEPY_ERROR}. "
            "Run: pip install moviepy==1.0.3"
        )

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    clips = []

    # --- Scene 1: Opening title ---
    title_frame = _make_title_frame(
        script['opening_title'],
        script['opening_subtitle']
    )
    title_arr = _pil_to_moviepy(title_frame)
    title_clip = ImageClip(title_arr).set_duration(TITLE_DURATION).set_fps(FPS)
    title_clip = title_clip.fx(fadein, TRANSITION).fx(fadeout, TRANSITION)
    clips.append(title_clip)

    # --- Scenes 2..N: Property images ---
    scene_captions = script.get('scene_captions', [])
    n_images = len(processed_images)

    for i, img_path in enumerate(processed_images):
        caption = scene_captions[i] if i < len(scene_captions) else ''
        scene_frame = _make_image_frame(img_path, caption, i, n_images)
        scene_arr = _pil_to_moviepy(scene_frame)
        scene_clip = ImageClip(scene_arr).set_duration(SCENE_DURATION).set_fps(FPS)
        scene_clip = scene_clip.fx(fadein, TRANSITION).fx(fadeout, TRANSITION)
        clips.append(scene_clip)

    # --- Highlights scene ---
    features = property_data.get('features', [])
    hl_frame = _make_highlights_frame(script['highlights_caption'], features)
    hl_arr = _pil_to_moviepy(hl_frame)
    hl_clip = ImageClip(hl_arr).set_duration(SCENE_DURATION).set_fps(FPS)
    hl_clip = hl_clip.fx(fadein, TRANSITION).fx(fadeout, TRANSITION)
    clips.append(hl_clip)

    # --- Closing CTA scene ---
    closing_frame = _make_closing_frame(
        script['closing_cta'],
        script['opening_title']
    )
    closing_arr = _pil_to_moviepy(closing_frame)
    closing_clip = ImageClip(closing_arr).set_duration(CLOSING_DURATION).set_fps(FPS)
    closing_clip = closing_clip.fx(fadein, TRANSITION).fx(fadeout, TRANSITION)
    clips.append(closing_clip)

    # --- Concatenate all scenes ---
    logger.info(f"Concatenating {len(clips)} scenes...")
    final = concatenate_videoclips(clips, method='compose')

    # --- Optional voice-over ---
    audio_clips = []

    if add_voiceover:
        vo_path = os.path.join(temp_dir, 'voiceover.wav')
        narration = script.get('narration', '')
        if narration and generate_voiceover(narration, vo_path):
            try:
                vo_audio = AudioFileClip(vo_path)
                # Trim or pad narration to video length
                if vo_audio.duration > final.duration:
                    vo_audio = vo_audio.subclip(0, final.duration)
                audio_clips.append(vo_audio)
                logger.info("Voice-over added successfully.")
            except Exception as e:
                logger.warning(f"Could not attach voice-over audio: {e}")

    if background_music_path and os.path.exists(background_music_path):
        try:
            music = AudioFileClip(background_music_path)
            music = music.volumex(0.15)  # background music at 15% volume
            if music.duration < final.duration:
                # Loop music if shorter than video
                loops = int(final.duration / music.duration) + 1
                from moviepy.audio.fx.audio_loop import audio_loop
                music = music.fx(audio_loop, nloops=loops)
            music = music.subclip(0, final.duration)
            audio_clips.append(music)
            logger.info("Background music added.")
        except Exception as e:
            logger.warning(f"Could not attach background music: {e}")

    if audio_clips:
        if len(audio_clips) == 1:
            final = final.set_audio(audio_clips[0])
        else:
            combined_audio = CompositeAudioClip(audio_clips)
            final = final.set_audio(combined_audio)

    # --- Export ---
    logger.info(f"Exporting video to: {output_path}")
    final.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac' if audio_clips else None,
        preset='medium',
        ffmpeg_params=['-crf', '23'],
        logger=None,  # suppress moviepy's verbose output
        temp_audiofile=os.path.join(temp_dir, 'temp_audio.m4a'),
    )

    # Cleanup temp audio
    for f in ['voiceover.wav', 'temp_audio.m4a']:
        fp = os.path.join(temp_dir, f)
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass

    logger.info(f"Video saved: {output_path}")
    return output_path
