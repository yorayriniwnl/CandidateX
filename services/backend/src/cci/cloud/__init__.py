"""Cloud file acquisition and extraction package."""

from cci.cloud.google_drive import (
    GoogleDriveClient,
    extract_drive_file_id,
    DriveResourceInfo,
)
from cci.cloud.fetcher import (
    fetch_cloud_document,
)

__all__ = [
    "GoogleDriveClient",
    "extract_drive_file_id",
    "DriveResourceInfo",
    "fetch_cloud_document",
]
