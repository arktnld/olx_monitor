"""Custom exceptions for OLX Monitor scraper"""


class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass


class NetworkError(ScraperError):
    """Network-related errors (connection, timeout, etc.)"""
    pass


class ParseError(ScraperError):
    """Errors when parsing HTML/JSON content"""
    pass


class RateLimitError(ScraperError):
    """Rate limiting or anti-bot protection detected"""
    pass


class AdNotFoundError(ScraperError):
    """Ad no longer exists or was removed"""
    pass
