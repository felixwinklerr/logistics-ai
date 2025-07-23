"""Exception handling middleware"""
import traceback
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.core.config import settings


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Custom exception handling middleware"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self.handle_exception(request, exc)
    
    async def handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle different types of exceptions"""
        
        # HTTP exceptions (including FastAPI HTTPException)
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            return await self.handle_http_exception(request, exc)
        
        # Validation errors
        if isinstance(exc, (RequestValidationError, ValidationError)):
            return await self.handle_validation_error(request, exc)
        
        # Database errors
        if isinstance(exc, SQLAlchemyError):
            return await self.handle_database_error(request, exc)
        
        # All other exceptions
        return await self.handle_generic_error(request, exc)
    
    async def handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions"""
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "path": str(request.url.path)
                }
            }
        )
    
    async def handle_validation_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle validation errors"""
        logger.warning(f"Validation Error: {exc} - Path: {request.url.path}")
        
        if isinstance(exc, RequestValidationError):
            errors = []
            for error in exc.errors():
                errors.append({
                    "field": " -> ".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"]
                })
            
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "type": "validation_error",
                        "code": 422,
                        "message": "Request validation failed",
                        "path": str(request.url.path),
                        "details": errors
                    }
                }
            )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "validation_error",
                    "code": 422,
                    "message": str(exc),
                    "path": str(request.url.path)
                }
            }
        )
    
    async def handle_database_error(self, request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle database errors"""
        logger.error(f"Database Error: {exc} - Path: {request.url.path}")
        
        # Don't expose internal database errors in production
        if settings.environment == "production":
            message = "A database error occurred. Please try again later."
        else:
            message = str(exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "database_error",
                    "code": 500,
                    "message": message,
                    "path": str(request.url.path)
                }
            }
        )
    
    async def handle_generic_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions"""
        logger.error(f"Unhandled Exception: {exc} - Path: {request.url.path}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Don't expose internal errors in production
        if settings.environment == "production":
            message = "An internal server error occurred. Please try again later."
        else:
            message = str(exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "internal_error",
                    "code": 500,
                    "message": message,
                    "path": str(request.url.path)
                }
            }
        )


# Exception handler functions for specific cases
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "code": 422,
                "message": "Request validation failed",
                "path": str(request.url.path),
                "details": errors
            }
        }
    ) 