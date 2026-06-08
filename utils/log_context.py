"""
日志上下文工具 - 提供请求追踪 ID（trace_id）注入能力
结构化日志中通过 logger.info("... | request_id=%s", trace_id) 形式输出
"""

import logging
import uuid
from contextlib import contextmanager


# 当前线程/协程内的请求追踪 ID
_current_trace_id: str = ""


def new_trace_id() -> str:
    """生成新的请求追踪 ID"""
    return uuid.uuid4().hex


def set_trace_id(trace_id: str) -> None:
    """设置当前上下文的 trace_id"""
    global _current_trace_id
    _current_trace_id = trace_id


def get_trace_id() -> str:
    """获取当前上下文的 trace_id，未设置时返回 '-'"""
    return _current_trace_id or "-"


@contextmanager
def with_request_trace(trace_id: str = None):
    """在上下文范围内使用指定的 trace_id（未传则自动生成）

    Usage:
        with with_request_trace():
            logger.info("...")
    """
    global _current_trace_id
    previous = _current_trace_id
    _current_trace_id = trace_id or new_trace_id()
    try:
        yield _current_trace_id
    finally:
        _current_trace_id = previous
