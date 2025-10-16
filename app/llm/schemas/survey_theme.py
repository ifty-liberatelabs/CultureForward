from pydantic import BaseModel, Field
from typing import List


class SurveyThemeAgentResponse(BaseModel):
    themes: List[str] = Field(
        ...,
        description="List of 4-5 survey theme titles",
        min_length=1,
        max_length=5
    )

