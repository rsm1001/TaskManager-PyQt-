"""
Task Manager - 日志配置模块
提供 JSON 格式日志输出，支持接入 ELK/Graylog 等日志分析平台
"""
import logging
import json
import re
import sys
import time
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """JSON 格式化器，将日志记录转换为 JSON 格式"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if self.include_extra and hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # 添加任务相关上下文（如果存在）
        if hasattr(record, "task_type"):
            log_entry["task_type"] = record.task_type
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id

        return json.dumps(log_entry, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器（仅用于开发调试）

    输出格式示例:
    2026-05-21 14:54:53.330 INFO    logging_config.py:85  日志系统初始化完成，日志文件: C:\\Users\\...  key=value ...
    """
    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"
    GRAY = "\033[90m"
    BLUE = "\033[34m"

    # 键值对正则: key=value, key="value", key='value'
    _KV_PATTERN = re.compile(
        r'(\w+)=(["\'])([^"\'\\]*(?:\\.[^"\'\\]*)*)\2'  # key="value" 或 key='value'
        r'|'
        r'(\w+)=(\S+?)(?=\s|$)'  # key=value
    )

    def formatTime(self, record: logging.LogRecord, datefmt=None) -> str:
        """兼容 Python 3.8 的时间格式化，使用毫秒精度"""
        ct = int(record.created)
        msec = int(record.msecs) if isinstance(record.msecs, float) else record.msecs
        if datefmt:
            return time.strftime(datefmt, time.localtime(ct)) + '.' + f"{msec:03d}"
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ct)) + '.' + f"{msec:03d}"

    def _colorize_kv(self, msg: str) -> str:
        """为消息中的键值对着色：键用蓝色，值保持默认色"""
        def replacer(match):
            # 处理 key="value" 或 key='value' 情况
            if match.group(1) is not None:
                key, quote, value = match.group(1), match.group(2), match.group(3)
                return f"{self.BLUE}{key}{self.RESET}={quote}{value}{quote}"
            # 处理 key=value 情况
            elif match.group(4) is not None:
                key, value = match.group(4), match.group(5)
                return f"{self.BLUE}{key}{self.RESET}={value}"
            return match.group(0)
        return self._KV_PATTERN.sub(replacer, msg)

    def format(self, record: logging.LogRecord) -> str:
        # 时间戳（灰色）
        timestamp = f"{self.GRAY}{self.formatTime(record)}{self.RESET}"

        # 级别（固定8字符宽度 + 对应颜色）
        level_color = self.COLORS.get(record.levelname, "")
        level_str = f"{level_color}{record.levelname[:8]:8}{self.RESET}"

        # 位置（青色）
        location = f"{self.COLORS['DEBUG']}{record.module}:{record.lineno}{self.RESET}"

        # 消息（白色，含键值对着色）
        message = self._colorize_kv(record.getMessage())

        return f"{timestamp} {level_str} {location}  {message}"


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    log_dir: str = None,
    enable_console: bool = True,
    enable_json_file: bool = True,
):
    """
    初始化日志系统

    Args:
        log_level: 日志级别，默认 INFO
        log_file: 日志文件名，默认使用 config 中的设置
        log_dir: 日志目录，默认使用 config 中的设置
        enable_console: 是否启用控制台输出
        enable_json_file: 是否启用 JSON 文件输出
    """
    import config.config

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 避免重复添加 handler
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 控制台输出（带颜色，用于开发）
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)

    # JSON 文件输出
    if enable_json_file:
        import os
        log_dir = log_dir or getattr(config.config, "LOG_DIR", "./logs")
        log_file = log_file or getattr(config.config, "LOG_FILE", "taskmanager.json.log")

        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, log_file)

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger"""
    return logging.getLogger(name)


def add_task_context(
    logger: logging.Logger,
    task_type: str,
    task_id: str = None,
    **kwargs
) -> logging.LoggerAdapter:
    """
    为 logger 添加任务上下文，返回带上下文的 adapter

    Args:
        logger: 原始 logger
        task_type: 任务类型（daily/todo/entertainment/shortcut）
        task_id: 任务 ID
        **kwargs: 其他额外字段

    Returns:
        LoggerAdapter，带有 task_type 和 task_id 上下文
    """
    extra = {"task_type": task_type, **(kwargs if task_id else {})}
    if task_id:
        extra["task_id"] = task_id
    return logging.LoggerAdapter(logger, extra)
