class ScraperError(Exception):
    """Base scraper exception."""


class ScraperRequestError(ScraperError):
    """Raised when an HTTP request fails after retries."""
