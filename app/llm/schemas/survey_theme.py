from pydantic import BaseModel, Field
from typing import List


class SurveyThemeAgentResponse(BaseModel):
    themes: List[str] = Field(
        ...,
        description="List of survey theme titles"
    )

