import logging
import sys
import structlog
from .config import settings


def configure_logging():
    """Configures structured logging."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),  # Shorter timestamp
    ]

    if settings.DEBUG:
        # Pretty printing for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)  # OpenAI HTTP spam
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Keep uvicorn access logs but make them less verbose
    if settings.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)


def get_logger(name: str):
    return structlog.get_logger(name)
