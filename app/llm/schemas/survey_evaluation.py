from pydantic import BaseModel, Field
from typing import Optional


class SurveyEvaluationResponse(BaseModel):
    """Response from survey evaluation agent"""
    is_answer_complete: bool = Field(
        ...,
        description="Whether the user's answer sufficiently addresses the current theme"
    )
    needs_follow_up: bool = Field(
        ...,
        description="Whether a follow-up question is needed for more detail or clarification"
    )
    follow_up_reason: Optional[str] = Field(
        None,
        description="Reason why follow-up is needed (if applicable)"
    )
    next_theme_index: Optional[int] = Field(
        None,
        description="Index of the next theme to ask about based on conversation flow (-1 if no more themes)"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of the evaluation decision"
    )

