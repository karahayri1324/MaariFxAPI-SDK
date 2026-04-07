"""Synchronous MaariFx client."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import IO, Iterator, Optional, Union

import httpx

from .exceptions import (
    AuthenticationError,
    MaarifXError,
    ProcessingError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from .models import SolveResult, StreamEvent, SubUser, UsageStats, ViewResult
from .streaming import iter_sse

_DEFAULT_BASE_URL = "https://api2.ogretimsayfam.com"
_DEFAULT_TIMEOUT = 180.0

ImageInput = Union[str, bytes, Path, IO[bytes]]


def _guess_content_type(filename: str) -> str:
    ct, _ = mimetypes.guess_type(filename)
    return ct or "application/octet-stream"


class MaarifX:
    """Synchronous client for the MaariFx API.

    Args:
        api_key: Your MaariFx API key.  Falls back to the ``MAARIFX_API_KEY``
            environment variable when *None*.
        base_url: API base URL.
        timeout: Default request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.environ.get("MAARIFX_API_KEY", "")
        if not self.api_key:
            raise AuthenticationError(
                "API key is required. Pass api_key= or set MAARIFX_API_KEY."
            )
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-API-Key": self.api_key},
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "MaarifX":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def _prepare_image(
        self, image: ImageInput
    ) -> tuple[str, bytes, str]:
        """Return (filename, data, content_type) from an image input."""
        if isinstance(image, (str, Path)):
            path = Path(image)
            return (
                path.name,
                path.read_bytes(),
                _guess_content_type(path.name),
            )
        if isinstance(image, bytes):
            return ("image.png", image, "image/png")
        # File-like object
        name = getattr(image, "name", "image.png")
        if isinstance(name, (str, Path)):
            name = Path(name).name
        else:
            name = "image.png"
        return (name, image.read(), _guess_content_type(name))

    def _build_solve_files(
        self,
        image: ImageInput,
        text: str,
        draw_on_image: bool,
        detail_level: int,
        class_level: Optional[str],
        stream: bool,
    ) -> dict:
        filename, data, ct = self._prepare_image(image)
        files: dict = {
            "image": (filename, data, ct),
            "text": (None, text),
            "draw_on_image": (None, str(draw_on_image).lower()),
            "detail_level": (None, str(detail_level)),
            "stream": (None, str(stream).lower()),
        }
        if class_level is not None:
            files["class_level"] = (None, str(class_level))
        return files

    def solve(
        self,
        image: ImageInput,
        text: str = "",
        *,
        draw_on_image: bool = True,
        detail_level: int = 3,
        class_level: Optional[str] = None,
        sub_user_token: Optional[str] = None,
    ) -> SolveResult:
        """Send an image for solving and return the complete result.

        Args:
            image: Image as a file path, raw bytes, or file-like object.
            text: Optional question or context.
            draw_on_image: Whether to draw annotations on the image.
            detail_level: Detail level (1-5).
            class_level: Grade/class level hint.
            sub_user_token: Sub-user token for auth-based billing.

        Returns:
            A ``SolveResult`` with the answer.
        """
        files = self._build_solve_files(
            image, text, draw_on_image, detail_level, class_level, stream=False
        )
        headers: dict[str, str] = {}
        if sub_user_token:
            headers["X-Sub-User-Token"] = sub_user_token

        response = self._request_raw(
            "POST", "/v1/solve", files=files, headers=headers
        )
        body = response.json()
        return SolveResult.model_validate(body)

    def solve_stream(
        self,
        image: ImageInput,
        text: str = "",
        *,
        draw_on_image: bool = True,
        detail_level: int = 3,
        class_level: Optional[str] = None,
        sub_user_token: Optional[str] = None,
    ) -> Iterator[StreamEvent]:
        """Send an image for solving and stream events as they arrive.

        Yields ``StreamEvent`` objects including tokens, status updates,
        and the final ``complete`` event.
        """
        files = self._build_solve_files(
            image, text, draw_on_image, detail_level, class_level, stream=True
        )
        headers: dict[str, str] = {}
        if sub_user_token:
            headers["X-Sub-User-Token"] = sub_user_token

        with self._client.stream(
            "POST", "/v1/solve", files=files, headers=headers
        ) as response:
            _check_status(response)
            yield from iter_sse(response)

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def register_user(
        self,
        external_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> SubUser:
        """Register a new sub-user under your API key."""
        payload: dict = {"external_id": external_id}
        if display_name is not None:
            payload["display_name"] = display_name
        if email is not None:
            payload["email"] = email
        resp = self._request("POST", "/v1/users/register", json=payload)
        return SubUser.model_validate(resp)

    def verify_user(self, token: str) -> dict:
        """Verify a sub-user token."""
        return self._request("POST", "/v1/users/verify", json={"token": token})

    def list_users(self) -> list[SubUser]:
        """List all sub-users under your API key."""
        resp = self._request("GET", "/v1/users")
        users = resp.get("sub_users", resp.get("users", []))
        return [SubUser.model_validate(u) for u in users]

    def delete_user(self, external_id: str) -> dict:
        """Deactivate a sub-user by external ID."""
        return self._request("DELETE", f"/v1/users/{external_id}")

    # ------------------------------------------------------------------
    # Usage & views
    # ------------------------------------------------------------------

    def get_usage(self) -> UsageStats:
        """Retrieve usage statistics for your API key."""
        resp = self._request("GET", "/v1/usage")
        return UsageStats.model_validate(resp)

    def get_view_url(self, request_id: str) -> ViewResult:
        """Get a temporary view URL for a solved request."""
        resp = self._request("GET", f"/v1/view/{request_id}")
        return ViewResult.model_validate(resp)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Send a request and return parsed JSON body."""
        resp = self._request_raw(method, path, **kwargs)
        return resp.json()

    def _request_raw(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Send a request and return the raw httpx Response."""
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise TimeoutError(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise MaarifXError(f"HTTP error: {exc}") from exc
        _check_status(response)
        return response


def _check_status(response: httpx.Response) -> None:
    """Raise an appropriate exception for non-2xx responses."""
    if 200 <= response.status_code < 300:
        return

    try:
        body = response.json()
        message = body.get("error", body.get("message", response.text))
    except Exception:
        message = response.text

    status = response.status_code
    if status == 401:
        raise AuthenticationError(str(message))
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            str(message),
            retry_after=float(retry_after) if retry_after else None,
        )
    if status == 400:
        raise ValidationError(str(message))
    if status == 502:
        raise ProcessingError(str(message))
    raise MaarifXError(str(message), status_code=status)
