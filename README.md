# YouTube Audio Analyzer (Visilink)

A full-stack web application to extract audio from YouTube videos, transcribe it using OpenAI Whisper, and summarize the content using the Gemini API.

## Tech Stack
- Frontend: React (Vite)
- Backend: Python (FastAPI)
- Database: Firebase Firestore (Cloud Database)
- AI Tools: yt-dlp, OpenAI Whisper (local), Gemini API (remote)

## Prerequisites
- Python 3.9+
- Node.js 18+
- Firebase account with Firestore database
- Gemini API key
- FFmpeg installed and in your system PATH (required for `yt-dlp`)

## Setup Instructions

### Firebase Database Setup
See [FIREBASE_SETUP.md](./FIREBASE_SETUP.md) for detailed Firebase configuration steps.

### Backend Setup
1. Navigate to the `backend` directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Firebase credentials and Gemini API key.
5. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install frontend dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

## Usage
1. Open the frontend in your browser (usually `http://localhost:5173`).
2. Paste a YouTube URL and click "Analyze".
3. Wait for the audio extraction, local transcription, and AI summarization.
4. View the results or browse the past history.

## Deployment
See [FIREBASE_SETUP.md](./FIREBASE_SETUP.md) for cloud deployment instructions.

