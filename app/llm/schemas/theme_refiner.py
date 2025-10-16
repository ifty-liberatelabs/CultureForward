from pydantic import BaseModel, Field
from typing import List


class ThemeRefinerResponse(BaseModel):
    themes: List[str] = Field(
        ...,
        description="List of refined survey theme titles (can be 4-8+ themes)",
        min_length=1,
        max_length=10
    )
    explanation: str = Field(
        ...,
        description="Brief explanation of changes made based on user feedback"
    )