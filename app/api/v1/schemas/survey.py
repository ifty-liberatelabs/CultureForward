from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime
from uuid import UUID


class InitSurveyInput(BaseModel):
    """Input for initializing a new survey thread"""
    survey_id: UUID = Field(..., description="ID of the survey to conduct")


class InitSurveyResponse(BaseModel):
    """Response when initializing a new survey thread"""
    thread_id: UUID = Field(..., description="Unique thread identifier for this conversation")
    survey_id: UUID = Field(..., description="Survey identifier")
    survey_title: str = Field(..., description="Title of the survey")
    created_at: datetime = Field(..., description="Timestamp when thread was created")


class SurveyChatInput(BaseModel):
    """Input for survey chat conversation"""
    thread_id: UUID = Field(..., description="Thread ID from init survey response")
    message: str = Field(..., description="User's message (can be 'hi', 'hello', or response to question)")


class SurveyChatResponse(BaseModel):
    """Response from survey chat"""
    thread_id: UUID = Field(..., description="Thread identifier")
    message: str = Field(..., description="Agent's question or follow-up")
    completed_theme: List[str] = Field(default=[], description="List of completed theme names")
    current_theme: str = Field(None, description="Current theme being discussed")
    all_themes_complete: bool = Field(default=False, description="Whether all themes have been completed")
    survey_complete: bool = Field(default=False, description="Whether the entire survey is complete")
    created_at: datetime = Field(..., description="Timestamp of response")


class SurveyThreadResponse(BaseModel):
    """Response containing thread information"""
    thread_id: UUID = Field(..., description="Thread identifier")
    survey_id: UUID = Field(..., description="Survey identifier")
    survey_title: str = Field(..., description="Survey title")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    messages: List[Dict] = Field(..., description="Conversation history")

