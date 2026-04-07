from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class VideoAnalysis(Base):
    __tablename__ = "video_analyses"

    id = Column(Integer, primary_key=True, index=True)
    youtube_url = Column(String(500), index=True, nullable=False)
    video_title = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    visual_analyses = Column(Text, nullable=True)  # JSON string of frame analyses
    video_path = Column(String(500), nullable=True) # Path to local video file for on-demand Q&A
    engine = Column(String(50), nullable=False, default="gemini")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


