from fastapi import APIRouter, Request
from langsmith.run_helpers import traceable
from datetime import datetime
from uuid import UUID

from app.api.v1.schemas.survey import (
    InitSurveyInput,
    InitSurveyResponse,
    SurveyChatInput,
    SurveyChatResponse,
    SurveyThreadResponse
)
from app.api.v1.schemas.error import error_response
from app.core.config import settings
from app.core.logging import logger
from app.llm.workflow.survey_graph import conversational_survey_graph
from app.utils.memory import survey_memory_store
from app.utils.errors import SessionNotFoundError, ChatError
from app.db.async_crud import AsyncSurveyCRUD, AsyncThreadCRUD, AsyncSurveyMessageCRUD


router = APIRouter()


async def _get_survey_context(survey_id: str, db_manager) -> dict:
    """Get survey details from database"""
    try:
        survey_crud = AsyncSurveyCRUD(db_manager)
        survey = await survey_crud.get_by_id(survey_id)
        return survey
    except Exception as e:
        logger.error(f"Error fetching survey: {e}")
        return None


@router.post("/init", response_model=InitSurveyResponse, responses={404: error_response(404), 500: error_response(500)})
async def init_survey(survey_input: InitSurveyInput, request: Request):
    """Initialize a new survey thread - creates thread and returns thread_id"""
    try:
        logger.info(
            "Initializing new survey thread",
            survey_id=str(survey_input.survey_id)
        )
        
        # Get survey context from database
        if not settings.DB_SAVE or not hasattr(request.state, "db_manager"):
            raise ChatError("Database is required for conversational surveys")
        
        survey = await _get_survey_context(str(survey_input.survey_id), request.state.db_manager)
        
        if not survey:
            raise SessionNotFoundError("Survey not found")
        
        # Validate survey has themes
        if not survey.get("themes") or len(survey["themes"]) == 0:
            raise ChatError("Survey has no themes defined")
        
        # Create a new thread
        thread_crud = AsyncThreadCRUD(request.state.db_manager)
        thread = await thread_crud.create(survey_id=str(survey_input.survey_id))
        
        if not thread:
            raise ChatError("Failed to create survey thread")
        
        thread_id = UUID(thread["id"])
        
        logger.info(
            "Survey thread initialized",
            thread_id=str(thread_id),
            survey_id=str(survey_input.survey_id)
        )
        
        return {
            "thread_id": thread_id,
            "survey_id": survey_input.survey_id,
            "survey_title": survey["title"],
            "created_at": datetime.now()
        }
    
    except SessionNotFoundError:
        raise
    except ChatError:
        raise
    except Exception as e:
        logger.error(f"Error initializing survey: {e}")
        raise ChatError(str(e))


