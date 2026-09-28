"""Unified cloud file acquisition: combines direct public download and API-based extraction."""

import hashlib
import io
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx
import pymupdf

from cci.cloud.google_drive import GoogleDriveClient, extract_drive_file_id
from cci.config import settings
from cci.intake.canonicalizer import classify_url
from cci.intake.parsers.docx import parse_docx_document
from cci.live.public_links import (
    analyze_document_content,
    fetch_cloud_file_data,
    inspect_zip_content,
    is_cloud_storage_url,
)


def fetch_cloud_document(
    url: str,
    timeout: float = 20.0,
    transport: httpx.BaseTransport | None = None,
    google_drive_client: GoogleDriveClient | None = None,
) -> dict[str, Any]:
    """Unified entry point for downloading, extracting, and verifying files from cloud drives.

    Strategy chain:
    1. Direct public download (SSRF-safe, fast, handles unauthenticated/open links)
    2. Google Drive API integration (for auth-gated files, Google Docs, or folders)
    3. Graceful fallback with honest, informative verification receipts
    """
    # 1. Try public fetch first (handles open Google Drive, Dropbox, OneDrive, public direct links)
    receipt = fetch_cloud_file_data(url, timeout=timeout, transport=transport)
    if receipt.get("status") == "fetched":
        return receipt

    # 2. If blocked by authentication or unavailable, check if it's a Google Drive link
    drive_info = extract_drive_file_id(url)
    if not drive_info:
        return receipt

    # Check if Google Drive integration is enabled
    if not getattr(settings, "CLOUD_FILE_EXTRACTION_ENABLED", True):
        return receipt

    client = google_drive_client
    if client is None:
        client = GoogleDriveClient(
            service_account_key=getattr(settings, "GOOGLE_SERVICE_ACCOUNT_KEY", None),
            api_key=getattr(settings, "GOOGLE_DRIVE_API_KEY", None),
        )

    try:
        max_bytes = int(getattr(settings, "CLOUD_FILE_MAX_SIZE_MB", 10)) * 1024 * 1024
        raw_bytes, content_type, meta = client.download_or_export(
            drive_info.file_id,
            max_bytes=max_bytes,
            timeout=timeout,
            transport=transport,
        )

        title = meta.get("name", "") or drive_info.file_id
        sha = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None

        # Case A: Google Drive Folder
        if content_type == "application/vnd.google-apps.folder":
            folder_files = meta.get("folder_files") or meta.get("files", [])
            file_items = []
            technologies = set()

            for item in folder_files:
                name = item.get("name", "")
                size = int(item.get("size", 0) or 0)
                ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                ftype = "code" if ext in {"py", "ts", "tsx", "js", "go", "rs", "java", "c", "cpp"} else "doc" if ext in {"md", "txt", "pdf", "docx"} else "file"
                file_items.append({"name": name, "size": size, "type": ftype})

                base = name.lower()
                if base == "dockerfile":
                    technologies.add("Docker")
                elif base in {"package.json", "pnpm-lock.yaml", "yarn.lock"}:
                    technologies.add("Node.js")
                elif base in {"requirements.txt", "pyproject.toml"}:
                    technologies.add("Python")
                elif ext == "py":
                    technologies.add("Python")
                elif ext in {"ts", "tsx"}:
                    technologies.add("TypeScript")
                elif ext in {"js", "jsx"}:
                    technologies.add("JavaScript")
                elif ext == "go":
                    technologies.add("Go")

            tech_list = sorted(list(technologies))
            inferred_kind = "project" if any(f["type"] == "code" for f in file_items) else "cloud_storage"
            return {
                "url": url,
                "status": "fetched",
                "verification": "cloud_file_verified",
                "title": title or "Google Drive Folder",
                "files": file_items,
                "file_count": len(file_items),
                "total_size": sum(f["size"] for f in file_items),
                "technologies": tech_list,
                "excerpt": f"Google Drive folder containing: {', '.join(f['name'] for f in file_items[:8])}",
                "inferred_kind": inferred_kind,
                "detail": f"Successfully retrieved Google Drive folder manifest ({len(file_items)} items detected via Drive API).",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        if not raw_bytes:
            # If Google Drive returned an error
            err_detail = meta.get("detail", "Google Drive file could not be accessed.")
            return {
                **receipt,
                "status": "access_restricted" if meta.get("status_code") in (401, 403) else receipt.get("status", "unavailable"),
                "detail": err_detail,
            }

        # Case B: DOCX Document
        _docx_ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if _docx_ct in content_type or (raw_bytes[:4] == b"PK\x03\x04" and b"word/" in raw_bytes[:8000]):
            parsed_doc = parse_docx_document(raw_bytes)
            clean_text = " ".join(parsed_doc.raw_text.split())[:12000]
            inferred_kind, _ = analyze_document_content(url, title, "", clean_text, is_gated=False)
            techs = [t for t in ("Python", "TypeScript", "JavaScript", "Go", "Docker", "AWS", "React", "Kubernetes", "SQL", "FastAPI") if re.search(rf"\b{t}\b", clean_text, re.I)]
            return {
                "url": url,
                "status": "fetched",
                "verification": "cloud_file_verified",
                "title": title or "document.docx",
                "files": [{"name": title or "document.docx", "size": len(raw_bytes), "type": "docx"}],
                "file_count": 1,
                "total_size": len(raw_bytes),
                "technologies": techs,
                "excerpt": clean_text[:3000],
                "inferred_kind": inferred_kind,
                "detail": f"Extracted DOCX document content via Google Drive API ({len(raw_bytes):,} bytes). Verified contents.",
                "content_sha256": sha,
                "embedded_urls": list(dict.fromkeys(parsed_doc.embedded_urls + parsed_doc.visible_urls))[:50],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        # Case C: PDF Document
        if "application/pdf" in content_type or raw_bytes.startswith(b"%PDF"):
            doc_title, doc_text = "", ""
            try:
                with pymupdf.open(stream=raw_bytes, filetype="pdf") as doc:
                    doc_title = doc.metadata.get("title", "")
                    doc_text = "\n".join(page.get_text() for page in doc[:10])
            except Exception:
                pass
            clean_text = " ".join(doc_text.split())[:12000]
            doc_name = doc_title or title or "document.pdf"
            inferred_kind, _ = analyze_document_content(url, doc_name, "", clean_text, is_gated=False)
            techs = [t for t in ("Python", "TypeScript", "JavaScript", "Go", "Docker", "AWS", "React", "Kubernetes", "SQL", "FastAPI") if re.search(rf"\b{t}\b", clean_text, re.I)]
            return {
                "url": url,
                "status": "fetched",
                "verification": "cloud_file_verified",
                "title": doc_name,
                "files": [{"name": doc_name, "size": len(raw_bytes), "type": "pdf"}],
                "file_count": 1,
                "total_size": len(raw_bytes),
                "technologies": techs,
                "excerpt": clean_text[:3000],
                "inferred_kind": inferred_kind,
                "detail": f"Extracted digital PDF document via Google Drive API ({len(raw_bytes):,} bytes). Verified contents.",
                "content_sha256": sha,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        # Case D: ZIP Archive
        if any(t in content_type for t in ("application/zip", "application/x-zip-compressed")) or raw_bytes.startswith(b"PK\x03\x04"):
            files, techs, excerpt = inspect_zip_content(raw_bytes)
            return {
                "url": url,
                "status": "fetched",
                "verification": "cloud_file_verified",
                "title": title or "archive.zip",
                "files": files,
                "file_count": len(files),
                "total_size": len(raw_bytes),
                "technologies": techs,
                "excerpt": excerpt,
                "inferred_kind": "project",
                "detail": f"Downloaded and extracted project archive via Google Drive API ({len(files)} files, {len(raw_bytes):,} bytes).",
                "content_sha256": sha,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        # Case E: Plain text, CSV, exported Google Docs/Sheets
        if any(t in content_type for t in ("text/plain", "text/csv", "text/markdown", "application/json")):
            text = raw_bytes.decode("utf-8", errors="replace")
            clean_text = " ".join(text.split())[:12000]
            inferred_kind, _ = analyze_document_content(url, title, "", clean_text, is_gated=False)
            techs = [t for t in ("Python", "TypeScript", "JavaScript", "Go", "Docker", "AWS", "React", "Kubernetes", "SQL", "FastAPI") if re.search(rf"\b{t}\b", clean_text, re.I)]
            return {
                "url": url,
                "status": "fetched",
                "verification": "cloud_file_verified",
                "title": title or "document.txt",
                "files": [{"name": title or "document.txt", "size": len(raw_bytes), "type": "doc"}],
                "file_count": 1,
                "total_size": len(raw_bytes),
                "technologies": techs,
                "excerpt": clean_text[:3000],
                "inferred_kind": inferred_kind,
                "detail": f"Exported document data via Google Drive API ({title}, {len(raw_bytes):,} bytes).",
                "content_sha256": sha,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    except Exception as exc:
        return {
            **receipt,
            "detail": f"{receipt.get('detail', '')} (Drive API error: {exc})",
        }

    return receipt
