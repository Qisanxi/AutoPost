"""
Safe exception classes — internal details are never exposed to users or logs.
"""


class DevRelAgentError(Exception):
    """Base exception."""
    def __init__(self, message: str, safe_message: str = "An error occurred"):
        super().__init__(message)
        self.safe_message = safe_message


class ValidationError(DevRelAgentError):
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation failed for {field}: {message}",
            safe_message=f"Invalid input provided for {field}."
        )
        self.field = field


class APIError(DevRelAgentError):
    def __init__(self, service: str, message: str, status_code: int = 0):
        super().__init__(
            message=f"{service} API error: {message}",
            safe_message=f"Unable to connect to {service}. Please try again later."
        )
        self.service = service
        self.status_code = status_code


class RateLimitError(APIError):
    def __init__(self, service: str):
        super().__init__(service=service, message="Rate limit exceeded", status_code=429)


class PublishingError(DevRelAgentError):
    def __init__(self, platform: str, message: str):
        super().__init__(
            message=f"Publishing to {platform} failed: {message}",
            safe_message=f"Unable to publish to {platform}."
        )
        self.platform = platform