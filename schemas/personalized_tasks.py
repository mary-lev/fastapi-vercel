"""
Pydantic schemas for personalized task generation feature
"""

from pydantic import BaseModel, Field
from typing import List, Literal


class StudentStruggleAnalysisSchema(BaseModel):
    """LLM output for student struggle synthesis"""

    critical_concepts: List[str] = Field(
        description="3-4 most critical concepts needing remediation in Russian",
        min_length=3,
        max_length=4
    )

    rationale: str = Field(
        description="Brief explanation of why these concepts were prioritized"
    )

    difficulty_level: Literal["beginner", "intermediate", "advanced"] = Field(
        description="Overall difficulty level for personalized tasks"
    )
