"""
Logging configuration for the application
"""

import logging
from loguru import logger

def get_logger(name: str):
    """Get a logger instance"""
    return logger

# Configure loguru to work with standard logging
def setup_logging():
    """Setup application logging"""
    logger.add("logs/app.log", rotation="500 MB", level="INFO")
    
    # Intercept standard logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            logger_opt = logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(record.levelname, record.getMessage())
    
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
