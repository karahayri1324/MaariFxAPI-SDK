"""MaariFx Python SDK -- solve physics problems with AI."""

from .async_client import AsyncMaarifX
from .client import MaarifX
from .exceptions import AuthenticationError, MaarifXError, RateLimitError
from .models import SolveResult, StreamEvent, SubUser

__all__ = [
    "MaarifX",
    "AsyncMaarifX",
    "SolveResult",
    "StreamEvent",
    "SubUser",
    "MaarifXError",
    "RateLimitError",
    "AuthenticationError",
]

__version__ = "0.1.0"
