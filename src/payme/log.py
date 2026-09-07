"""
Example usage
if __name__ == "__main__":
    logger = setup_logger("example_logger", level=logging.INFO)
    logger.info("This is an info message.")
    logger.error("This is an error message.")
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_DIR = "logs"


def resolve_log_file(log_file: str | Path | None = None) -> Path:
    """Resolve the log file path and create its directory.

    Resolution order: explicit argument, then ``PAYME_LOG_DIR``, then ``logs/``
    under the current working directory. The path is deliberately not derived
    from ``__file__`` - that wrote into the installed package's parent
    directory once the package was pip-installed. The returned path is absolute.
    """
    if log_file is not None:
        path = Path(log_file)
    else:
        path = Path(os.getenv("PAYME_LOG_DIR", DEFAULT_LOG_DIR)) / "payme.log"
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def setup_logger(
    name: str = "payme_logger",
    level: int = logging.DEBUG,
    log_file: str | Path | None = None,
):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # File handler
        file_handler = RotatingFileHandler(
            resolve_log_file(log_file),
            mode="a",  # Append mode
            encoding="utf-8",  # Ensure UTF-8 encoding
            delay=True,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.WARNING)  # Log only warnings and errors
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
