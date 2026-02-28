# logger.py - 日志工具
import logging
import sys
from typing import Optional

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_logger(
    name: str,
    level: Optional[str] = None,
    format_str: Optional[str] = None
) -> logging.Logger:
    """获取日志记录器"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(format_str or DEFAULT_FORMAT))
        logger.addHandler(handler)
    
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    else:
        logger.setLevel(logging.INFO)
    
    return logger


app_logger = get_logger("langgraph-mini")
