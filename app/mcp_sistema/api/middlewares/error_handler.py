"""
Error handling middleware
"""
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from typing import Callable

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling exceptions and returning proper error responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
            
        except ValueError as e:
            # Handle validation errors
            logger.warning(f"Validation error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation Error",
                    "detail": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except PermissionError as e:
            # Handle permission errors
            logger.warning(f"Permission error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Permission Denied",
                    "detail": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except FileNotFoundError as e:
            # Handle not found errors
            logger.warning(f"Not found error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": "Not Found",
                    "detail": str(e),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
        except Exception as e:
            # Handle all other errors
            logger.error(f"Unhandled error: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", None)
                }
            )