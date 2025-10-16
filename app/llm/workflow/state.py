from typing import TypedDict, List, Dict, Optional


class SurveyThemeState(TypedDict):
    title: str
    goal: str
    company_url: str
    current_themes: Optional[List[Dict]]
    user_feedback: Optional[str]
    company_analysis: str
    themes: List[Dict]
    explanation: Optional[str]
    chat_history: Optional[List[Dict]]
    node_status: str
