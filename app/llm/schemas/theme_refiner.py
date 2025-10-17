from pydantic import BaseModel, Field
from typing import List


class ThemeRefinerResponse(BaseModel):
    themes: List[str] = Field(
        ...,
        description="List of refined survey theme titles"
    )
    explanation: str = Field(
        ...,
        description="Brief explanation of changes made based on user feedback"
    )