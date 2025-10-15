from pydantic import BaseModel, Field, HttpUrl
from typing import List
from datetime import datetime


class SurveyThemeInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    goal: str = Field(..., min_length=1, max_length=500)
    company_url: HttpUrl


class SurveyThemeResponse(BaseModel):
    themes: List[dict] = Field(..., min_length=4, max_length=5)
    created_at: datetime

