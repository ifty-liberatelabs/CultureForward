from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langsmith import traceable
import yaml

from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.state import SurveyGenerationState
from app.llm.schemas import SurveyThemeAgentResponse
from app.utils.files import get_project_root


class ThemeGeneratorAgent:
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
            pydantic_object=SurveyThemeAgentResponse
        )

    def get_prompt(self, name: str) -> str:
        """Load prompt from YAML file."""
        prompt_path = get_project_root() / "app" / "llm" / "prompts" / "theme_generator.yml"
        with open(prompt_path, 'r') as f:
            prompts = yaml.safe_load(f)
        return prompts[name]["prompt"]

    def _extract_state_variables(self, state: SurveyGenerationState):
        """Extract required variables from state."""
        return {
            "context": state.get("context", ""),
            "company_analysis": state.get("company_analysis", ""),
        }

    def _prepare_messages(self, state_vars):
        """Prepare messages for LLM with structured output."""
        system_prompt = self.get_prompt("THEME_GENERATOR_SYSTEM_PROMPT")
        user_prompt = self.get_prompt("THEME_GENERATOR_USER_PROMPT")

        # Add format instructions
        format_instructions = self.output_parser.get_format_instructions()

        user_message = user_prompt.format(
            context=state_vars["context"],
            company_analysis=state_vars["company_analysis"]
        )

        # Append format instructions
        user_message += f"\n\nFormat your response as valid JSON matching this schema:\n{format_instructions}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        return messages

    async def _generate_themes(self, messages):
        """Call OpenAI with fallback to generate themes with structured output."""
        try:
            response = await self.openai_with_fallback_model.ainvoke(messages)
            
            # Parse structured output
            parsed_response = self.output_parser.parse(response.content)
            
            # Convert string themes to dict format for API
            themes = [{"theme": theme} for theme in parsed_response.themes]
            
            return themes

        except Exception as e:
            logger.error(f"Error generating themes: {e}")
            raise Exception({
                "status": "Theme Generation Error",
                "code": "theme_generation_error",
                "message": "Agent unavailable. Please try again shortly."
            })

    @traceable(run_type="llm", name="Theme Generator Node")
    async def theme_generator_node(self, state: SurveyGenerationState):
        """
        Main node function that generates survey themes.
        
        This node:
        1. Takes company analysis and user context from state
        2. Uses OpenAI with Gemini fallback to generate 4-5 relevant survey themes
        3. Returns structured themes to state
        """
        logger.info(
            "Starting theme generation",
            context=state.get("context")
        )

        try:
            # Extract state variables
            state_vars = self._extract_state_variables(state)

            # Validate required inputs
            if not state_vars["company_analysis"]:
                raise ValueError("Company analysis is required for theme generation")

            # Prepare messages
            messages = self._prepare_messages(state_vars)

            # Generate themes
            themes = await self._generate_themes(messages)

            logger.info(
                "Theme generation completed successfully",
                theme_count=len(themes)
            )

            return {
                "themes": themes,
                "node_status": "theme_generation_complete"
            }

        except Exception as e:
            logger.error(f"Error in theme generator node: {e}")
            raise


theme_generator_agent = ThemeGeneratorAgent()

