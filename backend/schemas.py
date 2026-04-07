from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class AnalyzeRequest(BaseModel):
    url: HttpUrl
    engine: str = "gemini"  # 'gemini' or 'local'

class VideoAnalysisResponse(BaseModel):
    id: int
    youtube_url: str
    video_title: Optional[str]
    transcript: Optional[str]
    summary: Optional[str]
    engine: str = "gemini"
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class ErrorResponse(BaseModel):
    detail: str

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
