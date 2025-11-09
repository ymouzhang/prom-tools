"""
Custom exceptions for prom-tools library.
"""

from typing import Optional, Dict, Any


class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response or {}

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (HTTP {self.status_code})"
        return self.message


class PrometheusError(APIError):
    """Exception raised for Prometheus API errors."""
    pass


class GrafanaError(APIError):
    """Exception raised for Grafana API errors."""
    pass


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""
    pass


class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


class ValidationError(Exception):
    """Exception raised for data validation errors."""
    pass