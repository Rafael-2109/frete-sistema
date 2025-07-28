"""
Global exception handlers for the API
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail or "HTTP Error",
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors
    """
    errors = []
    for error in exc.errors():
        error_detail = {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        }
        errors.append(error_detail)
    
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "Invalid request data",
            "errors": errors,
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path)
        }
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database errors
    """
    logger.error(f"Database error on {request.url.path}: {str(exc)}")
    
    # Don't expose internal database errors in production
    detail = "Database operation failed"
    if hasattr(request.app.state, "settings") and request.app.state.settings.DEBUG:
        detail = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database Error",
            "detail": detail,
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path)
        }
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Handle value errors
    """
    logger.warning(f"Value error on {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Bad Request",
            "detail": str(exc),
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path)
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle any unhandled exceptions
    """
    logger.error(f"Unhandled exception on {request.url.path}: {type(exc).__name__}: {str(exc)}", exc_info=True)
    
    # Don't expose internal errors in production
    detail = "An unexpected error occurred"
    if hasattr(request.app.state, "settings") and request.app.state.settings.DEBUG:
        detail = f"{type(exc).__name__}: {str(exc)}"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": detail,
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path)
        }
    )


def register_exception_handlers(app: Any) -> None:
    """
    Register all exception handlers with the FastAPI app
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)