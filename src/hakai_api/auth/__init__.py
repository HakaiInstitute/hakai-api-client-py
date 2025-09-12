"""Authentication strategies for the Hakai API client."""

from .base import AuthStrategy
from .desktop import DesktopAuthStrategy
from .web import WebAuthStrategy

__all__ = ["AuthStrategy", "WebAuthStrategy", "DesktopAuthStrategy"]
