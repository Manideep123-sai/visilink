from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import traceback
import tempfile
import json
import yt_dlp

import models, schemas, services
from database import get_db

app = FastAPI(title="Visilink API")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to pick the right AI functions based on engine choice
def get_ai_functions(engine_choice: str):
    if engine_choice == "local":
        return {
            "detect_triggers": services.detect_visual_triggers_local,
            "analyze_frames": services.analyze_frames_local,
            "summarize": services.summarize_text_local,
            "answer": services.answer_question_local,
        }
    else:
        return {
            "detect_triggers": services.detect_visual_triggers_gemini,
            "analyze_frames": services.analyze_frames_gemini,
            "summarize": services.summarize_text_gemini,
            "answer": services.answer_question_gemini,
        }

@app.post("/api/analyze/upload", response_model=schemas.VideoAnalysisResponse)
async def analyze_uploaded_video(
    file: UploadFile = File(...),
    engine_choice: str = Form("gemini")
):
    db = get_db()
    ai = get_ai_functions(engine_choice)

    # Save the uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, f"upload_{file.filename}")

    with open(video_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    video_title = file.filename
    audio_path = None

    try:
        # 1. Extract audio from local file
        audio_path = services.extract_audio_from_local(video_path)
    except Exception as e:
        traceback.print_exc()
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=400, detail=f"Failed to extract audio from uploaded file. {str(e)}")

    try:
        # 2. Transcribe
        transcript = services.transcribe_audio(audio_path)
    except Exception as e:
        traceback.print_exc()
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {str(e)}")

    try:
        # 3. Visual Analysis
        visual_analyses = None
        triggers = ai["detect_triggers"](transcript)
        if triggers:
            frames = services.extract_frames(video_path, triggers)
            if frames:
                visual_analyses = ai["analyze_frames"](frames, transcript)
    except Exception as e:
        traceback.print_exc()
        pass

    try:
        # 4. Summarize
        summary = ai["summarize"](transcript, visual_analyses)
    except Exception as e:
        traceback.print_exc()
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Failed to summarize transcript: {str(e)}")

    # Clean up
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(video_path):
        os.remove(video_path)

    # Serialize visual analyses for storage
    visual_analyses_json = None
    if visual_analyses:
        visual_analyses_json = json.dumps({str(k): v for k, v in visual_analyses.items()})

    # 5. Save to Firestore
    analysis = models.VideoAnalysis(
        youtube_url=f"local://{video_title}",
        video_title=video_title,
        transcript=transcript,
        summary=summary,
        visual_analyses=visual_analyses_json,
        engine=engine_choice
    )

    doc_ref = db.collection("video_analyses").add(analysis.to_dict())
    analysis.doc_id = doc_ref[1].id

    return {
        "id": analysis.doc_id,
        "youtube_url": analysis.youtube_url,
        "video_title": analysis.video_title,
        "transcript": analysis.transcript,
        "summary": analysis.summary,
        "visual_analyses": analysis.visual_analyses,
        "engine": analysis.engine,
        "created_at": analysis.created_at
    }


