"""
Pydantic schemas for learning analytics structured outputs from LLM
"""
from pydantic import BaseModel, Field
from typing import List


# Task-Level Analysis Schema (for OpenAI structured output)
class TaskAnalysisSchema(BaseModel):
    """
    Schema for task-level analysis structured output from LLM.

    Note: task_summary is no longer part of this schema. It's pre-generated once per task
    and stored in tasks.task_summary field to avoid regenerating for every student.
    """
    error_patterns: List[str] = Field(
        ...,
        description="List of 2-3 specific error patterns observed",
        min_length=0,
        max_length=5
    )
    learning_progression: str = Field(
        ...,
        description="Classification of learning progression",
        pattern="^(immediate_success|struggle_then_breakthrough|persistent_difficulty)$"
    )
    concept_gaps: List[str] = Field(
        ...,
        description="List of 2-3 specific concept gaps requiring reinforcement",
        min_length=0,
        max_length=5
    )
    strengths: List[str] = Field(
        ...,
        description="List of 1-2 demonstrated strengths",
        min_length=0,
        max_length=3
    )
    help_needed: bool = Field(
        ...,
        description="Whether student needs instructor intervention"
    )
    difficulty_level: str = Field(
        ...,
        description="Assessment of task difficulty appropriateness",
        pattern="^(too_easy|appropriate|too_hard)$"
    )


# Lesson-Level Analysis Schema (for OpenAI structured output)
class LessonAnalysisSchema(BaseModel):
    """Schema for lesson-level analysis structured output from LLM"""
    mastered_concepts: List[str] = Field(
        ...,
        description="List of 2-4 concepts mastered across tasks",
        min_length=0,
        max_length=6
    )
    struggling_concepts: List[str] = Field(
        ...,
        description="List of 2-4 concepts student is struggling with",
        min_length=0,
        max_length=6
    )
    pacing: str = Field(
        ...,
        description="Assessment of content difficulty match to student level",
        pattern="^(overwhelmed|appropriate|under_challenged)$"
    )
    retention_score: float = Field(
        ...,
        description="Score 0.0-1.0 indicating concept retention from early to late tasks",
        ge=0.0,
        le=1.0
    )
    help_seeking_pattern: str = Field(
        ...,
        description="Assessment of student's help-seeking behavior",
        pattern="^(too_frequent|appropriate|too_rare)$"
    )
    topic_dependencies_issues: List[str] = Field(
        ...,
        description="List of topic dependency problems identified",
        min_length=0,
        max_length=5
    )


# Course-Level Analysis Schema (for OpenAI structured output)
class ConceptGraph(BaseModel):
    """Nested schema for concept mastery graph"""
    strong_foundations: List[str] = Field(
        ...,
        description="Concepts with high retention and transfer",
        min_length=0,
        max_length=10
    )
    weak_connections: List[str] = Field(
        ...,
        description="Topic transitions where student struggled",
        min_length=0,
        max_length=10
    )


class PracticeRecommendation(BaseModel):
    """Nested schema for personalized practice recommendations"""
    concept: str = Field(..., min_length=1, max_length=200)
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    count: int = Field(..., ge=1, le=10, description="Recommended number of practice tasks")


class CourseProfileSchema(BaseModel):
    """Schema for course-level profile structured output from LLM"""
    core_strengths: List[str] = Field(
        ...,
        description="2-3 programming skills consistently demonstrated",
        min_length=0,
        max_length=5
    )
    persistent_weaknesses: List[str] = Field(
        ...,
        description="2-3 concepts remaining challenging across lessons",
        min_length=0,
        max_length=5
    )
    learning_velocity: str = Field(
        ...,
        description="Overall learning velocity assessment",
        pattern="^(rapid_improvement|steady_progress|plateaued|declining)$"
    )
    resilience_score: float = Field(
        ...,
        description="Score 0.0-1.0 indicating recovery from failures",
        ge=0.0,
        le=1.0
    )
    preferred_learning_style: str = Field(
        ...,
        description="Identified preferred learning style",
        pattern="^(visual_with_examples|trial_and_error|concept_first|pattern_recognition)$"
    )
    readiness_for_advanced: bool = Field(
        ...,
        description="Whether student is ready for advanced topics"
    )
    concept_graph: ConceptGraph = Field(
        ...,
        description="Map of concept mastery strengths and weaknesses"
    )
    recommended_practice: List[PracticeRecommendation] = Field(
        ...,
        description="2-3 personalized practice recommendations",
        min_length=0,
        max_length=5
    )
