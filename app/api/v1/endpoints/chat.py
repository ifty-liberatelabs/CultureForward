from fastapi import APIRouter, HTTPException
from langsmith.run_helpers import traceable
from datetime import datetime
from uuid import uuid4

from app.api.v1.schemas import (
    InitInput,
    InitResponse,
    ChatInput,
    ChatResponse,
    error_response
)
from app.core.logging import logger
from app.llm.workflow.graph import survey_theme_graph
from app.utils.memory import survey_memory_store
from app.utils.errors import identify_error


router = APIRouter()


@router.post("/init", response_model=InitResponse)
async def initialize_survey(init_input: InitInput):
    survey_id = uuid4()
    
    # Store init data for later use
    survey_memory_store.store_init_data(survey_id, {
        "title": init_input.title,
        "goal": init_input.goal,
        "company_url": str(init_input.company_url)
    })
    
    logger.info(
        "Survey session initialized",
        survey_id=str(survey_id),
        title=init_input.title
    )
    
    return {
        "survey_id": survey_id,
        "created_at": datetime.now()
    }


@router.post("/chat", response_model=ChatResponse, responses={404: error_response(404), 500: error_response(500)})
@traceable(name="Refine Survey Themes")
async def chat(chat_input: ChatInput):
    try:
        logger.info(
            "Processing theme refinement",
            survey_id=str(chat_input.survey_id),
            message=chat_input.message
        )

        # Get checkpointer and compile graph
        checkpointer = survey_memory_store.get_checkpointer()
        graph = survey_theme_graph.compile_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": str(chat_input.survey_id)}}
        
        # Try to get current state
        try:
            current_state = await graph.aget_state(config)
            state_values = current_state.values if current_state.values else {}
        except Exception:
            state_values = {}
        
        # Build input for graph based on whether themes exist in state
        if not state_values.get("themes"):
            # First chat: generate initial themes using stored init data
            init_data = survey_memory_store.get_init_data(chat_input.survey_id)
            
            if not init_data:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "status": "Session Not Found",
                        "code": "session_not_found",
                        "message": "Survey session not found. Initialize first with /init endpoint."
                    }
                )
            
            logger.info(
                "First chat - generating initial themes",
                survey_id=str(chat_input.survey_id),
                title=init_data["title"]
            )
            graph.name = "Survey Theme Generator"
            
            graph_input = {
                "title": init_data["title"],
                "goal": init_data["goal"],
                "company_url": init_data["company_url"],
                "current_themes": None,
                "user_feedback": None,
                "chat_history": [{"role": "user", "content": chat_input.message, "themes": None}]
            }
        else:
            # Subsequent chats: refine existing themes using stored state
            logger.info(
                "Refining existing themes",
                survey_id=str(chat_input.survey_id)
            )
            graph.name = "Survey Theme Refiner"
            
            existing_history = state_values.get("chat_history", [])
            
            graph_input = {
                "title": state_values["title"],
                "goal": state_values["goal"],
                "company_url": state_values["company_url"],
                "company_analysis": state_values.get("company_analysis", ""),
                "current_themes": state_values["themes"],
                "user_feedback": chat_input.message,
                "chat_history": existing_history + [{"role": "user", "content": chat_input.message, "themes": state_values["themes"]}]
            }

        result = await graph.ainvoke(graph_input, config=config)
        if not state_values.get("themes"):
            init_data = survey_memory_store.get_init_data(chat_input.survey_id)
            response_message = f"I've analyzed {init_data['company_url']} and created {len(result['themes'])} survey themes based on your goal."
            
            logger.info(
                "Initial themes generated",
                survey_id=str(chat_input.survey_id),
                theme_count=len(result["themes"])
            )
        else:
            response_message = result.get("explanation", "Themes have been refined.")
            
            logger.info(
                "Themes refined",
                survey_id=str(chat_input.survey_id),
                theme_count=len(result["themes"])
            )

        return {
            "survey_id": chat_input.survey_id,
            "themes": result["themes"],
            "message": response_message,
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
                "status": "Chat Error",
                "code": "chat_error",
                "message": str(e)
            })
