"""MaariFx SDK exceptions."""

from __future__ import annotations


class MaarifXError(Exception):
    """Base exception for all MaariFx SDK errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(MaarifXError):
    """Raised on 401 responses -- invalid or missing API key."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(MaarifXError):
    """Raised on 429 responses -- rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ValidationError(MaarifXError):
    """Raised on 400 responses -- invalid request parameters."""

    def __init__(self, message: str = "Invalid request parameters") -> None:
        super().__init__(message, status_code=400)


class ProcessingError(MaarifXError):
    """Raised on 502 responses -- backend processing failure."""

    def __init__(self, message: str = "Processing failed") -> None:
        super().__init__(message, status_code=502)


class TimeoutError(MaarifXError):
    """Raised when a request times out."""

    def __init__(self, message: str = "Request timed out") -> None:
        super().__init__(message, status_code=None)
