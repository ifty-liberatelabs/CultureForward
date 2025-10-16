from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langsmith import traceable
import yaml

from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.state import SurveyThemeState
from app.llm.schemas.theme_refiner import ThemeRefinerResponse
from app.utils.files import get_project_root


class ThemeRefinerAgent:
    def __init__(self):
        self.model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            max_retries=3
        )
        self.gemini_model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0.3,
            max_retries=2
        )
        self.openai_with_fallback_model = self.model.with_fallbacks([self.gemini_model])
        self.output_parser = PydanticOutputParser(
            pydantic_object=ThemeRefinerResponse
        )

    def get_prompt(self, name: str) -> str:
        """Load prompt from YAML file."""
        prompt_path = get_project_root() / "app" / "llm" / "prompts" / "theme_refiner.yml"
        with open(prompt_path, 'r') as f:
            prompts = yaml.safe_load(f)
        return prompts[name]["prompt"]

    def _extract_state_variables(self, state: SurveyThemeState):
        """Extract required variables from state."""
        # Format chat history for prompt
        chat_history = state.get("chat_history") or []
        formatted_history = ""
        if chat_history and len(chat_history) > 0:
            # Exclude the latest user message (it's already in user_feedback)
            for msg in chat_history[:-1]:
                if msg and isinstance(msg, dict):
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    content = msg.get("content", "")
                    formatted_history += f"{role}: {content}\n\n"
        
        return {
            "title": state.get("title", ""),
            "goal": state.get("goal", ""),
            "company_url": state.get("company_url", ""),
            "company_analysis": state.get("company_analysis", ""),
            "current_themes": state.get("current_themes", []),
            "user_feedback": state.get("user_feedback", ""),
            "chat_history": formatted_history if formatted_history else "No previous conversation",
        }

    def _prepare_messages(self, state_vars):
        """Prepare messages for LLM with structured output."""
        system_prompt = self.get_prompt("THEME_REFINER_SYSTEM_PROMPT")
        user_prompt = self.get_prompt("THEME_REFINER_USER_PROMPT")

        # Format current themes as readable text
        themes_text = "\n".join([f"- {theme.get('theme', theme)}" for theme in state_vars["current_themes"]])
        current_theme_count = len(state_vars["current_themes"])

        user_message = user_prompt.format(
            title=state_vars["title"],
            goal=state_vars["goal"],
            company_url=state_vars["company_url"],
            company_analysis=state_vars["company_analysis"],
            current_themes=themes_text,
            current_theme_count=current_theme_count,
            user_feedback=state_vars["user_feedback"],
            chat_history=state_vars["chat_history"]
        )

        # Add format instructions
        format_instructions = self.output_parser.get_format_instructions()
        user_message += f"\n\nFormat your response as valid JSON matching this schema:\n{format_instructions}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        return messages

    async def _refine_themes(self, messages):
        """Call OpenAI with fallback to refine themes."""
        try:
            response = await self.openai_with_fallback_model.ainvoke(messages)
            
            # Parse structured output
            parsed_response = self.output_parser.parse(response.content)
            
            # Convert string themes to dict format for API
            themes = [{"theme": theme} for theme in parsed_response.themes]
            
            return themes, parsed_response.explanation

        except Exception as e:
            logger.error(f"Error refining themes: {e}")
            raise Exception({
                "status": "Theme Refinement Error",
                "code": "theme_refinement_error",
                "message": "Agent unavailable. Please try again shortly."
            })

    @traceable(run_type="llm", name="Theme Refiner Node")
    async def theme_refiner_node(self, state: SurveyThemeState):
        """Refine survey themes based on user feedback."""
        logger.info(
            "Starting theme refinement",
            user_feedback=state.get("user_feedback")
        )

        try:
            # Extract state variables
            state_vars = self._extract_state_variables(state)

            # Validate required inputs
            if not state_vars["current_themes"]:
                raise ValueError("Current themes are required for refinement")
            if not state_vars["user_feedback"]:
                raise ValueError("User feedback is required for refinement")

            # Prepare messages
            messages = self._prepare_messages(state_vars)

            # Refine themes
            updated_themes, explanation = await self._refine_themes(messages)

            logger.info(
                "Theme refinement completed successfully",
                theme_count=len(updated_themes)
            )

            # Add assistant response to chat history
            existing_history = state.get("chat_history") or []
            
            return {
                "themes": updated_themes,
                "explanation": explanation,
                "chat_history": existing_history + [
                    {
                        "role": "assistant",
                        "content": explanation,
                        "themes": updated_themes
                    }
                ],
                "node_status": "theme_refinement_complete"
            }

        except Exception as e:
            logger.error(f"Error in theme refiner node: {e}")
            raise


theme_refiner_agent = ThemeRefinerAgent()

