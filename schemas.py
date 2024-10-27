# schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict

class SummarySchema(BaseModel):
    id: int
    lesson_name: str
    lesson_link: str
    lesson_type: str
    icon_file: Optional[str]
    data: Dict  # Assuming JSON contains a dictionary with "description", "items", "textbooks", etc.
    topic_id: int
    topic_title: str  # New field for the topic title
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
