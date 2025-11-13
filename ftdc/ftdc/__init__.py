"""FTDC tool for MongoDB Atlas."""

from .cli import main
from .errors import FTDCError
from .service import FTDCService

__version__ = "0.1.0"

__all__ = ["main", "FTDCService", "FTDCError"]
