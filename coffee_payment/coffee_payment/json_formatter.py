"""
Custom JSON formatter for Django logging.
Properly escapes quotes and formats log messages as valid JSON.
"""
import json
import logging
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter that properly escapes special characters
    and outputs valid JSON for each log record.
    """
    
    def format(self, record):
        """
        Format the log record as a JSON string.
        
        Args:
            record: LogRecord instance
            
        Returns:
            str: JSON formatted log message
        """
        # Create log entry dictionary
        log_entry = {
            'timestamp': self.formatTime(record, self.datefmt),
            'tag': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Convert to JSON string (this properly escapes quotes and special characters)
        return json.dumps(log_entry, ensure_ascii=False)
