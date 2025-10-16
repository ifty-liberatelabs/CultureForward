from langgraph.graph import StateGraph, END

from app.llm.workflow.state import SurveyThemeState
from app.llm.workflow.agents import (
    company_analyzer_agent,
    theme_generator_agent,
    theme_refiner_agent
)
from app.core.logging import logger


def starting_node(state: SurveyThemeState):
    workflow_type = "refinement" if state.get("themes") else "generation"
    logger.info(f"Starting theme {workflow_type} workflow")
    return {"node_status": "started"}


def workflow_routing(state: SurveyThemeState):
    return "refine" if state.get("themes") else "generate"


def final_node(state: SurveyThemeState):
    logger.info("Workflow completed")
    return {"node_status": "completed"}


class SurveyThemeGraph(StateGraph):
    def __init__(self):
        super().__init__(SurveyThemeState)

        self.add_node("start", starting_node)
        self.add_node("company_analyzer", company_analyzer_agent.company_analyzer_node)
        self.add_node("theme_generator", theme_generator_agent.theme_generator_node)
        self.add_node("theme_refiner", theme_refiner_agent.theme_refiner_node)
        self.add_node("final", final_node)

        self.set_entry_point("start")
        self.add_conditional_edges("start", workflow_routing, {
            "generate": "company_analyzer",
            "refine": "theme_refiner"
        })
        self.add_edge("company_analyzer", "theme_generator")
        self.add_edge("theme_generator", "final")
        self.add_edge("theme_refiner", "final")
        self.add_edge("final", END)

    def compile_graph(self, checkpointer=None):
        return self.compile(checkpointer=checkpointer) if checkpointer else self.compile()


survey_theme_graph = SurveyThemeGraph()