@app.post("/api/analyze", response_model=schemas.VideoAnalysisResponse)
def analyze_video(request: schemas.AnalyzeRequest):
    db = get_db()
    url = str(request.url)
    engine_choice = request.engine
    ai = get_ai_functions(engine_choice)
    audio_path = None

    try:
        # 1. Extract audio
        audio_path, title = services.extract_audio(url)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract audio. Check the URL or video privacy. {str(e)}")

    try:
        # 2. Transcribe
        transcript = services.transcribe_audio(audio_path)
    except Exception as e:
        traceback.print_exc()
        # Clean up
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {str(e)}")

    try:
        # 3. Visual Analysis (Optional enhancement)
        visual_analyses = None
        triggers = ai["detect_triggers"](transcript)
        if triggers:
            # For youtube links, we must download the video first since extract_frames asks for a local path
            temp_dir = tempfile.gettempdir()
            video_path = os.path.join(temp_dir, "temp_youtube_video.mp4")

            opts = {
                'format': 'bestvideo[ext=mp4]/best',
                'outtmpl': video_path,
                'quiet': True,
                'no_warnings': True
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            frames = services.extract_frames(video_path, triggers)

            if os.path.exists(video_path):
                os.remove(video_path)

            if frames:
                visual_analyses = ai["analyze_frames"](frames, transcript)
    except Exception as e:
        traceback.print_exc()
        # Proceed with summary even if visual processing fails
        pass

    try:
        # 4. Summarize
        summary = ai["summarize"](transcript, visual_analyses)
    except Exception as e:
        traceback.print_exc()
        # Clean up
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        raise HTTPException(status_code=500, detail=f"Failed to summarize transcript: {str(e)}")

    # Clean up audio file
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)

    # Serialize visual analyses for storage
    visual_analyses_json = None
    if visual_analyses:
        visual_analyses_json = json.dumps({str(k): v for k, v in visual_analyses.items()})

    # 5. Save to Firestore
    analysis = models.VideoAnalysis(
        youtube_url=url,
        video_title=title,
        transcript=transcript,
        summary=summary,
        visual_analyses=visual_analyses_json,
        engine=engine_choice
    )

    doc_ref = db.collection("video_analyses").add(analysis.to_dict())
    analysis.doc_id = doc_ref[1].id

    return {
        "id": analysis.doc_id,
        "youtube_url": analysis.youtube_url,
        "video_title": analysis.video_title,
        "transcript": analysis.transcript,
        "summary": analysis.summary,
        "visual_analyses": analysis.visual_analyses,
        "engine": analysis.engine,
        "created_at": analysis.created_at
    }

@app.get("/api/history", response_model=list[schemas.VideoAnalysisResponse])
def get_history(skip: int = 0, limit: int = 20):
    db = get_db()
    docs = db.collection("video_analyses").order_by("created_at", direction="DESCENDING").offset(skip).limit(limit).stream()
    analyses = []
    for doc in docs:
        data = doc.to_dict()
        analysis = models.VideoAnalysis.from_dict(data, doc.id)
        analyses.append({
            "id": analysis.doc_id,
            "youtube_url": analysis.youtube_url,
            "video_title": analysis.video_title,
            "transcript": analysis.transcript,
            "summary": analysis.summary,
            "visual_analyses": analysis.visual_analyses,
            "engine": analysis.engine,
            "created_at": analysis.created_at
        })
    return analyses

@app.get("/api/analyses/{analysis_id}", response_model=schemas.VideoAnalysisResponse)
def get_analysis(analysis_id: str):
    db = get_db()
    doc = db.collection("video_analyses").document(analysis_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Analysis not found")

    data = doc.to_dict()
    analysis = models.VideoAnalysis.from_dict(data, doc.id)

    return {
        "id": analysis.doc_id,
        "youtube_url": analysis.youtube_url,
        "video_title": analysis.video_title,
        "transcript": analysis.transcript,
        "summary": analysis.summary,
        "visual_analyses": analysis.visual_analyses,
        "engine": analysis.engine,
        "created_at": analysis.created_at
    }

@app.delete("/api/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str):
    db = get_db()
    doc = db.collection("video_analyses").document(analysis_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Analysis not found")

    db.collection("video_analyses").document(analysis_id).delete()
    return None

@app.post("/api/analyses/{analysis_id}/question", response_model=schemas.QuestionResponse)
def ask_question(analysis_id: str, request: schemas.QuestionRequest):
    db = get_db()
    doc = db.collection("video_analyses").document(analysis_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Analysis not found")

    data = doc.to_dict()
    analysis = models.VideoAnalysis.from_dict(data, doc.id)

    if not analysis.transcript:
        raise HTTPException(status_code=400, detail="No transcript available to answer questions from.")

    try:
        ai = get_ai_functions(analysis.engine or "gemini")
        answer = ai["answer"](analysis.transcript, request.question, analysis.visual_analyses)
        return schemas.QuestionResponse(answer=answer)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")
