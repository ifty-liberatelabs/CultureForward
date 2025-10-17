from fastapi import HTTPException
from typing import Optional


class AgentException(HTTPException):
    """
    Custom exception for agent errors with structured error responses.
    """
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        status: Optional[str] = None
    ):
        detail = {
            "status": status or self._get_default_status(status_code),
            "code": error_code,
            "message": message
        }
        super().__init__(status_code=status_code, detail=detail)
    
    @staticmethod
    def _get_default_status(status_code: int) -> str:
        status_map = {
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
            503: "Service Unavailable"
        }
        return status_map.get(status_code, "Error")


class GeminiError(AgentException):
    """Exception for Gemini API errors"""
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            error_code="gemini_error",
            message=message,
            status="Gemini Error"
        )


class ThemeGenerationError(AgentException):
    """Exception for theme generation errors"""
    def __init__(self, message: str = "Agent unavailable. Please try again shortly."):
        super().__init__(
            status_code=500,
            error_code="theme_generation_error",
            message=message,
            status="Theme Generation Error"
        )


class ThemeRefinementError(AgentException):
    """Exception for theme refinement errors"""
    def __init__(self, message: str = "Agent unavailable. Please try again shortly."):
        super().__init__(
            status_code=500,
            error_code="theme_refinement_error",
            message=message,
            status="Theme Refinement Error"
        )


class DatabaseConnectionError(AgentException):
    """Exception for database connection errors"""
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            error_code="db_connection_error",
            message=message,
            status="Database Connection Error"
        )


class SessionNotFoundError(AgentException):
    """Exception for session not found errors"""
    def __init__(self, message: str = "Survey session not found. Initialize first with /init endpoint."):
        super().__init__(
            status_code=404,
            error_code="session_not_found",
            message=message,
            status="Session Not Found"
        )


class ChatError(AgentException):
    """Generic exception for chat errors"""
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            error_code="chat_error",
            message=message,
            status="Chat Error"
        )
