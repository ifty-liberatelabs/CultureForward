from pydantic import BaseModel, Field, HttpUrl
from typing import List
from datetime import datetime
from uuid import UUID


class InitInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Survey title")
    goal: str = Field(..., min_length=1, max_length=500, description="Survey goal or objective")
    company_url: HttpUrl = Field(..., description="Company website URL for analysis")


class InitResponse(BaseModel):
    survey_id: UUID = Field(..., description="Unique survey session identifier")
    created_at: datetime = Field(..., description="Timestamp when session was created")


class ChatInput(BaseModel):
    survey_id: UUID = Field(..., description="Survey session ID from /init endpoint")
    message: str = Field(..., min_length=1, description="Your message or feedback about themes")


class ChatResponse(BaseModel):
    survey_id: UUID = Field(..., description="Survey session identifier")
    themes: List[dict] = Field(..., min_length=1, max_length=10, description="Generated or refined survey themes")
    message: str = Field(..., description="AI response explaining the themes or changes")
    created_at: datetime = Field(..., description="Timestamp when response was created")
