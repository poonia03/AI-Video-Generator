"""
app.py — Flask application entry point.

Routes:
  GET  /            → Serve the form UI
  POST /generate    → Accept form + images, generate video
  GET  /download/<filename>  → Download generated MP4
  GET  /preview/<filename>   → Stream video for inline preview
  GET  /health      → Health check endpoint
"""

import os
import uuid
import json
import logging
import shutil
import re
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template,
    send_file, send_from_directory, abort
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Import services
from services.script_generator import generate_script
from services.image_processor import process_images
from services.video_generator import generate_video

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE_MB', 50)) * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MIN_IMAGES = 4
MAX_IMAGES = 8

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def is_allowed_image(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def safe_filename(filename: str) -> str:
    """Secures and sanitizes an uploaded filename."""
    filename = secure_filename(filename)
    # Replace spaces and special chars
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    return filename or 'upload'


def cleanup_session(session_dir: str):
    """Removes a session temp directory."""
    try:
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            logger.info(f"Cleaned up session: {session_dir}")
    except Exception as e:
        logger.warning(f"Cleanup failed for {session_dir}: {e}")


def parse_features(raw: str) -> list:
    """
    Parses the features textarea into a clean list.
    Accepts newline or comma-separated values.
    """
    if not raw:
        return []
    # Split on newlines or commas
    parts = re.split(r'[\n,]', raw)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/generate', methods=['POST'])
def generate():
    """
    Main video generation endpoint.
    Accepts multipart/form-data with property fields + image files.
    Returns JSON with video filename or error details.
    """
    errors = []

    # --- 1. Validate required text fields ---
    required_fields = {
        'property_name': 'Property Name',
        'location': 'Location',
        'price': 'Price',
        'property_type': 'Property Type',
        'contact': 'Contact / CTA',
    }
    property_data = {}
    for field, label in required_fields.items():
        value = request.form.get(field, '').strip()
        if not value:
            errors.append(f'{label} is required.')
        else:
            property_data[field] = value

    # Features (optional but recommended)
    features_raw = request.form.get('features', '')
    property_data['features'] = parse_features(features_raw)

    # Optional settings
    add_voiceover = request.form.get('add_voiceover') == 'true'

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    # --- 2. Validate uploaded images ---
    files = request.files.getlist('images')
    if not files or (len(files) == 1 and files[0].filename == ''):
        return jsonify({'success': False, 'errors': ['Please upload at least 4 images.']}), 400

    if len(files) < MIN_IMAGES:
        return jsonify({
            'success': False,
            'errors': [f'Minimum {MIN_IMAGES} images required. You uploaded {len(files)}.']
        }), 400

    if len(files) > MAX_IMAGES:
        return jsonify({
            'success': False,
            'errors': [f'Maximum {MAX_IMAGES} images allowed. You uploaded {len(files)}.']
        }), 400

    # Check each file's extension and basic validity
    for i, f in enumerate(files):
        if not f.filename:
            errors.append(f'Image {i+1}: No filename.')
            continue
        if not is_allowed_image(f.filename):
            ext = os.path.splitext(f.filename)[1]
            errors.append(f'Image {i+1} ({f.filename}): Unsupported format "{ext}". Use JPG, PNG, WEBP, or BMP.')

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    # --- 3. Save uploaded images to a session directory ---
    session_id = str(uuid.uuid4())[:12]
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)

    saved_paths = []
    try:
        for i, f in enumerate(files):
            ext = os.path.splitext(f.filename)[1].lower()
            fname = f'upload_{i+1:02d}{ext}'
            save_path = os.path.join(session_dir, fname)
            f.save(save_path)
            saved_paths.append(save_path)
    except Exception as e:
        cleanup_session(session_dir)
        logger.error(f"File save error: {e}")
        return jsonify({'success': False, 'errors': ['Failed to save uploaded files.']}), 500

    # --- 4. Generate script ---
    try:
        script = generate_script(property_data)
        logger.info(f"Script generated via: {script.get('source', 'unknown')}")
    except Exception as e:
        cleanup_session(session_dir)
        logger.error(f"Script generation error: {e}")
        return jsonify({'success': False, 'errors': ['Failed to generate script. Please try again.']}), 500

    # --- 5. Process images ---
    processed_dir = os.path.join(session_dir, 'processed')
    try:
        processed_images = process_images(saved_paths, processed_dir)
    except ValueError as e:
        cleanup_session(session_dir)
        return jsonify({'success': False, 'errors': [str(e)]}), 400
    except Exception as e:
        cleanup_session(session_dir)
        logger.error(f"Image processing error: {e}")
        return jsonify({'success': False, 'errors': ['Image processing failed.']}), 500

    # --- 6. Generate video ---
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_filename = f'property_video_{session_id}_{timestamp}.mp4'
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    temp_dir = os.path.join(session_dir, 'temp')

    try:
        generate_video(
            processed_images=processed_images,
            script=script,
            property_data=property_data,
            output_path=output_path,
            temp_dir=temp_dir,
            add_voiceover=add_voiceover,
        )
    except RuntimeError as e:
        cleanup_session(session_dir)
        logger.error(f"Video generation runtime error: {e}")
        return jsonify({'success': False, 'errors': [str(e)]}), 500
    except Exception as e:
        cleanup_session(session_dir)
        logger.error(f"Unexpected video error: {e}", exc_info=True)
        return jsonify({'success': False, 'errors': ['Video generation failed. Please try again.']}), 500

    # --- 7. Cleanup session uploads (keep output video) ---
    cleanup_session(session_dir)

    return jsonify({
        'success': True,
        'video_filename': output_filename,
        'script_source': script.get('source', 'template'),
        'scene_count': len(processed_images) + 3,  # images + title + highlights + closing
        'message': 'Video generated successfully!'
    })


@app.route('/preview/<filename>')
def preview_video(filename):
    """Streams the MP4 for inline browser preview."""
    safe = secure_filename(filename)
    if not safe.endswith('.mp4'):
        abort(404)
    return send_from_directory(OUTPUT_FOLDER, safe, mimetype='video/mp4')


@app.route('/download/<filename>')
def download_video(filename):
    """Sends the MP4 as a file download."""
    safe = secure_filename(filename)
    if not safe.endswith('.mp4'):
        abort(404)
    filepath = os.path.join(OUTPUT_FOLDER, safe)
    if not os.path.exists(filepath):
        abort(404)
    return send_file(
        filepath,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=safe
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'success': False,
        'errors': [f'Upload too large. Maximum total size is {MAX_UPLOAD_SIZE // (1024*1024)} MB.']
    }), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'errors': ['Resource not found.']}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Unhandled 500: {e}")
    return jsonify({'success': False, 'errors': ['Internal server error.']}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
