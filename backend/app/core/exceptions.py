from __future__ import annotations


class AppException(Exception):
    """应用级异常基类"""

    def __init__(self, message: str, status_code: int = 500, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=404,
        )


class DataQualityError(AppException):
    """数据质量问题（如未来函数检测命中）"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message=message, status_code=422, detail=detail)


class LLMTimeoutError(AppException):
    def __init__(self, news_id: str | None = None):
        super().__init__(
            message=f"LLM inference timeout{' for news ' + news_id if news_id else ''}",
            status_code=504,
        )


class RateLimitError(AppException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            detail={"retry_after_seconds": retry_after},
        )
