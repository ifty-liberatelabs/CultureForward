import structlog
import logging
from typing import Any, Dict
from app.core.config import settings

def setup_logging():
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format='%(message)s'
    )
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.INFO if not settings.DEBUG else logging.DEBUG
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )

logger = structlog.get_logger()

