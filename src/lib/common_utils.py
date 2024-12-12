import logging
from typing import Any
import uuid


def setup_logging(name: str) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger(name)
    
    # Only add handler if it doesn't exist
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(logging.INFO)
    return logger


def safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    try:
        for key in keys:
            obj = obj[key]
        return obj
    except (KeyError, TypeError, IndexError):
        return default


def generate_id(prefix: str) -> str:
    """Generate a unique ID with a prefix.
    
    Args:
        prefix: Resource type prefix (e.g., 'ws', 'acc', 'path')
    Returns:
        A string in format '{prefix}-{uuid4}'
    """
    return f"{prefix}-{str(uuid.uuid4())}"

