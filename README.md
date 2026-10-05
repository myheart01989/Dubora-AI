# YouTube Video Language Converter

A complete, production-ready web application for translating video dialogue into 21+ languages while **strictly preserving the original background music, sound effects, timing, and video visual stream**.

---

## 🎯 Main Objective & Audio Architecture

Traditional dubbing tools crudely discard the entire audio track, stripping away the soundtrack, ambience, and Foley effects. **YouTube Video Language Converter** uses an intelligent multi-stage pipeline:

```
Original Video
      ↓
Extract 16-bit PCM Audio
      ↓
Speech / Voice Separation (Demucs / Center-Phase Spectral Filter)
      ├── Speech Track (isolated dialogue)
      └── Background Audio (Score, instruments, Foley, and room ambience)
      ↓
Speech Transcription (Whisper / Faster-Whisper / Gemini AI with timestamps)
      ↓
Dialogue Translation (Maintains idiomatic cadence and timestamps)
      ↓
Target Language TTS (Female, Male, Neutral, styles, speed & pitch)
      ↓
Timing Synchronization (atempo stretching to fit exact segment window)
      ↓
Dialogue Timeline Assembly (Accurate millisecond delay placement)
      ↓
Audio Mixing (Target speech + preserved background audio with volume controls 0-200%)
      ↓
Video Muxing (`-c:v copy` preserves untouched video frames, FPS, resolution)
      ↓
Final Output Video + Subtitles (SRT, VTT, TXT transcripts)
```

---

## 🚀 Key Features

1. **Dual Video Ingestion:**
   - Upload MP4, MOV, MKV, AVI, WEBM (probes duration, resolution, FPS, codecs).
   - Ingest public YouTube videos via `yt-dlp` (DRM and private video restrictions strictly respected).
2. **21+ Supported Languages:**
   - Auto Detect, English, Telugu, Hindi, Tamil, Kannada, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Urdu, Spanish, French, German, Italian, Portuguese, Japanese, Korean, Chinese, Arabic, Russian.
   - Real-time swap button (`⇄ Swap Languages`) with identical-language prevention.
3. **Independent Video Duration Limiting:**
   - 30s, 1m, 2m, 5m, 10m, 15m, 30m, 60m, Custom HH:MM:SS range, or Process Full Video.
   - Validation before processing: prompts user to auto-trim, adjust limit, process full video, or cancel.
4. **Audio Preservation Controls:**
   - Preserve Background Music (ON/OFF).
   - Preserve Sound Effects (ON/OFF).
   - Replace Spoken Language (ON/OFF).
   - Preserve Original Video (ON/OFF).
   - Independent volume sliders: Voice (0–200%), Background Music (0–200%), SFX (0–200%).
5. **Target Voice Customization:**
   - Voice Gender: Female, Male, Neutral.
   - Voice Style: Natural, Professional, Friendly, Narrator, Energetic, Calm.
   - Speaking Speed: 0.75x, 1.0x, 1.25x, 1.5x.
   - Pitch: Low, Normal, High.
6. **Subtitles & Transcripts:**
   - Generate Original Subtitles (SRT/VTT/TXT).
   - Generate Target Subtitles (SRT/VTT/TXT).
   - Optional hardcoded burn-in (Top/Bottom position, Small/Medium/Large font).
7. **Interactive Dashboard:**
   - Real-time 11-stage progress tracker.
   - Side-by-side video preview (Original vs Target Language).
   - Audio comparison player (Original Audio vs Target Language Mixed Audio).
   - Instant downloadable artifacts.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy ORM, SQLite
- **Audio & Video Processing:** FFmpeg, `ffprobe`, `pydub`, `yt-dlp`
- **Speech Recognition:** Faster-Whisper, Gemini AI Multimodal Audio, Acoustic VAD
- **Translation:** Gemini AI Translator, Google Translate client
- **TTS:** `gTTS`, Edge-TTS, Gemini Audio
- **Frontend:** HTML5, CSS3, Modern JavaScript (responsive studio dashboard)

---

## 💻 Installation & Local Development

### Prerequisites

- **Python 3.11+** installed
- **FFmpeg** installed and accessible in your system `PATH`:
  - **macOS:** `brew install ffmpeg`
  - **Windows:** `winget install Gyan.FFmpeg` or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
  - **Linux (Ubuntu/Debian):** `sudo apt-get install -y ffmpeg`

---

### Step-by-Step Instructions

#### 🍏 macOS

```bash
# 1. Clone or navigate to the repository
cd youtube-language-converter

# 2. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment variables
cp .env.example .env

# 5. Start the FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser.

---

#### 🪟 Windows (PowerShell)

```powershell
# 1. Navigate to the project folder
cd youtube-language-converter

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment variables
Copy-Item .env.example .env

# 5. Start the application
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser.

---

### 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up --build -d

# Check logs
docker compose logs -f
```

---

## 🧪 Automated Testing

Run the full test suite (including the 30s English→Telugu and 2-min Hindi→English test workflows):

```bash
PYTHONPATH=. pytest -v tests/
```

Test coverage includes:
1. Video upload and metadata inspection
2. Duration validation and auto-trimming
3. Language pairing validation
4. Audio extraction (16-bit PCM WAV)
5. Spectral vocal and background separation
6. Segment translation
7. Target TTS synthesis and timeline delay placement
8. Audio mixing with volume weights
9. Lossless video muxing (`-c:v copy`)
10. Downloadable artifact endpoints

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/video/upload` | Upload video file (MP4, MOV, MKV, AVI, WEBM) |
| `POST` | `/api/video/youtube` | Ingest YouTube video URL |
| `GET` | `/api/video/{video_id}` | Retrieve video metadata |
| `DELETE`| `/api/video/{video_id}` | Remove video and storage |
| `GET` | `/api/languages` | List supported languages |
| `GET` | `/api/voices` | List voice styles, genders, pitches |
| `POST` | `/api/process` | Dispatch background conversion job |
| `GET` | `/api/job/{job_id}` | Poll progress (stages 1–11) and results |
| `GET` | `/api/download/{file_id}`| Download final MP4, SRT, VTT, TXT |
| `GET` | `/api/media/{job_id}/{type}` | Stream media previews (video / audio) |
