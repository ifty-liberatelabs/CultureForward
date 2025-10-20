from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import OutputFixingParser
from langchain_core.prompts.prompt import PromptTemplate
from langsmith import traceable
import yaml

from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.survey_state import ConversationalSurveyState
from app.llm.schemas import SurveyEvaluationResponse
from app.utils.files import get_project_root


class EvaluationAgent:
    def __init__(self):
        self.model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,
            max_retries=3
        )
        self.gemini_model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0,
            max_retries=2
        )
        self.llm = self.model.with_fallbacks([self.gemini_model])
        
        # Output parser with fixing capability
        self.output_parser_fixer_llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0
        )
        self.output_fixing_parser_prompt = PromptTemplate.from_template(
            self._get_output_fixing_prompt()
        )
        self.parser = PydanticOutputParser(pydantic_object=SurveyEvaluationResponse)
        self.fix_parser = OutputFixingParser.from_llm(
            parser=self.parser,
            llm=self.output_parser_fixer_llm,
            prompt=self.output_fixing_parser_prompt,
            max_retries=3
        )
        self.chain = self.llm | self.fix_parser

    def get_prompt(self, name: str) -> str:
        """Load prompt from YAML file."""
        prompt_path = get_project_root() / "app" / "llm" / "prompts" / "survey_evaluation.yml"
        with open(prompt_path, 'r') as f:
            prompts = yaml.safe_load(f)
        return prompts[name]["prompt"]
    
    def _get_output_fixing_prompt(self) -> str:
        """Load output fixing parser prompt"""
        prompt_path = get_project_root() / "app" / "llm" / "prompts" / "output_fixing_parser.yml"
        with open(prompt_path, 'r') as f:
            config = yaml.safe_load(f)
        return config["prompt"]

    def _format_conversation_history(self, history: list) -> str:
        """Format conversation history for prompt"""
        if not history:
            return "No previous conversation"
        
        formatted = []
        for msg in history:
            role = "Assistant" if msg["role"] == "assistant" else "User"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def _format_themes(self, themes: list) -> str:
        """Format all themes as a readable list"""
        return "\n".join([f"{i}. {theme['theme']}" for i, theme in enumerate(themes)])

    def _get_discussed_themes(self, theme_responses: dict, themes: list) -> str:
        """Format list of already discussed themes"""
        discussed = []
        for i, theme in enumerate(themes):
            theme_name = theme["theme"]
            if theme_name in theme_responses and theme_responses[theme_name].get("complete"):
                discussed.append(f"- Theme {i}: {theme_name} (Complete)")
        
        if not discussed:
            return "No themes discussed yet"
        return "\n".join(discussed)


    @traceable(run_type="llm", name="Survey Evaluation Agent")
    async def evaluation_node(self, state: ConversationalSurveyState):
        """Evaluate user responses and determine conversation flow"""
        logger.info(
            "Evaluating survey response",
            theme_index=state.get("current_theme_index")
        )

        try:
            # Extract state variables
            current_theme_index = state.get("current_theme_index", 0)
            themes = state.get("themes", [])
            current_theme = themes[current_theme_index]["theme"]
            user_message = state.get("user_message", "")
            conversation_history = state.get("conversation_history", [])
            theme_responses = state.get("theme_responses", {})
            
            # Prepare messages
            system_prompt = self.get_prompt("SURVEY_EVALUATION_SYSTEM_PROMPT")
            user_prompt_template = self.get_prompt("SURVEY_EVALUATION_USER_PROMPT")
            format_instructions = self.parser.get_format_instructions()
            
            user_prompt = user_prompt_template.format(
                survey_title=state.get("survey_title", ""),
                survey_goal=state.get("survey_goal", ""),
                all_themes=self._format_themes(themes),
                current_theme=current_theme,
                current_theme_index=current_theme_index,
                discussed_themes=self._get_discussed_themes(theme_responses, themes),
                user_answer=user_message,
                conversation_history=self._format_conversation_history(conversation_history[:-1] if conversation_history else [])
            )
            
            user_prompt += f"\n\nFormat your response as valid JSON matching this schema:\n{format_instructions}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Get evaluation
            evaluation = await self.chain.ainvoke(messages)
            
            # Check if survey is already complete
            survey_complete = state.get("survey_complete", False)
            
            if survey_complete:
                # Survey is complete, no matter what user sends
                all_themes_complete = True
                next_theme_index = -1
            elif all_themes_complete and current_theme_index == -2:
                # User provided feedback, mark survey as complete
                theme_responses["feedback"] = {
                    "answer": user_message,
                    "complete": True
                }
                survey_complete = True
                next_theme_index = -1
            elif evaluation.is_answer_complete and not evaluation.needs_follow_up:
                # Mark current theme as complete
                theme_responses[current_theme] = {
                    "answer": user_message,
                    "complete": True
                }
                
                # Move to next theme
                next_theme_index = current_theme_index + 1
                
                # Check if we've completed all themes
                if next_theme_index >= len(themes):
                    all_themes_complete = True
                    next_theme_index = -2  # Special index for feedback phase
                else:
                    all_themes_complete = False
            else:
                # Current theme needs follow-up, stay on same theme
                if current_theme not in theme_responses:
                    theme_responses[current_theme] = {
                        "answer": user_message,
                        "complete": False,
                        "follow_ups": [user_message]
                    }
                else:
                    theme_responses[current_theme]["follow_ups"].append(user_message)
                
                next_theme_index = current_theme_index
                all_themes_complete = False
                survey_complete = False
            
            # Log completed themes
            completed_themes = [theme_name for theme_name, data in theme_responses.items() if data.get("complete")]
            current_theme_name = themes[next_theme_index]["theme"] if next_theme_index >= 0 and next_theme_index < len(themes) else "Survey Complete"
            
            logger.info(
                "Response evaluated",
                is_complete=evaluation.is_answer_complete,
                needs_follow_up=evaluation.needs_follow_up,
                completed_themes=completed_themes,
                current_theme=current_theme_name,
                all_complete=all_themes_complete
            )
            
            return {
                "is_answer_complete": evaluation.is_answer_complete,
                "needs_follow_up": evaluation.needs_follow_up,
                "next_theme_index": next_theme_index,
                "theme_responses": theme_responses,
                "all_themes_complete": all_themes_complete,
                "survey_complete": survey_complete,
                "node_status": "evaluation_complete"
            }

        except Exception as e:
            logger.error(f"Error in evaluation agent: {e}")
            raise


evaluation_agent = EvaluationAgent()

