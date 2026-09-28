"""Unit tests for Google Drive URL extraction and API client operations."""

import json
import httpx
import pytest

from cci.cloud.google_drive import (
    DriveResourceInfo,
    GoogleDriveClient,
    extract_drive_file_id,
)


def test_extract_drive_file_id_various_formats():
    # 1. Drive file view link
    info1 = extract_drive_file_id("https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view?usp=sharing")
    assert info1 is not None
    assert info1.file_id == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert info1.resource_type == "file"

    # 2. Drive open?id= link
    info2 = extract_drive_file_id("https://drive.google.com/open?id=abc1234XYZ")
    assert info2 is not None
    assert info2.file_id == "abc1234XYZ"
    assert info2.resource_type == "file"

    # 3. Drive uc?id= link
    info3 = extract_drive_file_id("https://drive.google.com/uc?export=download&id=uc_file_999")
    assert info3 is not None
    assert info3.file_id == "uc_file_999"
    assert info3.resource_type == "file"

    # 4. Google Docs
    info4 = extract_drive_file_id("https://docs.google.com/document/d/doc_sample_123/edit?tab=t.0")
    assert info4 is not None
    assert info4.file_id == "doc_sample_123"
    assert info4.resource_type == "document"

    # 5. Google Sheets
    info5 = extract_drive_file_id("https://docs.google.com/spreadsheets/d/sheet_sample_456/edit#gid=0")
    assert info5 is not None
    assert info5.file_id == "sheet_sample_456"
    assert info5.resource_type == "spreadsheet"

    # 6. Google Slides
    info6 = extract_drive_file_id("https://docs.google.com/presentation/d/deck_sample_789/edit#slide=id.p")
    assert info6 is not None
    assert info6.file_id == "deck_sample_789"
    assert info6.resource_type == "presentation"

    # 7. Google Drive Folder
    info7 = extract_drive_file_id("https://drive.google.com/drive/folders/folder_xyz_987")
    assert info7 is not None
    assert info7.file_id == "folder_xyz_987"
    assert info7.resource_type == "folder"

    info8 = extract_drive_file_id("https://drive.google.com/drive/u/1/folders/folder_with_user")
    assert info8 is not None
    assert info8.file_id == "folder_with_user"
    assert info8.resource_type == "folder"

    # 8. Non-Google URLs return None
    assert extract_drive_file_id("https://github.com/user/repo") is None
    assert extract_drive_file_id("https://dropbox.com/s/123/file.zip") is None
    assert extract_drive_file_id("") is None


def test_google_drive_client_metadata():
    client = GoogleDriveClient(api_key="fake-test-key")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "fake-test-key" in str(request.url)
        assert "/files/test_id" in str(request.url)
        return httpx.Response(
            200,
            json={
                "id": "test_id",
                "name": "portfolio_project.zip",
                "mimeType": "application/zip",
                "size": "1048576",
                "trashed": False,
            },
        )

    transport = httpx.MockTransport(mock_handler)
    meta = client.get_metadata("test_id", transport=transport)
    assert meta["id"] == "test_id"
    assert meta["name"] == "portfolio_project.zip"
    assert meta["mimeType"] == "application/zip"


def test_google_drive_client_access_restricted():
    client = GoogleDriveClient()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "The caller does not have permission"}})

    transport = httpx.MockTransport(mock_handler)
    meta = client.get_metadata("private_file", transport=transport)
    assert meta["error"] == "access_restricted"
    assert meta["status_code"] == 403


def test_google_drive_client_export_google_doc():
    client = GoogleDriveClient()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "/export" in str(request.url):
            assert "mimeType=text%2Fplain" in str(request.url) or "mimeType=text/plain" in str(request.url)
            return httpx.Response(200, text="System Architecture Specification\nMicroservices built with FastAPI and Redis.")
        return httpx.Response(200, json={"id": "doc1", "name": "Spec.gdoc", "mimeType": "application/vnd.google-apps.document"})

    transport = httpx.MockTransport(mock_handler)
    content, content_type, meta = client.download_or_export(
        "doc1",
        mime_type="application/vnd.google-apps.document",
        transport=transport,
    )
    assert content is not None
    assert content_type == "text/plain"
    assert b"System Architecture" in content


def test_google_drive_client_list_folder():
    client = GoogleDriveClient()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "files": [
                    {"id": "f1", "name": "main.py", "mimeType": "text/x-python", "size": "1200"},
                    {"id": "f2", "name": "Dockerfile", "mimeType": "text/plain", "size": "450"},
                    {"id": "f3", "name": "README.md", "mimeType": "text/markdown", "size": "800"},
                ]
            },
        )

    transport = httpx.MockTransport(mock_handler)
    files = client.list_folder_files("folder123", transport=transport)
    assert len(files) == 3
    assert files[0]["name"] == "main.py"
    assert files[1]["name"] == "Dockerfile"
