from enum import Enum


class LogLevel(Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'

COLORS = {
    LogLevel.DEBUG: '\033[36m',    # cyan
    LogLevel.INFO: '\033[92m',     # green
    LogLevel.WARNING: '\033[95m',  # purple
    LogLevel.ERROR: '\033[91m',    # red
    LogLevel.CRITICAL: '\033[31m', # dark-red
    'ENDC': '\033[0m'              # reset color
}

class Logger:
    @classmethod
    def _format_message(cls, level: LogLevel, message: str) -> str:
        color = COLORS.get(level, COLORS['ENDC'])
        return f"{color}[{level}]{COLORS['ENDC']} {message}"
    
    @classmethod
    def log(cls, level: LogLevel = LogLevel.DEBUG, *args, **kwargs):
        message = ' '.join(str(arg) for arg in args)
        formatted_message = cls._format_message(level, message)
        print(formatted_message, **kwargs)
    
    @classmethod
    def debug(cls, *args, **kwargs):
        cls.log(LogLevel.DEBUG, *args, **kwargs)
    
    @classmethod
    def info(cls, *args, **kwargs):
        cls.log(LogLevel.INFO, *args, **kwargs)
    
    @classmethod
    def warning(cls, *args, **kwargs):
        cls.log(LogLevel.WARNING, *args, **kwargs)
    
    @classmethod
    def error(cls, *args, **kwargs):
        cls.log(LogLevel.ERROR, *args, **kwargs)
    
    @classmethod
    def critical(cls, *args, **kwargs):
        cls.log(LogLevel.CRITICAL, *args, **kwargs)

    @classmethod
    def setup(cls, level: LogLevel = LogLevel.INFO):
        cls._level = level