import logging
import json
from datetime import datetime

def log_error(message, tag, level):
    logger = logging.getLogger(tag)
    logger.error(message)

def log_info(message, tag):
    logger = logging.getLogger(tag)
    logger.info(message)
