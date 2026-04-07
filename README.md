# Visilink: Advanced YouTube & Video AI Analyzer

Visilink is a powerful full-stack application designed to extract, analyze, and summarize video content using state-of-the-art AI models. It goes beyond simple transcription by identifying visual elements in a video (graphs, charts, diagrams) and incorporating them into structured summaries and interactive Q&A.

---

## Features

- **Dual Source Support**: Analyze YouTube URLs directly or upload local video files.
- **Multimodal AI Analysis**:
  - **Transcription**: High-precision local transcription using `faster-whisper`.
  - **Visual Recognition**: Automatically detects visual triggers (charts, board writing, etc.) and extracts relevant frames.
  - **Frame Analysis**: Uses Gemini (cloud) or Moondream (local) to identify and explain visual data.
  - **Text Generation**: Uses Gemini (cloud) or Qwen 2.5 (local) for summarization and answering questions.
- **Advanced Summaries**: Generates structured Markdown summaries with **Comparison Tables** for visual content.
- **On-Demand Visual Q&A**: Ask follow-up questions with specific timestamps (e.g., "What is shown at 02:45?") and the system will dynamically extract and analyze a fresh frame live.
- **History Management**: Track and manage your past analyses in a beautiful, glassmorphic UI.
- **AI Engine Toggle**: Switch between **Cloud (Gemini)** for speed/scale or **Local (Ollama/Whisper)** for privacy/cost.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: Local MySQL (Relational storage)
- **Transcription**: `faster-whisper` (Base model)
- **Local AI Models**: `qwen2.5:3b` (Text) and `moondream` (Vision) via Ollama
- **Cloud AI**: Google Gemini 2.5 Flash
- **Video Processing**: `yt-dlp` and `ffmpeg`

### Frontend
- **Framework**: React 19 (Vite)
- **Styling**: Vanilla CSS (Custom Glassmorphic Design)
- **Icons**: Lucide React
- **Markdown**: `react-markdown` with GFM support for tables.

---

## Quick Start

### 1. Prerequisites
- Python 3.9+ and Node.js 18+
- **FFmpeg** (Ensure it is in your system PATH)
- **MySQL** (Running locally on port 3306)
- **Ollama** (Required for local AI mode, with `qwen2.5:3b` and `moondream` models)

### 2. Backend Setup
1. Navigate to `backend/`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your `.env` file (see `.env.example`).
4. Initialize the database:
   ```bash
   python create_db.py
   ```
5. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

### 3. Frontend Setup
1. Navigate to `frontend/`.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## Technical Note: Video Persistence
To support the **On-Demand Frame Extraction** feature, the backend stores a persistent copy of analyzed videos in a local `backend/data/videos` folder. This folder is excluded from version control to save space. If you delete these files, the Q&A system will fall back to text-only analysis for those videos.

---

## Acknowledgments
- Inspired by the need for better educational video summaries.
- Powered by Google Gemini, OpenAI Whisper, and the Ollama community (Qwen & Moondream).