@router.post("/chat", response_model=SurveyChatResponse, responses={404: error_response(404), 500: error_response(500)})
@traceable(name="Survey Chat")
async def survey_chat(chat_input: SurveyChatInput, request: Request):
    """Chat with the survey agent - send user message and get agent's question"""
    try:
        logger.info(
            "Processing survey chat",
            thread_id=str(chat_input.thread_id),
            message=chat_input.message
        )
        
        if not settings.DB_SAVE or not hasattr(request.state, "db_manager"):
            raise ChatError("Database is required for conversational surveys")
        
        # Verify thread exists and get its context
        thread_crud = AsyncThreadCRUD(request.state.db_manager)
        thread = await thread_crud.get_by_id(str(chat_input.thread_id))
        
        if not thread:
            raise SessionNotFoundError("Survey thread not found")
        
        # Get survey context
        survey = await _get_survey_context(thread["survey_id"], request.state.db_manager)
        if not survey:
            raise SessionNotFoundError("Survey not found")
        
        # Save user message to database
        message_crud = AsyncSurveyMessageCRUD(request.state.db_manager)
        await message_crud.create(
            role="user",
            content=chat_input.message,
            thread_id=str(chat_input.thread_id)
        )
        
        # Get conversation history from database
        messages = await message_crud.get_by_thread_id(str(chat_input.thread_id))
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
        
        # Get checkpointer and compile graph
        checkpointer = survey_memory_store.get_checkpointer()
        graph = conversational_survey_graph.compile_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": str(chat_input.thread_id)}}
        
        # Try to get current state
        try:
            current_state = await graph.aget_state(config)
            state_values = current_state.values if current_state.values else {}
        except Exception as e:
            logger.warning(f"Failed to retrieve graph state: {e}")
            state_values = {}
        
        # Build graph input
        graph_input = {
            "survey_id": thread["survey_id"],
            "thread_id": str(chat_input.thread_id),
            "survey_title": survey["title"],
            "survey_goal": survey["goal"],
            "themes": survey["themes"],
            "user_message": chat_input.message,
            "conversation_history": conversation_history,
            "current_theme_index": state_values.get("current_theme_index", 0),
            "theme_responses": state_values.get("theme_responses", {}),
            "is_answer_complete": False,
            "needs_follow_up": False,
            "next_theme_index": None,
            "agent_response": "",
            "all_themes_complete": state_values.get("all_themes_complete", False),
            "survey_complete": state_values.get("survey_complete", False),
            "node_status": ""
        }
        
        # Run graph
        result = await graph.ainvoke(graph_input, config=config)
        
        agent_response = result["agent_response"]
        all_themes_complete = result.get("all_themes_complete", False)
        survey_complete = result.get("survey_complete", False)
        
        # Extract completed themes (exclude feedback)
        theme_responses = result.get("theme_responses", {})
        completed_theme = [theme_name for theme_name, data in theme_responses.items() 
                          if data.get("complete") and theme_name != "feedback"]
        
        # Get current theme - use next_theme_index from evaluation (the theme being asked NOW)
        next_theme_index = result.get("next_theme_index")
        if survey_complete or next_theme_index is None or next_theme_index == -1:
            current_theme = None
        elif next_theme_index == -2:  # Feedback phase
            current_theme = None  # All themes done, asking for feedback
        else:
            current_theme = survey["themes"][next_theme_index]["theme"]
        
        # Save agent response to database
        await message_crud.create(
            role="assistant",
            content=agent_response,
            thread_id=str(chat_input.thread_id)
        )
        
        logger.info(
            "Survey chat processed",
            thread_id=str(chat_input.thread_id),
            all_themes_complete=all_themes_complete,
            survey_complete=survey_complete
        )
        
        return {
            "thread_id": chat_input.thread_id,
            "message": agent_response,
            "completed_theme": completed_theme,
            "current_theme": current_theme,
            "all_themes_complete": all_themes_complete,
            "survey_complete": survey_complete,
            "created_at": datetime.now()
        }
    
    except SessionNotFoundError:
        raise
    except ChatError:
        raise
    except Exception as e:
        logger.error(f"Error processing survey chat: {e}")
        raise ChatError(str(e))


@router.get("/thread/{thread_id}", response_model=SurveyThreadResponse, responses={404: error_response(404), 500: error_response(500)})
async def get_survey_thread(thread_id: UUID, request: Request):
    """Get survey thread with full conversation history"""
    try:
        logger.info("Fetching survey thread", thread_id=str(thread_id))
        
        if not settings.DB_SAVE or not hasattr(request.state, "db_manager"):
            raise ChatError("Database is required for conversational surveys")
        
        # Get thread
        thread_crud = AsyncThreadCRUD(request.state.db_manager)
        thread = await thread_crud.get_by_id(str(thread_id))
        
        if not thread:
            raise SessionNotFoundError("Survey thread not found")
        
        # Get survey
        survey = await _get_survey_context(thread["survey_id"], request.state.db_manager)
        if not survey:
            raise SessionNotFoundError("Survey not found")
        
        # Get messages
        message_crud = AsyncSurveyMessageCRUD(request.state.db_manager)
        messages = await message_crud.get_by_thread_id(str(thread_id))
        
        logger.info("Survey thread fetched", thread_id=str(thread_id))
        
        return {
            "thread_id": thread_id,
            "survey_id": UUID(thread["survey_id"]),
            "survey_title": survey["title"],
            "created_at": thread["created_at"],
            "messages": messages
        }
    
    except SessionNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching survey thread: {e}")
        raise ChatError(str(e))

