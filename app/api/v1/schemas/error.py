from pydantic import BaseModel

class ErrorResponse(BaseModel):
    detail: dict[str, str]


def error_response(code: int):
    if code == 400:
        return {
            "model": ErrorResponse,
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "status": "Bad Request",
                            "code": "validation_error",
                            "message": "Invalid input provided"
                        }
                    }
                }
            }
        }
    elif code == 404:
        return {
            "model": ErrorResponse,
            "description": "Not Found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "status": "Not Found",
                            "code": "not_found",
                            "message": "Resource not found"
                        }
                    }
                }
            }
        }
    else:
        return {
            "model": ErrorResponse,
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "status": "Internal Server Error",
                            "code": "gemini_error/unknown_error",
                            "message": "Internal Server Error"
                        }
                    }
                }
            }
        }

