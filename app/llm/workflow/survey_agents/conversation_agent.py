from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
import yaml

from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.survey_state import ConversationalSurveyState
from app.utils.files import get_project_root


class ConversationAgent:
    def __init__(self):
        self.model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.7,
            max_retries=3
        )
        self.gemini_model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0.7,
            max_retries=2
        )
        self.llm = self.model.with_fallbacks([self.gemini_model])

    def get_prompt(self, name: str) -> str:
        """Load prompt from YAML file."""
        prompt_path = get_project_root() / "app" / "llm" / "prompts" / "survey_conversation.yml"
        with open(prompt_path, 'r') as f:
            prompts = yaml.safe_load(f)
        return prompts[name]["prompt"]

    def _format_conversation_history(self, history: list) -> str:
        """Format conversation history for prompt"""
        if not history:
            return "No previous conversation"
        
        formatted = []
        for msg in history:
            role = "You" if msg["role"] == "assistant" else "User"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def _format_themes(self, themes: list) -> str:
        """Format all themes as a readable list"""
        return "\n".join([f"- {theme['theme']}" for theme in themes])

    def _get_task_instructions(self, is_first_question: bool, needs_follow_up: bool) -> tuple:
        """Get task type and instructions based on conversation state"""
        if is_first_question:
            task_type = "Start the survey conversation"
            instructions = (
                "This is the first theme. Welcome the user warmly and ask your first question about this theme. "
                "Keep it friendly and conversational."
            )
        elif needs_follow_up:
            task_type = "Ask a follow-up question"
            instructions = (
                "The user's previous answer needs more depth or clarity. "
                "Ask a follow-up question that builds on what they said. "
                "Reference their previous response to show you're listening."
            )
        else:
            task_type = "Transition to new theme"
            instructions = (
                "Move to the next theme in a natural way. "
                "Briefly acknowledge their previous response if appropriate, "
                "then smoothly transition to the new theme."
            )
        
        return task_type, instructions

    @traceable(run_type="llm", name="Survey Conversation Agent")
    async def conversation_node(self, state: ConversationalSurveyState):
        """Generate conversational questions for survey themes"""
        logger.info(
            "Generating survey question",
            theme_index=state.get("current_theme_index"),
            needs_follow_up=state.get("needs_follow_up", False)
        )

        try:
            # Check survey completion status
            survey_complete = state.get("survey_complete", False)
            all_themes_complete = state.get("all_themes_complete", False)
            
            if survey_complete:
                return {
                    "agent_response": "Survey completed! Thank you for your participation.",
                    "node_status": "conversation_complete"
                }
            
            # Get current theme
            current_theme_index = state.get("current_theme_index", 0)
            themes = state.get("themes", [])
            
            # Check if we're in feedback phase
            if all_themes_complete and current_theme_index == -2:
                # Feedback phase
                current_theme = "feedback"
                return {
                    "agent_response": "Is there anything you want to add or any feedback you'd like to share?",
                    "node_status": "conversation_complete"
                }
            elif current_theme_index >= len(themes):
                return {
                    "agent_response": "Thank you for completing the survey!",
                    "node_status": "conversation_complete"
                }
            else:
                current_theme = themes[current_theme_index]["theme"]
            
            # Determine if this is first question
            conversation_history = state.get("conversation_history", [])
            is_first_question = len(conversation_history) == 0
            needs_follow_up = state.get("needs_follow_up", False)
            
            # Get task type and instructions
            task_type, instructions = self._get_task_instructions(is_first_question, needs_follow_up)
            
            # Prepare messages
            system_prompt = self.get_prompt("SURVEY_CONVERSATION_SYSTEM_PROMPT")
            user_prompt_template = self.get_prompt("SURVEY_CONVERSATION_USER_PROMPT")
            
            user_prompt = user_prompt_template.format(
                survey_title=state.get("survey_title", ""),
                survey_goal=state.get("survey_goal", ""),
                all_themes=self._format_themes(themes),
                current_theme=current_theme,
                conversation_history=self._format_conversation_history(conversation_history),
                user_message=state.get("user_message", ""),
                task_type=task_type,
                instructions=instructions
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            agent_response = response.content
            
            logger.info(
                "Survey question generated",
                theme=current_theme,
                is_first=is_first_question
            )
            
            return {
                "agent_response": agent_response,
                "node_status": "conversation_complete"
            }

        except Exception as e:
            logger.error(f"Error in conversation agent: {e}")
            raise


conversation_agent = ConversationAgent()

