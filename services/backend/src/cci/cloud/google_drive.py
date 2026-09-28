"""Google Drive API client with bounded fetch, metadata inspection, and format conversion."""

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from cci.security.ssrf import SSRFSecurityError, resolve_and_validate_hostname


@dataclass(frozen=True)
class DriveResourceInfo:
    """Parsed Google Drive or Google Docs resource descriptor."""

    file_id: str
    resource_type: str  # 'file', 'document', 'spreadsheet', 'presentation', 'folder'
    raw_url: str


def extract_drive_file_id(url: str) -> DriveResourceInfo | None:
    """Extracts the file or folder ID and resource type from any Google Drive/Docs URL."""
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()

    # 1. Google Docs document
    doc_match = re.search(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)", cleaned)
    if doc_match:
        return DriveResourceInfo(file_id=doc_match.group(1), resource_type="document", raw_url=cleaned)

    # 2. Google Sheets spreadsheet
    sheet_match = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", cleaned)
    if sheet_match:
        return DriveResourceInfo(file_id=sheet_match.group(1), resource_type="spreadsheet", raw_url=cleaned)

    # 3. Google Slides presentation
    slides_match = re.search(r"docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)", cleaned)
    if slides_match:
        return DriveResourceInfo(file_id=slides_match.group(1), resource_type="presentation", raw_url=cleaned)

    # 4. Google Drive folder
    folder_match = re.search(r"drive\.google\.com/(?:drive/(?:u/\d+/)?folders/|folderview\?(?:[^\s&]*&)?id=)([a-zA-Z0-9_-]+)", cleaned)
    if folder_match:
        return DriveResourceInfo(file_id=folder_match.group(1), resource_type="folder", raw_url=cleaned)

    # 5. Standard Google Drive file (/file/d/<id>, /open?id=<id>, /uc?id=<id>)
    file_match = re.search(r"drive\.google\.com/(?:file/d/|open\?(?:[^\s&]*&)?id=|uc\?(?:[^\s&]*&)?id=)([a-zA-Z0-9_-]+)", cleaned)
    if file_match:
        return DriveResourceInfo(file_id=file_match.group(1), resource_type="file", raw_url=cleaned)

    return None


