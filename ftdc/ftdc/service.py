"""FTDC download service for MongoDB Atlas."""

import time
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPDigestAuth

from .errors import (
    DownloadError,
    JobCreationError,
    JobStatusError,
    ReplicaSetNotFoundError,
)
from .models import Clusters, JobId, JobState, JobStatus, LogCollectionJob, Shard


MONGODB_API_BASE_URL = "https://cloud.mongodb.com/api/atlas/v1.0/groups"


class FTDCService:
    """Service for downloading FTDC data from MongoDB Atlas."""

    def __init__(self, public_key: str, private_key: str):
        """Initialize the FTDC service.

        Args:
            public_key: Atlas API public key
            private_key: Atlas API private key
        """
        self.auth = HTTPDigestAuth(public_key, private_key)
        self.session = requests.Session()

    def get_replica_set(
        self, group_key: str, replica_set_name: str
    ) -> str:
        """Get the replica set name from the cluster processes.

        Args:
            group_key: MongoDB Atlas project/group ID
            replica_set_name: Target replica set or shard name

        Returns:
            The actual replica set name

        Raises:
            ReplicaSetNotFoundError: If the replica set cannot be found
        """
        url = f"{MONGODB_API_BASE_URL}/{group_key}/processes"

        response = self.session.get(url, auth=self.auth)

        if response.status_code != 200:
            raise ReplicaSetNotFoundError(
                f"Failed to get processes. Status: {response.status_code}, "
                f"Response: {response.text}"
            )

        data = response.json()
        shards = [
            Shard(
                user_alias=result.get("userAlias", ""),
                type_name=result.get("typeName", ""),
                replica_set_name=result.get("replicaSetName"),
            )
            for result in data.get("results", [])
        ]

        # Filter shards matching the replica set name
        matching_shards = [
            shard
            for shard in shards
            if (shard.replica_set_name and replica_set_name in shard.replica_set_name)
            or replica_set_name in shard.user_alias
        ]

        if not matching_shards:
            raise ReplicaSetNotFoundError(
                f"No replica set found that corresponds to {replica_set_name}"
            )

        # Return the first match's replica set name
        first_shard = matching_shards[0]
        if first_shard.replica_set_name:
            return first_shard.replica_set_name

        raise ReplicaSetNotFoundError(
            f"Replica set name not found in matching shard: {first_shard.user_alias}"
        )

    def create_ftdc_job(
        self, group_key: str, replica_set: str, byte_size: int
    ) -> JobId:
        """Create an FTDC log collection job.

        Args:
            group_key: MongoDB Atlas project/group ID
            replica_set: Replica set name
            byte_size: Size of data to collect in bytes

        Returns:
            Job ID object

        Raises:
            JobCreationError: If job creation fails
        """
        url = f"{MONGODB_API_BASE_URL}/{group_key}/logCollectionJobs"

        job = LogCollectionJob.create(replica_set, byte_size)
        payload = {
            "resourceType": job.resource_type,
            "resourceName": job.resource_name,
            "redacted": job.redacted,
            "sizeRequestedPerFileBytes": job.size_requested_per_file_bytes,
            "logTypes": job.log_types,
        }

        response = self.session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            auth=self.auth,
        )

        if response.status_code != 201:
            raise JobCreationError(
                f"Failed to create FTDC job. Status: {response.status_code}, "
                f"Response: {response.text}"
            )

        data = response.json()
        return JobId(id=data["id"])

    def check_job_state(
        self, group_key: str, job_id: str, poll_interval: int = 3
    ) -> str:
        """Poll the job status until completion.

        Args:
            group_key: MongoDB Atlas project/group ID
            job_id: Job identifier
            poll_interval: Seconds to wait between polls

        Returns:
            Download URL for the job

        Raises:
            JobStatusError: If job status check fails or job fails
        """
        url = f"{MONGODB_API_BASE_URL}/{group_key}/logCollectionJobs/{job_id}"

        while True:
            response = self.session.get(url, auth=self.auth)

            if response.status_code != 200:
                raise JobStatusError(
                    f"Failed to check job status. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )

            data = response.json()
            status = data.get("status", "")

            if status == JobState.IN_PROGRESS.value:
                print(f"Job {job_id} is still in progress...")
                time.sleep(poll_interval)
                continue
            elif status in (JobState.SUCCESS.value, JobState.MARKED_FOR_EXPIRY.value):
                print(f"Job {job_id} completed successfully!")
                return data.get("downloadUrl", "")
            elif status in (JobState.FAILURE.value, JobState.EXPIRED.value):
                raise JobStatusError(
                    f"Job {job_id} failed with status: {status}"
                )
            else:
                raise JobStatusError(
                    f"Unknown job status: {status}"
                )

    def download_ftdc_data(
        self, group_key: str, job_id: str, replica_set: str, output_dir: Path
    ) -> Path:
        """Download the FTDC data file.

        Args:
            group_key: MongoDB Atlas project/group ID
            job_id: Job identifier
            replica_set: Replica set name
            output_dir: Directory to save the file

        Returns:
            Path to the downloaded file

        Raises:
            DownloadError: If download fails
        """
        url = f"{MONGODB_API_BASE_URL}/{group_key}/logCollectionJobs/{job_id}/download"

        response = self.session.get(url, auth=self.auth, stream=True)

        if response.status_code != 200:
            raise DownloadError(
                f"Failed to download FTDC data. Status: {response.status_code}, "
                f"URL: {url}"
            )

        filename = f"ftdc_data_{replica_set}_job_{job_id}.tar.gz"
        file_path = output_dir / filename

        print(f"Downloading FTDC data for job {job_id}...")

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Download complete!")
        return file_path

    def get_ftdc_data(
        self,
        group_key: str,
        replica_set_name: str,
        byte_size: int = 10_000_000,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Main method to orchestrate FTDC data download.

        Args:
            group_key: MongoDB Atlas project/group ID
            replica_set_name: Target replica set or shard name
            byte_size: Size of data to collect in bytes
            output_dir: Directory to save the file (defaults to current directory)

        Returns:
            Path to the downloaded file
        """
        if output_dir is None:
            output_dir = Path.cwd()

        # Step 1: Get replica set
        print(f"Looking for replica set: {replica_set_name}")
        replica_set = self.get_replica_set(group_key, replica_set_name)
        print(f"Found replica set: {replica_set}")

        # Step 2: Create FTDC job
        print("Creating FTDC collection job...")
        job = self.create_ftdc_job(group_key, replica_set, byte_size)
        print(f"Job created with ID: {job.id}")

        # Step 3: Poll job status
        print("Checking job status...")
        self.check_job_state(group_key, job.id)

        # Step 4: Download data
        file_path = self.download_ftdc_data(group_key, job.id, replica_set, output_dir)

        return file_path
