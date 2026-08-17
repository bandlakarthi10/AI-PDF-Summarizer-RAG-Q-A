import logging
import sys
import io


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("pdf_rag")
    if logger.handlers:
        return logger          # Already configured

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Use UTF-8 encoding on stdout to handle Unicode characters (arrows, emoji)
    # on Windows where the default console encoding may be CP1252.
    stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    handler = logging.StreamHandler(stream)
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = setup_logging()
