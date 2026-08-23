class ScraperError(Exception):
    """Base scraper exception."""


class ScraperRequestError(ScraperError):
    """Raised when an HTTP request fails after retries."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScraperUnavailableError(ScraperRequestError):
    """Typed fail-closed diagnostic when a scraper cannot acquire data."""

    def __init__(self, message: str, *, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code
