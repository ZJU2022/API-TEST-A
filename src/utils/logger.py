import logging
import os
import sys
from datetime import datetime


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger instance with the specified name and log level.
    
    Args:
        name: The name of the logger (typically __name__)
        level: The logging level (default: INFO)
        
    Returns:
        Logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid adding handlers if they already exist
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file handler
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"api_test_{timestamp}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter and add to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
