from fastapi import APIRouter, Request
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
from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.graph import survey_theme_graph
from app.utils.memory import survey_memory_store
from app.utils.errors import (
    SessionNotFoundError,
    ChatError,
    GeminiError,
    ThemeGenerationError,
    ThemeRefinementError
)
from app.db.async_crud import AsyncSurveyCRUD, AsyncMessageCRUD


router = APIRouter()


async def _survey_exists_in_db(survey_id: str, db_manager) -> bool:
    """Check if survey exists in database"""
    try:
        survey_crud = AsyncSurveyCRUD(db_manager)
        survey = await survey_crud.get_by_id(survey_id)
        return survey is not None
    except Exception as e:
        logger.warning(f"Error checking survey existence in database: {e}")
        return False


@router.post("/init", response_model=InitResponse)
async def initialize_survey(init_input: InitInput, request: Request):
    survey_id = uuid4()
    
    # Store init data for later use
    survey_memory_store.store_init_data(survey_id, {
        "title": init_input.title,
        "goal": init_input.goal,
        "company_url": str(init_input.company_url)
    })
    
    # Save to database if DB_SAVE is enabled
    if settings.DB_SAVE and hasattr(request.state, "db_manager"):
        try:
            survey_crud = AsyncSurveyCRUD(request.state.db_manager)
            db_survey = await survey_crud.create(
                title=init_input.title,
                goal=init_input.goal,
                company_url=str(init_input.company_url),
                themes=[]
            )
            # Use the database-generated survey_id
            if db_survey:
                from uuid import UUID
                survey_id = UUID(db_survey["id"])
                # Update memory store with database survey_id
                survey_memory_store.store_init_data(survey_id, {
                    "title": init_input.title,
                    "goal": init_input.goal,
                    "company_url": str(init_input.company_url)
                })
                logger.info("Survey saved to database", survey_id=str(survey_id))
            else:
                logger.warning("Failed to create survey in database - using memory-only mode")
        except Exception as e:
            logger.warning(f"Failed to save survey to database: {e}")
    
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
async def chat(chat_input: ChatInput, request: Request):
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
        except Exception as e:
            logger.warning(f"Failed to retrieve graph state: {e}")
            state_values = {}
        
        # Build input for graph based on whether themes exist in state
        if not state_values.get("themes"):
            # First chat: generate initial themes using stored init data
            init_data = survey_memory_store.get_init_data(chat_input.survey_id)
            
            if not init_data:
                raise SessionNotFoundError()
            
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
                "themes": None,
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
                "themes": state_values["themes"],
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

        # Save messages and update themes in database if DB_SAVE is enabled
        if settings.DB_SAVE and hasattr(request.state, "db_manager"):
            # Check if survey exists in database
            survey_exists = await _survey_exists_in_db(str(chat_input.survey_id), request.state.db_manager)
            
            if survey_exists:
                try:
                    message_crud = AsyncMessageCRUD(request.state.db_manager)
                    survey_crud = AsyncSurveyCRUD(request.state.db_manager)
                    
                    # Save user message
                    await message_crud.create(
                        role="user",
                        content=chat_input.message,
                        survey_id=str(chat_input.survey_id)
                    )
                    
                    # Save AI response message
                    await message_crud.create(
                        role="assistant",
                        content=response_message,
                        survey_id=str(chat_input.survey_id)
                    )
                    
                    # Update themes in survey table
                    await survey_crud.update_themes(
                        survey_id=str(chat_input.survey_id),
                        themes=result["themes"]
                    )
                    
                    logger.info("Messages and themes saved to database", survey_id=str(chat_input.survey_id))
                except Exception as e:
                    logger.warning(f"Failed to save to database: {e}")
            else:
                logger.debug("Survey not in database, skipping database save", survey_id=str(chat_input.survey_id))

        return {
            "survey_id": chat_input.survey_id,
            "themes": result["themes"],
            "message": response_message,
            "created_at": datetime.now()
        }

    except SessionNotFoundError:
        raise
    
    except (GeminiError, ThemeGenerationError, ThemeRefinementError) as e:
        logger.error(f"Agent Error: {e}")
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise ChatError(str(e))
