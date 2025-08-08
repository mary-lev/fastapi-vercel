import logging
import sys
import os
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up application logging configuration
    """
    # Check if running in a serverless environment (like Vercel)
    is_serverless = os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("FUNCTIONS_WORKER_RUNTIME")
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Only add file handler in non-serverless environments
    if not is_serverless:
        try:
            # Create logs directory if it doesn't exist
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            handlers.append(logging.FileHandler(log_dir / "app.log"))
        except (OSError, PermissionError):
            # If we can't create the logs directory, just use stdout
            pass

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    logger = logging.getLogger("fastapi_app")
    return logger


# Create a global logger instance
logger = setup_logging()
