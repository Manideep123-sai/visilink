from typing import Optional
from datetime import datetime

class VideoAnalysis:
    """Firestore model for video analyses"""

    def __init__(
        self,
        youtube_url: str,
        video_title: Optional[str] = None,
        transcript: Optional[str] = None,
        summary: Optional[str] = None,
        visual_analyses: Optional[str] = None,
        engine: str = "gemini",
        created_at: Optional[datetime] = None,
        doc_id: Optional[str] = None
    ):
        self.doc_id = doc_id
        self.youtube_url = youtube_url
        self.video_title = video_title
        self.transcript = transcript
        self.summary = summary
        self.visual_analyses = visual_analyses
        self.engine = engine
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self):
        """Convert to Firestore document format"""
        return {
            "youtube_url": self.youtube_url,
            "video_title": self.video_title,
            "transcript": self.transcript,
            "summary": self.summary,
            "visual_analyses": self.visual_analyses,
            "engine": self.engine,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data, doc_id):
        """Create instance from Firestore document"""
        return VideoAnalysis(
            doc_id=doc_id,
            youtube_url=data.get("youtube_url"),
            video_title=data.get("video_title"),
            transcript=data.get("transcript"),
            summary=data.get("summary"),
            visual_analyses=data.get("visual_analyses"),
            engine=data.get("engine", "gemini"),
            created_at=data.get("created_at"),
        )

