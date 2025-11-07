"""Logging setup for EarShot."""
import logging
import os
import sys


def setup_logging(log_dir: str, level: str = "INFO"):
    """Configure application logging to console and file."""
    os.makedirs(log_dir, exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Format: timestamp level module :: message
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s :: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # File handler
    logfile = os.path.join(log_dir, "earshot.log")
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
