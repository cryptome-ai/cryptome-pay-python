"""Exceptions for Cryptome Pay SDK."""

from typing import Optional


class CryptomePayError(Exception):
    """Base exception for Cryptome Pay errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(message)

    def is_retryable(self) -> bool:
        """Check if this error can be retried."""
        if self.status_code is None:
            return False
        return self.status_code == 429 or self.status_code >= 500

    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        if self.status_code is None:
            return False
        return 1001 <= self.status_code <= 1005

    def is_validation_error(self) -> bool:
        """Check if this is a validation error."""
        if self.status_code is None:
            return False
        return 10001 <= self.status_code <= 10009

    def is_chain_error(self) -> bool:
        """Check if this is a chain-related error."""
        if self.status_code is None:
            return False
        return 20001 <= self.status_code <= 20003


class AuthenticationError(CryptomePayError):
    """Authentication failed."""
    pass


class ValidationError(CryptomePayError):
    """Validation error."""
    pass


class RateLimitError(CryptomePayError):
    """Rate limit exceeded."""
    pass


class ChainError(CryptomePayError):
    """Chain-related error."""
    pass
