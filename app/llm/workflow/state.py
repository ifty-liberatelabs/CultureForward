from typing import TypedDict, List, Dict


class SurveyGenerationState(TypedDict):
    """
    SurveyGenerationState contains the state for survey theme generation workflow.
    """
    context: str  # User-provided context about survey needs
    company_url: str  # Company website URL
    company_analysis: str  # Generated company analysis from CompanyAnalyzerNode
    themes: List[Dict]  # Generated survey themes from ThemeGeneratorNode
    node_status: str  # Current node status

