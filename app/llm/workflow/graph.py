from langgraph.graph import StateGraph, END

from app.llm.workflow.state import SurveyGenerationState
from app.llm.workflow.agents import (
    company_analyzer_agent,
    theme_generator_agent
)
from app.core.logging import logger


def starting_node(state: SurveyGenerationState):
    """Initial node to validate inputs."""
    logger.info("Starting survey theme generation workflow")
    return {"node_status": "started"}


def final_node(state: SurveyGenerationState):
    """Final node to complete workflow."""
    logger.info("Survey theme generation workflow completed")
    return {"node_status": "completed"}


class SurveyThemeGraph(StateGraph):
    def __init__(self):
        super().__init__(SurveyGenerationState)

        # Add nodes
        self.add_node("start", starting_node)
        self.add_node(
            "company_analyzer",
            company_analyzer_agent.company_analyzer_node
        )
        self.add_node(
            "theme_generator",
            theme_generator_agent.theme_generator_node
        )
        self.add_node("final", final_node)

        # Define edges
        self.set_entry_point("start")
        self.add_edge("start", "company_analyzer")
        self.add_edge("company_analyzer", "theme_generator")
        self.add_edge("theme_generator", "final")
        self.add_edge("final", END)

    def compile_graph(self):
        """Compile the graph for execution."""
        return self.compile()


survey_theme_graph = SurveyThemeGraph()

