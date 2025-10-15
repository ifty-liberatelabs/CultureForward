from fastapi import APIRouter, HTTPException
from langsmith.run_helpers import traceable
from datetime import datetime

from app.api.v1.schemas import SurveyThemeInput, SurveyThemeResponse, error_response
from app.core.logging import logger
from app.llm.workflow.graph import survey_theme_graph
from app.utils.errors import identify_error


router = APIRouter()


@router.post("/generate_themes", response_model=SurveyThemeResponse, responses={400: error_response(400), 500: error_response(500)})
@traceable(name="Generate Survey Themes")
async def generate_survey_themes(survey_input: SurveyThemeInput):
    try:
        logger.info("Starting survey theme generation", title=survey_input.title, goal=survey_input.goal)

        graph = survey_theme_graph.compile_graph()
        graph.name = "Survey Theme Generator"

        graph_input = {
            "context": survey_input.goal,
            "company_url": str(survey_input.company_url)
        }

        result = await graph.ainvoke(graph_input)

        logger.info("Survey themes generated", theme_count=len(result.get("themes", [])))

        return {
            "themes": result["themes"],
            "created_at": datetime.now()
        }

    except HTTPException as e:
        logger.error(f"HTTP Error -> {e}")
        raise e

    except Exception as e:
        logger.error(f"Error -> {e}")
        e_str = str(e)
        
        if identify_error(e):
            raise HTTPException(status_code=500, detail=eval(e_str))
        else:
            raise HTTPException(status_code=500, detail={
                "status": "Survey Theme Generation Error",
                "code": "theme_generation_error",
                "message": str(e)
            })

