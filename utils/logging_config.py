"""
Task Manager - 日志配置模块
提供 JSON 格式日志输出，支持接入 ELK/Graylog 等日志分析平台
"""
import logging
import json
import sys
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
    """带颜色的控制台格式化器（仅用于开发调试）"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""
        record.levelname = f"{color}{record.levelname}{reset}"
        return f"[{record.asctime}] [{record.levelname}] [{record.module}] {record.getMessage()}"


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
