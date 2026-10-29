# AI Property Video Generator 🏠🎬

A Flask web application that automatically converts property details and uploaded images into a short, professional, share-ready promotional MP4 video.

## Features

- 📝 **AI-generated scripts** via Google Gemini API (with automatic template fallback)
- 🖼️ **4–8 property images** processed and assembled into video scenes
- 🎨 **Professional text overlays** — opening title, scene captions, highlights, closing CTA
- 🎬 **Smooth fade transitions** between scenes
- 🔊 **Optional offline voice-over** narration (pyttsx3 / no API key needed)
- 📥 **In-browser preview** and one-click MP4 download
- ✅ **Works without any API key** (template-based fallback always available)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3 (Glassmorphism), Vanilla JavaScript |
| Backend | Python 3.x, Flask 3.0 |
| Video | MoviePy 1.0.3 + FFmpeg (via imageio-ffmpeg) |
| Images | Pillow |
| AI Script | Google Gemini 1.5 Flash (optional) |
| TTS | pyttsx3 (optional, offline) |

## Project Structure

```
ai-property-video-generator/
├── app.py                        # Flask app & routes
├── requirements.txt
├── .env.example                  # Copy to .env and configure
├── .gitignore
├── README.md
├── test_phase3.py                # Phase 3 smoke test
├── templates/
│   └── index.html                # Single-page UI
├── static/
│   ├── css/style.css
│   └── js/script.js
├── services/
│   ├── __init__.py
│   ├── script_generator.py       # AI + template script generation
│   ├── image_processor.py        # Resize, crop, grade images
│   └── video_generator.py        # Build and export MP4
├── uploads/                      # Temporary upload storage
├── outputs/                      # Generated MP4 videos
└── sample_data/
    └── property.json             # Sample property for testing
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9+ (tested on Python 3.15)
- Internet connection for initial package installation
- FFmpeg is **bundled automatically** via `imageio-ffmpeg` — no manual install needed

### 2. Clone / Download

```bash
cd "AI  video genertor"
```

### 3. Create and activate virtual environment

```powershell
# Windows PowerShell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure environment

```powershell
copy .env.example .env
```

Edit `.env` — the app works without any API key (template mode).  
To enable AI script generation, add your Gemini API key (free tier available at https://aistudio.google.com):

```
GEMINI_API_KEY=your_key_here
```

### 6. Run the application

```powershell
.\venv\Scripts\python.exe app.py
```

Open your browser at: **http://localhost:5000**

## Usage

1. Fill in property details (name, type, location, price, features, contact)
2. Upload 4–8 property images (JPG/PNG/WEBP)
3. Optionally enable Voice-Over narration
4. Click **Generate Video**
5. Preview and download your MP4

## Testing (Phase 3 Smoke Test)

```powershell
.\venv\Scripts\python.exe test_phase3.py
```

Expected output: `outputs/test_video.mp4` (~1–3 MB), ~25 seconds long.

## AI Integration

### Google Gemini API
- Model: `gemini-1.5-flash`
- Free tier: https://aistudio.google.com
- Set `GEMINI_API_KEY` in `.env`
- The app validates all AI output before use and falls back to templates on failure

### Fallback
- Purely template-based — works with zero API keys
- No invented facts: all content comes directly from user input

## Video Specifications

| Setting | Value |
|---------|-------|
| Resolution | 1280 × 720 (HD) |
| Frame Rate | 24 FPS |
| Codec | H.264 |
| Audio | AAC (when audio enabled) |
| Duration | ~20–40 seconds |
| Format | MP4 |

## Error Handling

The application handles:
- Missing required fields
- < 4 or > 8 images uploaded
- Unsupported image formats
- Corrupted images
- AI API failures → automatic template fallback
- FFmpeg/MoviePy errors
- Server-side errors (no stack traces exposed to users)

## Dependencies

See [requirements.txt](requirements.txt) for the full list.

Key packages:
- `flask` — web framework
- `moviepy` — video assembly
- `imageio-ffmpeg` — bundled FFmpeg binary
- `pillow` — image processing
- `google-generativeai` — Gemini AI (optional)
- `python-dotenv` — environment variable management
- `pyttsx3` — offline text-to-speech (optional)

## Known Limitations

- Voice-over quality depends on the system's installed TTS voices
- First video generation may be slow (30–90 seconds) on lower-end hardware
- Gemini API requires an internet connection and a (free) API key

## Future Improvements

- Background music library
- Multiple video themes/templates
- Progress websocket for real-time updates
- Batch processing for multiple properties
- Cloud storage integration
- Custom font upload
