# Visilink: Advanced YouTube & Video AI Analyzer 🎥🧠

Visilink is a powerful full-stack application designed to extract, analyze, and summarize video content using state-of-the-art AI models. It goes beyond simple transcription by identifying visual elements in a video (graphs, charts, diagrams) and incorporating them into structured summaries and interactive Q&A.

---

## ✨ Features

- **Dual Source Support**: Analyze YouTube URLs directly or upload local video files.
- **Multimodal AI Analysis**:
  - **Transcription**: High-precision local transcription using `faster-whisper`.
  - **Visual Recognition**: Automatically detects visual triggers (charts, board writing, etc.) and extracts relevant frames.
  - **Frame Analysis**: Uses Gemini (cloud) or Moondream (local) to "see" and explain visual data.
- **Advanced Summaries**: Generates structured Markdown summaries with **Comparison Tables** for visual content.
- **Interactive Q&A**: Ask follow-up questions about the video’s spoken and visual content.
- **History Management**: Track and manage your past analyses in a beautiful, glassmorphic UI.
- **AI Engine Toggle**: Switch between **Cloud (Gemini)** for speed/scale or **Local (Ollama/Whisper)** for privacy/cost.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: Local MySQL (Relational storage)
- **Transcription**: `faster-whisper`
- **Visual AI**: `google-generativeai` (Gemini) or `ollama` (Moondream)
- **Video Processing**: `yt-dlp` and `ffmpeg`

### Frontend
- **Framework**: React 19 (Vite)
- **Styling**: Vanilla CSS (Custom Glassmorphic Design)
- **Icons**: Lucide React
- **Markdown**: `react-markdown` with GFM support

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+ and Node.js 18+
- **FFmpeg** (Ensure it is in your system PATH)
- **MySQL** (Running locally on port 3306)
- **Ollama** (Optional, for local AI functionality)

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

## 📦 Deployment Note
This application is currently optimized for local execution with a local MySQL instance. To deploy to production, ensure your environment variables and database connection strings are updated accordingly.

---

## 🤝 Acknowledgments
- Inspired by the need for better educational video summaries.
- Powered by Google Gemini, OpenAI Whisper, and the Ollama community.
