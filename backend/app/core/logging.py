"""Logging configuration and utilities for the application"""
import logging
import sys
from typing import Optional
from pathlib import Path

from loguru import logger as loguru_logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json: bool = False,
    enable_correlation_id: bool = True
) -> None:
    """
    Setup application logging with loguru
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        enable_json: Whether to use JSON formatting
        enable_correlation_id: Whether to include correlation IDs
    """
    # Remove default loguru handler
    loguru_logger.remove()
    
    # Console handler with colored output
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    if enable_correlation_id:
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<blue>{extra[correlation_id]}</blue> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    loguru_logger.add(
        sys.stdout,
        format=console_format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        if enable_json:
            file_format = "{time} | {level} | {name} | {function} | {line} | {message}"
        
        loguru_logger.add(
            log_file,
            format=file_format,
            level=level,
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            serialize=enable_json,
            backtrace=True,
            diagnose=True
        )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    # Create a standard library logger that forwards to loguru
    stdlib_logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if not stdlib_logger.handlers:
        # Create a handler that forwards to loguru
        class LoguruHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level if it exists
                try:
                    level = loguru_logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                # Find caller from where the logging call originated
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                loguru_logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )
        
        stdlib_logger.addHandler(LoguruHandler())
        stdlib_logger.setLevel(logging.DEBUG)
        
        # Prevent propagation to avoid duplicate logs
        stdlib_logger.propagate = False
    
    return stdlib_logger


def add_correlation_id(correlation_id: str) -> None:
    """
    Add correlation ID to logger context
    
    Args:
        correlation_id: Unique identifier for request/operation correlation
    """
    loguru_logger.configure(extra={"correlation_id": correlation_id})


def remove_correlation_id() -> None:
    """Remove correlation ID from logger context"""
    loguru_logger.configure(extra={"correlation_id": ""})


# Performance logging utilities
def log_performance(operation_name: str):
    """
    Decorator for logging performance metrics
    
    Args:
        operation_name: Name of the operation being measured
    """
    def decorator(func):
        import time
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                logger.info(f"{operation_name} completed in {execution_time:.2f}ms")
                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"{operation_name} failed after {execution_time:.2f}ms: {str(e)}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                logger.info(f"{operation_name} completed in {execution_time:.2f}ms")
                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                logger.error(f"{operation_name} failed after {execution_time:.2f}ms: {str(e)}")
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Structured logging helpers
def log_order_event(logger: logging.Logger, order_id: str, event: str, **kwargs) -> None:
    """
    Log order-related events with structured data
    
    Args:
        logger: Logger instance
        order_id: Order identifier
        event: Event description
        **kwargs: Additional event data
    """
    event_data = {
        "order_id": order_id,
        "event": event,
        **kwargs
    }
    logger.info(f"Order Event: {event}", extra={"event_data": event_data})


def log_ai_processing(logger: logging.Logger, document_id: str, provider: str, confidence: float, **kwargs) -> None:
    """
    Log AI document processing events
    
    Args:
        logger: Logger instance
        document_id: Document identifier
        provider: AI provider used
        confidence: Processing confidence score
        **kwargs: Additional processing data
    """
    processing_data = {
        "document_id": document_id,
        "ai_provider": provider,
        "confidence": confidence,
        **kwargs
    }
    logger.info(f"AI Processing completed with confidence {confidence:.2%}", extra={"processing_data": processing_data})


def log_subcontractor_event(logger: logging.Logger, subcontractor_id: str, event: str, **kwargs) -> None:
    """
    Log subcontractor-related events
    
    Args:
        logger: Logger instance
        subcontractor_id: Subcontractor identifier
        event: Event description
        **kwargs: Additional event data
    """
    event_data = {
        "subcontractor_id": subcontractor_id,
        "event": event,
        **kwargs
    }
    logger.info(f"Subcontractor Event: {event}", extra={"event_data": event_data})


# Initialize logging on module import
setup_logging() 