class GoogleDriveClient:
    """Lightweight Google Drive API v3 client with bounded execution and zero required external SDKs."""

    BASE_URL = "https://www.googleapis.com/drive/v3"

    def __init__(
        self,
        service_account_key: str | dict | None = None,
        api_key: str | None = None,
        access_token: str | None = None,
    ):
        self.api_key = api_key
        self.access_token = access_token
        self._service_account_info: dict[str, Any] | None = None
        self._cached_sa_token: str | None = None
        self._token_expiry: float = 0.0

        if service_account_key:
            if isinstance(service_account_key, dict):
                self._service_account_info = service_account_key
            elif isinstance(service_account_key, str):
                trimmed = service_account_key.strip()
                if trimmed.startswith("{"):
                    try:
                        self._service_account_info = json.loads(trimmed)
                    except Exception:
                        pass
                elif os.path.exists(trimmed):
                    try:
                        with open(trimmed, "r", encoding="utf-8") as f:
                            self._service_account_info = json.load(f)
                    except Exception:
                        pass

    def _get_bearer_token(self) -> str | None:
        """Resolves access token from direct token or service account credentials."""
        if self.access_token:
            return self.access_token

        if not self._service_account_info:
            return None

        now = time.time()
        if self._cached_sa_token and now < (self._token_expiry - 60):
            return self._cached_sa_token

        # Attempt to obtain a token via google-auth if installed
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests

            credentials = service_account.Credentials.from_service_account_info(
                self._service_account_info,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            self._cached_sa_token = credentials.token
            self._token_expiry = credentials.expiry.timestamp() if credentials.expiry else (now + 3600)
            return self._cached_sa_token
        except ImportError:
            pass
        except Exception:
            pass

        return None

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "CandidateX-CloudEvidence/1.0",
            "Accept": "application/json",
        }
        token = self._get_bearer_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _append_params(self, params: dict[str, Any]) -> dict[str, Any]:
        result = {**params}
        if self.api_key and "key" not in result and not self._get_bearer_token():
            result["key"] = self.api_key
        return result

    def get_metadata(
        self,
        file_id: str,
        timeout: float = 8.0,
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        """Fetches metadata for a file or folder from Google Drive API."""
        url = f"{self.BASE_URL}/files/{quote(file_id)}"
        params = self._append_params({
            "fields": "id,name,mimeType,size,description,trashed,webContentLink,capabilities",
            "supportsAllDrives": "true",
        })

        with httpx.Client(
            transport=transport,
            timeout=timeout,
            trust_env=False,
            follow_redirects=True,
        ) as client:
            resp = client.get(url, headers=self._build_headers(), params=params)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (401, 403):
                return {
                    "error": "access_restricted",
                    "status_code": resp.status_code,
                    "detail": "Google Drive document requires authentication or access permissions.",
                }
            elif resp.status_code == 404:
                return {
                    "error": "not_found",
                    "status_code": 404,
                    "detail": "Google Drive file not found or has been moved.",
                }
            return {
                "error": "http_error",
                "status_code": resp.status_code,
                "detail": f"Google Drive API returned HTTP {resp.status_code}.",
            }

    def list_folder_files(
        self,
        folder_id: str,
        max_files: int = 30,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> list[dict[str, Any]]:
        """Lists files located inside a Google Drive folder."""
        url = f"{self.BASE_URL}/files"
        query = f"'{folder_id}' in parents and trashed = false"
        params = self._append_params({
            "q": query,
            "fields": "files(id,name,mimeType,size,webContentLink)",
            "pageSize": min(max_files, 50),
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        })

        with httpx.Client(
            transport=transport,
            timeout=timeout,
            trust_env=False,
            follow_redirects=True,
        ) as client:
            resp = client.get(url, headers=self._build_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("files", [])
            return []

    def download_or_export(
        self,
        file_id: str,
        mime_type: str | None = None,
        max_bytes: int = 10 * 1024 * 1024,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> tuple[bytes | None, str, dict[str, Any]]:
        """Downloads a binary file or exports a Google Workspace doc to standard bytes.

        Returns (raw_bytes, content_type, metadata_or_error_dict).
        """
        # If mime_type was not provided, fetch metadata first
        meta = {}
        if not mime_type:
            meta = self.get_metadata(file_id, timeout=timeout, transport=transport)
            if "error" in meta:
                return None, "", meta
            mime_type = meta.get("mimeType", "")

        is_gdoc = mime_type == "application/vnd.google-apps.document"
        is_gsheet = mime_type == "application/vnd.google-apps.spreadsheet"
        is_gslides = mime_type == "application/vnd.google-apps.presentation"
        is_folder = mime_type == "application/vnd.google-apps.folder"

        if is_folder:
            if "folder_files" not in meta:
                meta["folder_files"] = self.list_folder_files(file_id, timeout=timeout, transport=transport)
            return None, "application/vnd.google-apps.folder", meta

        headers = self._build_headers()

        # Handle Google Workspace documents with export endpoint
        if is_gdoc or is_gsheet or is_gslides:
            export_mime = (
                "text/plain" if is_gdoc else
                "text/csv" if is_gsheet else
                "application/pdf"
            )
            export_url = f"{self.BASE_URL}/files/{quote(file_id)}/export"
            params = self._append_params({"mimeType": export_mime})

            with httpx.Client(
                transport=transport,
                timeout=timeout,
                trust_env=False,
                follow_redirects=True,
            ) as client:
                with client.stream("GET", export_url, headers=headers, params=params) as resp:
                    if resp.status_code != 200:
                        return None, "", {
                            "error": "export_failed",
                            "status_code": resp.status_code,
                            "detail": f"Failed to export Google document: HTTP {resp.status_code}",
                        }
                    content = bytearray()
                    for chunk in resp.iter_bytes():
                        content.extend(chunk)
                        if len(content) > max_bytes:
                            break
                    return bytes(content), export_mime, meta

        # Standard binary or uploaded file: download with alt=media
        download_url = f"{self.BASE_URL}/files/{quote(file_id)}"
        params = self._append_params({"alt": "media", "supportsAllDrives": "true"})

        with httpx.Client(
            transport=transport,
            timeout=timeout,
            trust_env=False,
            follow_redirects=True,
        ) as client:
            with client.stream("GET", download_url, headers=headers, params=params) as resp:
                if resp.status_code != 200:
                    return None, "", {
                        "error": "download_failed",
                        "status_code": resp.status_code,
                        "detail": f"Failed to download Google Drive file: HTTP {resp.status_code}",
                    }
                content_type = resp.headers.get("content-type", mime_type or "application/octet-stream")
                content = bytearray()
                for chunk in resp.iter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        break
                return bytes(content), content_type, meta
