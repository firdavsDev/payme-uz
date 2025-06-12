import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

base_root_path = Path(__file__).parent.parent.parent
log_folder_path = base_root_path / "logs"
log_folder_path.mkdir(parents=True, exist_ok=True)
log_file_path = log_folder_path / "payme.log"


def setup_logger(name: str = "payme_logger", level: int = logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # File handler
        file_handler = RotatingFileHandler(
            log_file_path,
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


# Example usage
# if __name__ == "__main__":
#     logger = setup_logger("example_logger", level=logging.INFO)
#     logger.info("This is an info message.")
#     logger.error("This is an error message.")
