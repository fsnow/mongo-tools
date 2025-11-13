"""Custom exceptions for FTDC tool."""


class FTDCError(Exception):
    """Base exception for FTDC errors."""
    pass


class ReplicaSetNotFoundError(FTDCError):
    """Raised when the specified replica set cannot be found."""
    pass


class JobCreationError(FTDCError):
    """Raised when FTDC job creation fails."""
    pass


class JobStatusError(FTDCError):
    """Raised when checking job status fails."""
    pass


class DownloadError(FTDCError):
    """Raised when downloading FTDC data fails."""
    pass


class AuthenticationError(FTDCError):
    """Raised when authentication fails."""
    pass
