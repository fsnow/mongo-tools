"""Data models for MongoDB Atlas API responses."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class JobState(str, Enum):
    """Job state enumeration."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    IN_PROGRESS = "IN_PROGRESS"
    MARKED_FOR_EXPIRY = "MARKED_FOR_EXPIRY"
    EXPIRED = "EXPIRED"


@dataclass
class Shard:
    """Represents a MongoDB shard/process."""
    user_alias: str
    type_name: str
    replica_set_name: Optional[str] = None


@dataclass
class Clusters:
    """Response from the processes endpoint."""
    results: list[Shard]


@dataclass
class JobId:
    """Response from creating a log collection job."""
    id: str


@dataclass
class JobStatus:
    """Response from checking job status."""
    id: str
    download_url: str
    status: str


@dataclass
class LogCollectionJob:
    """Payload for creating a log collection job."""
    resource_type: str
    resource_name: str
    redacted: bool
    size_requested_per_file_bytes: int
    log_types: list[str]

    @classmethod
    def create(cls, replica_set: str, byte_size: int) -> "LogCollectionJob":
        """Create a log collection job payload."""
        return cls(
            resource_type="REPLICASET",
            resource_name=replica_set,
            redacted=True,
            size_requested_per_file_bytes=byte_size,
            log_types=["FTDC"],
        )
