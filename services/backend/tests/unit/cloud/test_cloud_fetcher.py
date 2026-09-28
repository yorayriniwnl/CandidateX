"""Unit tests for the unified cloud document fetcher."""

import io
import docx
import httpx
import pytest

from cci.cloud.fetcher import fetch_cloud_document
from cci.cloud.google_drive import GoogleDriveClient


def test_fetch_cloud_document_public_success():
    """If the public download succeeds, fetch_cloud_document returns the public receipt directly."""
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, headers={"content-type": "application/pdf"}, content=fake_pdf)
    )
    result = fetch_cloud_document("https://drive.google.com/file/d/test1234/view", transport=transport)
    assert result["status"] == "fetched"
    assert result["file_count"] == 1


def test_fetch_cloud_document_fallback_to_drive_api_for_folder():
    """When a folder link is fetched, Drive API lists the folder items and infers the project stack."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "googleapis.com/drive/v3/files" in url_str:
            return httpx.Response(
                200,
                json={
                    "name": "Backend-Microservices",
                    "mimeType": "application/vnd.google-apps.folder",
                    "files": [
                        {"id": "1", "name": "main.py", "size": 1500},
                        {"id": "2", "name": "Dockerfile", "size": 300},
                        {"id": "3", "name": "requirements.txt", "size": 200},
                    ],
                },
            )
        # Public preview returns login gate
        return httpx.Response(401, text="Sign in to Google Drive")

    transport = httpx.MockTransport(mock_handler)
    gdrive_client = GoogleDriveClient(api_key="mock-key")

    result = fetch_cloud_document(
        "https://drive.google.com/drive/folders/folder_sample_123",
        transport=transport,
        google_drive_client=gdrive_client,
    )
    assert result["status"] == "fetched"
    assert result["inferred_kind"] == "project"
    assert "Python" in result["technologies"]
    assert "Docker" in result["technologies"]
    assert result["file_count"] == 3


def test_fetch_cloud_document_fallback_docx_download():
    """When a restricted file is fetched with Drive API, DOCX content is parsed and verified."""
    doc = docx.Document()
    doc.add_paragraph("AWS Certified Solutions Architect Certificate")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "googleapis.com" in url_str:
            if "alt=media" in url_str:
                return httpx.Response(
                    200,
                    headers={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                    content=docx_bytes,
                )
            return httpx.Response(
                200,
                json={
                    "id": "docx_sample_456",
                    "name": "aws_cert.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "size": str(len(docx_bytes)),
                },
            )
        return httpx.Response(403, text="Access Denied")

    transport = httpx.MockTransport(mock_handler)
    gdrive_client = GoogleDriveClient(api_key="mock-key")

    result = fetch_cloud_document(
        "https://drive.google.com/file/d/docx_sample_456/view",
        transport=transport,
        google_drive_client=gdrive_client,
    )
    assert result["status"] == "fetched"
    assert result["inferred_kind"] == "credential"
    assert "AWS" in result["technologies"]
    assert result["files"][0]["type"] == "docx"
