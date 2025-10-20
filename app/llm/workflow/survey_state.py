from typing import TypedDict, List, Dict, Optional


class ConversationalSurveyState(TypedDict):
    """State for conversational survey agent"""
    # Survey context
    survey_id: str
    thread_id: str
    survey_title: str
    survey_goal: str
    themes: List[Dict]  # List of theme objects: [{"theme": "theme_name"}]
    
    # Current conversation
    user_message: str
    conversation_history: List[Dict]  # [{"role": "user/assistant", "content": "..."}]
    
    # Theme tracking
    current_theme_index: int  # Index of the theme being discussed
    theme_responses: Dict[str, Dict]  # {theme_name: {"answer": "...", "complete": bool, "follow_ups": []}}
    
    # Evaluation results
    is_answer_complete: bool  # Whether current answer satisfies the theme
    needs_follow_up: bool  # Whether follow-up question is needed
    next_theme_index: Optional[int]  # Index of next theme to ask about
    
    # Agent responses
    agent_response: str  # Question or follow-up from conversational agent
    all_themes_complete: bool  # Whether all themes have been answered
    survey_complete: bool  # Whether the entire survey including feedback is complete
    
    # Node status
    node_status: str

