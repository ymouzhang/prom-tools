"""
Base HTTP client with async support and rate limiting.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import aiohttp
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from asyncio_throttle import Throttler
from .exceptions import APIError, RateLimitError


class BaseAsyncClient(ABC):
    """Base class for async API clients with rate limiting and retry logic."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.headers = headers or {}

        # Rate limiting
        self.throttler = Throttler(rate_limit=rate_limit, period=1) if rate_limit else None

        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        self._httpx_session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure session is created."""
        if self._session is None or self._session.closed:
            connector_kwargs = {"ssl": self.verify_ssl}
            timeout = aiohttp.ClientTimeout(total=self.timeout)

            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(**connector_kwargs),
            )

    async def _ensure_httpx_session(self) -> None:
        """Ensure httpx session is created."""
        if self._httpx_session is None:
            self._httpx_session = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

    async def close(self) -> None:
        """Close all sessions."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._httpx_session:
            await self._httpx_session.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_httpx: bool = False,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and rate limiting."""

        if self.throttler:
            await self.throttler.acquire()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = {**self.headers, **(headers or {})}

        if use_httpx:
            return await self._request_httpx(method, url, params, json_data, request_headers)
        else:
            return await self._request_aiohttp(method, url, params, json_data, request_headers)

    async def _request_aiohttp(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Make request using aiohttp."""
        await self._ensure_session()

        async with self._session.request(
            method,
            url,
            params=params,
            json=json_data,
            headers=headers,
        ) as response:
            await self._handle_response(response)
            return await response.json()

    async def _request_httpx(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_data: Optional[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Make request using httpx."""
        await self._ensure_httpx_session()

        response = await self._httpx_session.request(
            method,
            url,
            params=params,
            json=json_data,
            headers=headers,
        )

        await self._handle_httpx_response(response)
        return response.json()

    async def _handle_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle aiohttp response and raise appropriate errors."""
        if response.status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limit exceeded",
                status_code=response.status,
                retry_after=int(retry_after) if retry_after else None,
            )
        elif response.status == 401:
            raise APIError(
                "Authentication failed",
                status_code=response.status,
            )
        elif response.status >= 400:
            error_text = await response.text()
            raise APIError(
                f"Request failed: {error_text}",
                status_code=response.status,
            )

    async def _handle_httpx_response(self, response: httpx.Response) -> None:
        """Handle httpx response and raise appropriate errors."""
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limit exceeded",
                status_code=response.status_code,
                retry_after=int(retry_after) if retry_after else None,
            )
        elif response.status_code == 401:
            raise APIError(
                "Authentication failed",
                status_code=response.status_code,
            )
        elif response.status_code >= 400:
            raise APIError(
                f"Request failed: {response.text}",
                status_code=response.status_code,
            )

    @abstractmethod
    def _prepare_auth_headers(self) -> Dict[str, str]:
        """Prepare authentication headers."""
        pass