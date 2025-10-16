from langchain_google_genai import ChatGoogleGenerativeAI
from google.ai.generativelanguage_v1beta.types import Tool as GenAITool
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
import yaml

from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.state import SurveyThemeState
from app.utils.files import get_project_root


class CompanyAnalyzerAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0,
            model_kwargs={"thinking_budget": 0},
            max_retries=3
        )

    def get_prompt(self, name: str) -> str:
        """Load prompt from YAML file."""
        prompt_path = get_project_root() / "app" / "llm" / "prompts" / "company_analyzer.yml"
        with open(prompt_path, 'r') as f:
            prompts = yaml.safe_load(f)
        return prompts[name]["prompt"]

    def _extract_state_variables(self, state: SurveyThemeState):
        """Extract required variables from state."""
        return {
            "company_url": state.get("company_url", ""),
        }

    def _prepare_messages(self, state_vars):
        """Prepare messages for LLM."""
        system_prompt = self.get_prompt("COMPANY_ANALYZER_SYSTEM_PROMPT")
        user_prompt = self.get_prompt("COMPANY_ANALYZER_USER_PROMPT")

        user_message = user_prompt.format(
            company_url=state_vars["company_url"]
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        return messages

    async def _generate_analysis(self, messages):
        """Call Gemini with Google Search tools."""
        try:
            response = await self.llm.ainvoke(
                messages,
                tools=[GenAITool(google_search={})],
            )
            return response.content
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise Exception({
                "status": "Gemini Error",
                "code": "gemini_error",
                "message": str(e)
            })

    @traceable(run_type="llm", name="Company Analyzer Node")
    async def company_analyzer_node(self, state: SurveyThemeState):
        """Analyze company using Gemini with Google Search."""
        logger.info(
            "Starting company analysis",
            company_url=state.get("company_url")
        )

        try:
            # Extract state variables
            state_vars = self._extract_state_variables(state)

            # Prepare messages
            messages = self._prepare_messages(state_vars)

            # Generate analysis
            analysis = await self._generate_analysis(messages)

            logger.info("Company analysis completed successfully")

            return {
                "company_analysis": analysis,
                "node_status": "company_analysis_complete"
            }

        except Exception as e:
            logger.error(f"Error in company analyzer node: {e}")
            raise


company_analyzer_agent = CompanyAnalyzerAgent()

