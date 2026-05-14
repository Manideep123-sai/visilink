# Manideep Sai C
# Reg.no 23BCE0737

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import traceback
import tempfile
import json
import yt_dlp
import time
import shutil

import models, schemas, services
from database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Persistent data directory for videos
DATA_DIR = os.path.join(os.getcwd(), "data", "videos")
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="Visilink API")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    engine_choice: str = Form("gemini"),
    db: Session = Depends(get_db)
):
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

    # Clean up audio
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    # Save video to persistent storage for on-demand Q&A
    final_video_name = f"{db.query(models.VideoAnalysis).count() + 1}_{file.filename}"
    persistent_video_path = os.path.join(DATA_DIR, final_video_name)
    import shutil
    shutil.move(video_path, persistent_video_path)

    # Serialize visual analyses for storage
    visual_analyses_json = None
    if visual_analyses:
        visual_analyses_json = json.dumps({str(k): v for k, v in visual_analyses.items()})

    # 5. Save to database
    db_analysis = models.VideoAnalysis(
        youtube_url=f"local://{video_title}",
        video_title=video_title,
        transcript=transcript,
        summary=summary,
        visual_analyses=visual_analyses_json,
        video_path=persistent_video_path,
        engine=engine_choice
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    return db_analysis


@app.post("/api/analyze", response_model=schemas.VideoAnalysisResponse)
def analyze_video(request: schemas.AnalyzeRequest, db: Session = Depends(get_db)):
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
            final_video_name = f"yt_{int(time.time())}.mp4"
            persistent_video_path = os.path.join(DATA_DIR, final_video_name)

            opts = {
                'format': 'bestvideo[ext=mp4]/best',
                'outtmpl': persistent_video_path,
                'quiet': True,
                'no_warnings': True
            }

            import time
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            frames = services.extract_frames(persistent_video_path, triggers)

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

    # 5. Save to database
    db_analysis = models.VideoAnalysis(
        youtube_url=url,
        video_title=title,
        transcript=transcript,
        summary=summary,
        visual_analyses=visual_analyses_json,
        video_path=persistent_video_path if 'persistent_video_path' in locals() else None,
        engine=engine_choice
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    return db_analysis

@app.get("/api/history", response_model=list[schemas.VideoAnalysisResponse])
def get_history(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    analyses = db.query(models.VideoAnalysis).order_by(models.VideoAnalysis.created_at.desc()).offset(skip).limit(limit).all()
    return analyses

@app.get("/api/analyses/{analysis_id}", response_model=schemas.VideoAnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(models.VideoAnalysis).filter(models.VideoAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@app.delete("/api/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(models.VideoAnalysis).filter(models.VideoAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    db.delete(analysis)
    db.commit()
    return None

@app.post("/api/analyses/{analysis_id}/question", response_model=schemas.QuestionResponse)
def ask_question(analysis_id: int, request: schemas.QuestionRequest, db: Session = Depends(get_db)):
    analysis = db.query(models.VideoAnalysis).filter(models.VideoAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not analysis.transcript:
        raise HTTPException(status_code=400, detail="No transcript available to answer questions from.")

    try:
        ai = get_ai_functions(analysis.engine or "gemini")
        answer = ai["answer"](
            transcript=analysis.transcript,
            question=request.question,
            visual_analyses_json=analysis.visual_analyses,
            video_path=analysis.video_path
        )
        return schemas.QuestionResponse(answer=answer)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")
