from langgraph.graph import StateGraph, END

from app.llm.workflow.survey_state import ConversationalSurveyState
from app.llm.workflow.survey_agents import conversation_agent, evaluation_agent
from app.core.logging import logger


def start_node(state: ConversationalSurveyState):
    """Entry point for the survey conversation"""
    logger.info(f"Starting survey conversation for thread: {state.get('thread_id')}")
    
    # Initialize theme_responses if not exists
    if "theme_responses" not in state or state["theme_responses"] is None:
        state["theme_responses"] = {}
    
    # Check if this is the first message
    conversation_history = state.get("conversation_history", [])
    if not conversation_history:
        # First question - no evaluation needed
        return {"node_status": "start_first_question"}
    else:
        # User has responded - evaluate their answer
        return {"node_status": "start_evaluation"}


def routing_after_start(state: ConversationalSurveyState) -> str:
    """Route based on whether this is first question or evaluation needed"""
    conversation_history = state.get("conversation_history", [])
    
    if not conversation_history:
        return "conversation"
    else:
        return "evaluation"


def routing_after_evaluation(state: ConversationalSurveyState) -> str:
    """Route based on evaluation results"""
    survey_complete = state.get("survey_complete", False)
    all_themes_complete = state.get("all_themes_complete", False)
    
    if survey_complete:
        return "final"
    
    if all_themes_complete:
        # All themes done, ask for feedback
        next_theme_index = state.get("next_theme_index")
        if next_theme_index == -2:  # Feedback phase
            state["current_theme_index"] = -2
            return "conversation"
        else:
            return "final"
    
    needs_follow_up = state.get("needs_follow_up", False)
    is_complete = state.get("is_answer_complete", False)
    
    if not is_complete or needs_follow_up:
        # Need follow-up or answer incomplete
        return "conversation"
    else:
        # Move to next theme
        next_theme_index = state.get("next_theme_index")
        if next_theme_index is not None and next_theme_index >= 0:
            # Update current theme index
            state["current_theme_index"] = next_theme_index
            return "conversation"
        else:
            # No more themes
            return "final"


def final_node(state: ConversationalSurveyState):
    """Complete the survey"""
    logger.info(f"Survey conversation completed for thread: {state.get('thread_id')}")
    return {
        "all_themes_complete": True,
        "survey_complete": True,
        "agent_response": "Thank you so much for sharing your thoughtful responses! I really appreciate the time you've taken to complete this survey. Your feedback is valuable and will help make meaningful improvements.",
        "node_status": "survey_complete"
    }


class ConversationalSurveyGraph(StateGraph):
    def __init__(self):
        super().__init__(ConversationalSurveyState)

        # Add nodes
        self.add_node("start", start_node)
        self.add_node("conversation", conversation_agent.conversation_node)
        self.add_node("evaluation", evaluation_agent.evaluation_node)
        self.add_node("final", final_node)

        # Set entry point
        self.set_entry_point("start")
        
        # Add edges with routing
        self.add_conditional_edges("start", routing_after_start, {
            "conversation": "conversation",
            "evaluation": "evaluation"
        })
        
        # After conversation, if it's a follow-up/question, wait for user response
        # The endpoint will handle returning to user
        self.add_edge("conversation", END)
        
        # After evaluation, decide next step
        self.add_conditional_edges("evaluation", routing_after_evaluation, {
            "conversation": "conversation",
            "end": "final"
        })
        
        # Final node ends
        self.add_edge("final", END)

    def compile_graph(self, checkpointer=None):
        return self.compile(checkpointer=checkpointer) if checkpointer else self.compile()


conversational_survey_graph = ConversationalSurveyGraph()

