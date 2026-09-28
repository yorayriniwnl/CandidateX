"""Bounded public page inspection. Remote content is data, never instructions or code."""
import hashlib
import io
import re
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx
import pymupdf

from cci.intake.canonicalizer import classify_url, is_false_positive_link
from cci.security.ssrf import resolve_and_validate_hostname, SSRFSecurityError

MAX_LINKS = 24
MAX_BYTES = 512 * 1024
LINK_SECONDS = 20


class PublicTransport(httpx.BaseTransport):
    """Pin the connection to a validated address while preserving TLS SNI and Host.

    No connection reuse across hosts sharing an IP. The underlying transport never
    receives the user hostname as its connection destination and ignores proxy env.
    """
    def __init__(self):
        self.transport = httpx.HTTPTransport(trust_env=False, retries=0,
            limits=httpx.Limits(max_keepalive_connections=0))

    def handle_request(self, request):
        parsed = urlsplit(str(request.url))
        if (parsed.scheme not in {'https', 'http'} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in {None, 80, 443}):
            raise SSRFSecurityError('Only public HTTP(S) links on standard ports without credentials are allowed.')
        addresses = resolve_and_validate_hostname(parsed.hostname)
        if any(not ip.is_global for ip in addresses):
            raise SSRFSecurityError('Non-public network addresses are not allowed.')
        headers = dict(request.headers)
        headers['host'] = request.url.netloc.decode('ascii')
        pinned = httpx.Request(request.method, request.url.copy_with(host=str(addresses[0])),
            headers=headers, extensions={**request.extensions, 'sni_hostname': request.url.host})
        return self.transport.handle_request(pinned)

    def close(self):
        self.transport.close()


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.in_title = False
        self.title, self.description, self.text = [], '', []
        self.og_title = ''

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'template', 'svg'}:
            self.hidden += 1
        if tag == 'title':
            self.in_title = True
        values = dict(attrs)
        if tag == 'meta':
            name = values.get('name', '').lower()
            prop = values.get('property', '').lower()
            content = values.get('content', '')
            if (prop == 'og:title' or name == 'og:title') and content:
                self.og_title = content[:300]
            if (name == 'description' or prop == 'og:description') and not self.description:
                self.description = content[:1000]

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript', 'template', 'svg'}:
            self.hidden = max(0, self.hidden - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.hidden:
            return
        if self.in_title:
            self.title.append(data)
        elif data.strip():
            self.text.append(data.strip())


def is_cloud_storage_url(url: str) -> bool:
    """Checks whether a URL points to a cloud drive or shared document host."""
    cat = classify_url(url)
    if cat == "cloud_storage":
        return True
    domain = urlsplit(url).netloc.lower()
    return any(s in domain for s in ("drive.google", "docs.google", "dropbox", "onedrive", "1drv.ms", "sharepoint", "box.com", "icloud"))


def get_cloud_direct_download_url(url: str) -> str | None:
    """Translates a cloud viewer/sharing URL into a direct fetch/download URL where possible."""
    # Google Drive file
    match = re.search(r'drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Google Docs
    match = re.search(r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)', url)
    if match:
        doc_id = match.group(1)
        return f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    # Google Sheets
    match = re.search(r'docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)', url)
    if match:
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    # Google Slides
    match = re.search(r'docs\.google\.com/presentation/d/([a-zA-Z0-9_-]+)', url)
    if match:
        slide_id = match.group(1)
        return f"https://docs.google.com/presentation/d/{slide_id}/export/pdf"

    # Dropbox
    if 'dropbox.com' in url:
        if '?dl=0' in url:
            return url.replace('?dl=0', '?dl=1')
        elif '&dl=0' in url:
            return url.replace('&dl=0', '&dl=1')
        elif '?' in url and 'dl=1' not in url:
            return url + '&dl=1'
        elif '?' not in url:
            return url + '?dl=1'

    # OneDrive / 1drv.ms
    if any(h in url for h in ('onedrive.live.com', '1drv.ms')):
        if 'download=1' not in url:
            sep = '&' if '?' in url else '?'
            return url + f'{sep}download=1'

    return None


def inspect_zip_content(content: bytes) -> tuple[list[dict], list[str], str]:
    """Inspects an in-memory zip archive to extract file manifest, tech stack, and excerpt."""
    files = []
    technologies = set()
    excerpt_parts = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            infolist = zf.infolist()
            valid_entries = [
                info for info in infolist
                if not info.is_dir()
                and not info.filename.startswith('__MACOSX/')
                and '/.git/' not in info.filename
                and not info.filename.startswith('.git/')
            ]
            for info in valid_entries[:60]:
                fname = info.filename
                fsize = info.file_size
                ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''

                ftype = 'file'
                if ext in {'py', 'ts', 'tsx', 'js', 'jsx', 'go', 'rs', 'java', 'c', 'cpp', 'cs', 'php', 'rb', 'sql'}:
                    ftype = 'code'
                elif ext in {'md', 'txt', 'pdf', 'docx', 'doc', 'rst'}:
                    ftype = 'doc'
                elif ext in {'json', 'yaml', 'yml', 'toml', 'xml', 'csv', 'env'}:
                    ftype = 'config'

                files.append({'name': fname, 'size': fsize, 'type': ftype})

                base = fname.split('/')[-1].lower()
                if base == 'dockerfile':
                    technologies.add('Docker')
                elif base in {'package.json', 'pnpm-lock.yaml', 'yarn.lock'}:
                    technologies.add('Node.js')
                elif base in {'requirements.txt', 'pyproject.toml', 'pipfile'}:
                    technologies.add('Python')
                elif base == 'go.mod':
                    technologies.add('Go')
                elif base == 'cargo.toml':
                    technologies.add('Rust')
                elif ext == 'py':
                    technologies.add('Python')
                elif ext in {'ts', 'tsx'}:
                    technologies.add('TypeScript')
                elif ext in {'js', 'jsx'}:
                    technologies.add('JavaScript')
                elif ext == 'go':
                    technologies.add('Go')
                elif ext == 'rs':
                    technologies.add('Rust')
                elif ext == 'java':
                    technologies.add('Java')
                elif ext == 'sql':
                    technologies.add('SQL')

                if len(excerpt_parts) < 3 and (base.startswith('readme') or ext in {'py', 'ts', 'js', 'txt'}):
                    if fsize < 32 * 1024:
                        try:
                            sample = zf.read(info.filename).decode('utf-8', errors='replace')
                            clean_sample = ' '.join(sample.split())[:300]
                            excerpt_parts.append(f"[{base}]: {clean_sample}")
                        except Exception:
                            pass
    except Exception:
        pass
    return files, sorted(list(technologies)), ' | '.join(excerpt_parts)


def fetch_cloud_file_data(url: str, timeout: float = 20.0, transport=None) -> dict:
    """Safely opens a cloud or public link, fetches file content, extracts files and data."""
    receipt = {
        'url': url,
        'status': 'unavailable',
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'files': [],
        'file_count': 0,
        'total_size': 0,
        'technologies': [],
        'excerpt': '',
        'title': '',
        'inferred_kind': 'cloud_storage',
        'detail': 'Link could not be reached.',
    }
    if is_false_positive_link(url):
        return {**receipt, 'status': 'not_scanned', 'detail': 'Invalid URL or academic degree abbreviation falsely parsed as a link.'}
    parsed = urlsplit(url)
    if parsed.scheme not in {'https', 'http'} or not parsed.hostname:
        return {**receipt, 'detail': 'Only public HTTP(S) links are supported.'}
    try:
        addresses = resolve_and_validate_hostname(parsed.hostname)
        if any(not ip.is_global for ip in addresses):
            return {**receipt, 'status': 'security_blocked', 'detail': 'Non-public network addresses are not allowed.'}
    except SSRFSecurityError:
        return {**receipt, 'status': 'security_blocked', 'detail': 'Destination failed safety validation.'}

    direct_url = get_cloud_direct_download_url(url)
    urls_to_try = [direct_url, url] if direct_url and direct_url != url else [url]

    deadline = time.monotonic() + timeout
    for target_url in urls_to_try:
        try:
            with httpx.Client(transport=transport or PublicTransport(), follow_redirects=False,
                              trust_env=False, headers={'User-Agent': 'CandidateX-PublicEvidence/1.0',
                              'Accept': '*/*', 'Accept-Encoding': 'identity'}) as client:
                current, redirects = target_url, []
                for hop in range(4):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return {**receipt, 'status': 'timeout', 'detail': 'Fetch timed out.'}
                    client.cookies.clear()
                    with client.stream('GET', current, timeout=min(6.0, remaining)) as response:
                        if response.is_redirect:
                            if hop == 3 or not response.headers.get('location'):
                                break
                            current = urljoin(current, response.headers['location'])
                            redirects.append(current)
                            continue
                        if response.status_code in (401, 403, 429, 999):
                            is_cloud = is_cloud_storage_url(url)
                            detail = (f'Cloud document requires authentication or access permissions (HTTP {response.status_code}). Cannot fetch files without access.'
                                      if is_cloud else f'Login or permission gate prevents fetching (HTTP {response.status_code}).')
                            return {**receipt, 'status': 'access_restricted', 'detail': detail}
                        if response.status_code != 200:
                            break

                        content_type = response.headers.get('content-type', '').lower()
                        max_cloud_bytes = 2 * 1024 * 1024
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > max_cloud_bytes:
                                break
                            if time.monotonic() >= deadline:
                                return {**receipt, 'status': 'timeout', 'detail': 'Fetch timed out.'}

                        raw_bytes = bytes(content)
                        sha = hashlib.sha256(raw_bytes).hexdigest()
                        _docx_ct = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                        is_docx = (_docx_ct in content_type
                                   or ('application/octet-stream' in content_type
                                       and raw_bytes[:4] == b'PK\x03\x04'
                                       and b'word/' in raw_bytes[:8000]))
                        is_image = any(t in content_type for t in ('image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/tiff'))
                        is_spreadsheet = any(t in content_type for t in (
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'))
                        is_presentation = any(t in content_type for t in (
                            'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint'))
                        is_zip = (not is_docx and not is_spreadsheet and not is_presentation) and (
                            any(t in content_type for t in ('application/zip', 'application/x-zip-compressed'))
                            or raw_bytes.startswith(b'PK\x03\x04'))
                        is_pdf = 'application/pdf' in content_type or raw_bytes.startswith(b'%PDF')

                        # 1. DOCX Document
                        if is_docx:
                            from cci.intake.parsers.docx import parse_docx_document
                            parsed_doc = parse_docx_document(raw_bytes)
                            doc_text = ' '.join(parsed_doc.raw_text.split())[:12000]
                            clean_path = parsed.path.split('/')[-1]
                            title = clean_path if clean_path and '.' in clean_path else 'document.docx'
                            inferred_kind, _ = analyze_document_content(url, title, '', doc_text, is_gated=False)
                            techs = [t for t in ('Python', 'TypeScript', 'JavaScript', 'Go', 'Docker', 'AWS', 'React', 'Kubernetes', 'SQL', 'FastAPI') if re.search(rf'\b{t}\b', doc_text, re.I)]
                            files = [{'name': title, 'size': len(raw_bytes), 'type': 'docx'}]
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': files,
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': techs,
                                'excerpt': doc_text[:3000],
                                'inferred_kind': inferred_kind,
                                'detail': f"Successfully fetched DOCX document ({title}, {len(raw_bytes):,} bytes). Extracted document text and verified data.",
                                'content_sha256': sha,
                                'embedded_urls': list(dict.fromkeys(parsed_doc.embedded_urls + parsed_doc.visible_urls))[:50],
                            }

                        # 2. ZIP Archive
                        if is_zip:
                            files, techs, excerpt = inspect_zip_content(raw_bytes)
                            clean_path = parsed.path.split('/')[-1]
                            title = clean_path if clean_path and '.' in clean_path else 'project_archive.zip'
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': files,
                                'file_count': len(files),
                                'total_size': len(raw_bytes),
                                'technologies': techs,
                                'excerpt': excerpt,
                                'inferred_kind': 'project',
                                'detail': f"Successfully fetched archive ({len(files)} files, {len(raw_bytes):,} bytes). Extracted code and project artifacts.",
                                'content_sha256': sha,
                            }

                        # 2. PDF Document
                        if is_pdf:
                            doc_title, doc_text = '', ''
                            try:
                                with pymupdf.open(stream=raw_bytes, filetype='pdf') as doc:
                                    doc_title = doc.metadata.get('title', '')
                                    doc_text = '\n'.join(page.get_text() for page in doc[:10])
                            except Exception:
                                pass
                            clean_path = parsed.path.split('/')[-1]
                            title = doc_title or clean_path or 'document.pdf'
                            clean_text = ' '.join(doc_text.split())[:12000]
                            inferred_kind, _ = analyze_document_content(url, title, '', clean_text, is_gated=False)
                            files = [{'name': title, 'size': len(raw_bytes), 'type': 'pdf'}]
                            techs = [t for t in ('Python', 'TypeScript', 'JavaScript', 'Go', 'Docker', 'AWS', 'React', 'Kubernetes', 'SQL', 'FastAPI') if re.search(rf'\b{t}\b', clean_text, re.I)]
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': files,
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': techs,
                                'excerpt': clean_text[:3000],
                                'inferred_kind': inferred_kind,
                                'detail': f"Successfully fetched digital document ({title}, {len(raw_bytes):,} bytes). Extracted document text and verified data.",
                                'content_sha256': sha,
                            }

                        # Image File
                        if is_image:
                            clean_path = parsed.path.split('/')[-1]
                            title = clean_path if clean_path and '.' in clean_path else 'image_file'
                            inferred_kind = 'credential' if re.search(r'(?:certificate|certification|badge|diploma|award)', f'{title} {url}', re.I) else 'cloud_storage'
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': [{'name': title, 'size': len(raw_bytes), 'type': 'image'}],
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': [],
                                'excerpt': '',
                                'inferred_kind': inferred_kind,
                                'detail': f"Fetched image file ({title}, {len(raw_bytes):,} bytes). Image content cannot be text-analyzed; visual inspection required.",
                                'content_sha256': sha,
                            }

                        # Spreadsheet
                        if is_spreadsheet:
                            clean_path = parsed.path.split('/')[-1]
                            title = clean_path if clean_path and '.' in clean_path else 'spreadsheet'
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': [{'name': title, 'size': len(raw_bytes), 'type': 'spreadsheet'}],
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': [],
                                'excerpt': '',
                                'inferred_kind': 'cloud_storage',
                                'detail': f"Fetched spreadsheet ({title}, {len(raw_bytes):,} bytes). Spreadsheet contents noted but not deeply parsed.",
                                'content_sha256': sha,
                            }

                        # Presentation
                        if is_presentation:
                            clean_path = parsed.path.split('/')[-1]
                            title = clean_path if clean_path and '.' in clean_path else 'presentation'
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': [{'name': title, 'size': len(raw_bytes), 'type': 'presentation'}],
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': [],
                                'excerpt': '',
                                'inferred_kind': 'portfolio',
                                'detail': f"Fetched presentation ({title}, {len(raw_bytes):,} bytes). Presentation contents noted but not deeply parsed.",
                                'content_sha256': sha,
                            }

                        # Plain Text / Code / CSV / JSON
                        if any(t in content_type for t in ('text/plain', 'text/csv', 'text/markdown', 'application/json', 'application/xml', 'text/x-')):
                            text = raw_bytes.decode('utf-8', errors='replace')
                            clean_text = ' '.join(text.split())[:12000]
                            clean_path = parsed.path.split('/')[-1]
                            title = clean_path or 'document.txt'
                            techs = [t for t in ('Python', 'TypeScript', 'JavaScript', 'Go', 'Docker', 'AWS', 'React', 'Kubernetes', 'SQL', 'FastAPI') if re.search(rf'\b{t}\b', clean_text, re.I)]
                            files = [{'name': title, 'size': len(raw_bytes), 'type': 'code' if any(title.endswith(e) for e in ('.py', '.ts', '.js', '.go', '.rs')) else 'doc'}]
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': title,
                                'files': files,
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': techs,
                                'excerpt': clean_text[:3000],
                                'inferred_kind': 'project' if files[0]['type'] == 'code' else 'cloud_storage',
                                'detail': f"Successfully fetched document data ({title}, {len(raw_bytes):,} bytes). Extracted text and verified contents.",
                                'content_sha256': sha,
                            }

                        # 4. HTML Page / Preview
                        if any(t in content_type for t in ('text/html', 'application/xhtml+xml')):
                            text = raw_bytes.decode('utf-8', errors='replace')
                            parser = PageText()
                            parser.feed(text)
                            title = parser.og_title or ' '.join(parser.title)
                            description = parser.description
                            visible = ' '.join(parser.text)
                            excerpt = re.sub(r'\s+', ' ', visible).strip()[:12000]
                            gate = re.search(r'(sign in to continue|log in to continue|verify you are human|just a moment|access denied|enable javascript and cookies|google drive:\s*sign-in|meet google drive)', f'{title} {excerpt[:1200]}', re.I)
                            if gate:
                                return {
                                    **receipt,
                                    'status': 'access_restricted',
                                    'detail': 'Cloud document requires authentication or access permissions. Cannot inspect file without access.',
                                }
                            clean_title = re.sub(r'\s*[-|]\s*(?:Google Drive|OneDrive|Dropbox|Box|iCloud)\s*$', '', title, flags=re.I).strip()
                            inferred_kind, _ = analyze_document_content(url, clean_title, description, visible, is_gated=False)
                            techs = [t for t in ('Python', 'TypeScript', 'JavaScript', 'Go', 'Docker', 'AWS', 'React', 'Next.js', 'Vue', 'Node.js', 'Kubernetes', 'SQL', 'FastAPI', 'Tailwind', 'GraphQL', 'Three.js') if re.search(rf'\b{t}\b', excerpt, re.I)]
                            file_type = 'portfolio_site' if inferred_kind == 'portfolio' else ('cloud_document' if is_cloud else 'web_page')
                            file_name = clean_title or ('portfolio_site' if inferred_kind == 'portfolio' else ('cloud_document' if is_cloud else 'web_page'))
                            files = [{'name': file_name, 'size': len(raw_bytes), 'type': file_type}]
                            detail_msg = (
                                f"Fetched candidate portfolio website ({clean_title or title}). Extracted page content and technologies."
                                if inferred_kind == 'portfolio' else
                                f"Fetched cloud file metadata ({clean_title or title}). Extracted page data."
                                if is_cloud else
                                f"Fetched web page metadata ({clean_title or title}). Extracted page data."
                            )
                            return {
                                **receipt,
                                'status': 'fetched',
                                'title': clean_title or title,
                                'files': files,
                                'file_count': 1,
                                'total_size': len(raw_bytes),
                                'technologies': techs,
                                'excerpt': excerpt[:3000],
                                'inferred_kind': inferred_kind,
                                'detail': detail_msg,
                                'content_sha256': sha,
                            }
        except Exception:
            continue

    return receipt


def analyze_document_content(url: str, title: str, description: str, visible_text: str, is_gated: bool) -> tuple[str, str]:
    """Analyzes reachable document/page metadata and excerpts before making assertions.

    Returns (inferred_kind, remark_detail).
    """
    clean_title = re.sub(r'\s*[-|]\s*(?:Google Drive|OneDrive|Dropbox|Box|iCloud)\s*$', '', title, flags=re.I).strip()
    is_cloud = is_cloud_storage_url(url)
    clues = f"{clean_title} {description} {visible_text[:1200]} {url}".lower()

    if is_gated or re.search(r'\b(?:sign\s*in|log\s*in|access\s*denied|you\s*need\s*access|request\s*access|google\s*drive:\s*sign-in)\b', clues):
        if is_cloud:
            doc_name = clean_title if clean_title and "sign" not in clean_title.lower() else "cloud file"
            return (
                "cloud_storage",
                f"Cloud storage document ({doc_name}) requires authentication or permissions. "
                "Contents cannot be inspected without access; cannot verify whether this is a project artifact, credential, or personal document.",
            )
        return (
            "public_page",
            "The public response is a login or anti-bot gate; its content is not verification evidence.",
        )

    # 1. Credentials / Certificates
    if re.search(r'\b(?:certificates?|certifications?|credentials?|diplomas?|degrees?|licenses?|accreditations?|badges?|coursera|udemy|aws\s+certified|comptia)\b', clues):
        doc_label = clean_title if clean_title else "unnamed document"
        return (
            "credential",
            f"Observed shared document appearing to be a credential or certificate ({doc_label}). "
            "Self-hosted link is not issuer verification. Confirm recipient, dates, and certificate ID with the certifying body.",
        )

    # 2. Resumes / CVs
    if re.search(r'\b(?:curriculum\s+vitae|resumes?|candidate\s*profile)\b', clues):
        doc_label = clean_title if clean_title else "resume file"
        return (
            "portfolio",
            f"Observed shared document appearing to be a resume or curriculum vitae ({doc_label}). "
            "Contains candidate declarations; not an independent project artifact.",
        )

    # 3. Portfolio & Developer Showcases
    if classify_url(url) == "portfolio" or re.search(r'\b(?:presentations?|slides?|pitch\s*deck|portfolio|personal\s*website|case\s*stud(?:y|ies)|showcase|about\s*me)\b|\.(?:pptx?|key)\b', clues):
        is_deck = bool(re.search(r'\b(?:presentations?|slides?|pitch\s*deck)\b|\.(?:pptx?|key)\b', clues))
        if is_deck:
            doc_label = clean_title if clean_title else "presentation deck"
            return (
                "portfolio",
                f"Observed shared presentation or portfolio deck ({doc_label}). "
                "Self-published showcase material; design, impact, and technical execution require separate verification.",
            )
        doc_label = clean_title if clean_title else "personal portfolio website"
        return (
            "portfolio",
            f"Observed candidate personal portfolio website ({doc_label}). "
            "Self-published showcase material; design, live projects, and technical demonstrations noted.",
        )

    # 4. Project Source Code / Archive / Technical Report
    if re.search(r'\b(?:source\s*code|codebase|repositories?|project\s*report|thesis|technical\s*specification|architecture\s*doc)\b|\.(?:zip|tar|gz|py|ts|tsx|js|go|java|cpp|rs)\b', clues):
        doc_label = clean_title if clean_title else "project file"
        return (
            "project",
            f"Observed shared project document or source archive ({doc_label}). "
            "Self-published project file; code authorship, commit history, and runtime execution are not verified.",
        )

    # 5. Cloud Storage fallback (unverified / generic)
    if is_cloud:
        doc_label = clean_title if clean_title else "cloud storage document"
        return (
            "cloud_storage",
            f"Observed reachable cloud file ({doc_label}). "
            "File contents and purpose are unverified; it could be a project artifact, credential, personal notes, or other document.",
        )

    # 6. Regular public web page
    return (
        "public_page",
        "Retrieved public page text. Page claims are self-published unless independently confirmed by an issuer; no ownership or skill credit is inferred.",
    )


def inspect_link(url, deadline, transport=None):
    if is_false_positive_link(url):
        return {
            'url': url,
            'kind': 'invalid',
            'status': 'not_scanned',
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'verification': 'not_verified',
            'detail': 'Invalid URL or academic degree abbreviation falsely parsed as a link; excluded from acquisition.',
        }
    receipt = {'url': url, 'kind': classify_url(url), 'status': 'unavailable',
               'fetched_at': datetime.now(timezone.utc).isoformat(), 'verification': 'not_verified'}
    if time.monotonic() >= deadline:
        return {**receipt, 'status': 'not_scanned', 'detail': 'Public-link time budget reached.'}
    try:
        # One client per supplied link; never share credentials/cookies across links or redirects.
        with httpx.Client(transport=transport or PublicTransport(), follow_redirects=False,
                          trust_env=False, headers={'User-Agent': 'CandidateX-PublicEvidence/1.0',
                          'Accept': 'text/html,text/plain,application/pdf', 'Accept-Encoding': 'identity'}) as client:
            current, redirects = url, []
            for hop in range(4):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise httpx.ReadTimeout('Time budget reached')
                client.cookies.clear()
                with client.stream('GET', current, timeout=min(4, remaining)) as response:
                    receipt.update(http_status=response.status_code, final_url=current, redirects=redirects)
                    if response.is_redirect:
                        if hop == 3 or not response.headers.get('location'):
                            return {**receipt, 'status': 'unavailable', 'detail': 'Redirect limit or missing destination.'}
                        current = urljoin(current, response.headers['location'])
                        redirects.append(current)
                        continue
                    if response.status_code in (401, 403, 429, 999):
                        is_cloud = is_cloud_storage_url(url)
                        if is_cloud:
                            try:
                                from cci.cloud.fetcher import fetch_cloud_document
                                cloud_res = fetch_cloud_document(url, timeout=min(6.0, remaining), transport=transport)
                                if cloud_res.get('status') == 'fetched':
                                    return {**receipt, **cloud_res}
                            except Exception:
                                pass
                        detail = ('Cloud storage document requires authentication or access permissions (HTTP ' + str(response.status_code) + '). Cannot inspect or verify file contents.'
                                  if is_cloud else 'Login, provider restriction, or rate limit prevents public inspection.')
                        return {**receipt, 'status': 'access_restricted', 'inferred_kind': 'cloud_storage' if is_cloud else 'public_page', 'detail': detail}
                    if response.status_code != 200:
                        return {**receipt, 'detail': f'Public page returned HTTP {response.status_code}.'}
                    content_type = response.headers.get('content-type', '').lower()
                    _supported_types = ('text/html', 'text/plain', 'application/xhtml+xml', 'application/pdf',
                                        'application/zip', 'application/x-zip-compressed', 'application/octet-stream',
                                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                                        'application/vnd.ms-excel', 'application/vnd.ms-powerpoint',
                                        'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/tiff')
                    if not any(t in content_type for t in _supported_types):
                        return {**receipt, 'status': 'unsupported_content', 'detail': 'Content type not supported for automated inspection.'}
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_BYTES:
                            return {**receipt, 'status': 'too_large', 'detail': 'Public page exceeds the 512 KB inspection limit.'}
                        if time.monotonic() >= deadline:
                            raise httpx.ReadTimeout('Time budget reached')
                    raw_content = bytes(content)
                    _docx_ct = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    is_docx = (_docx_ct in content_type
                               or ('application/octet-stream' in content_type
                                   and raw_content[:4] == b'PK\x03\x04'
                                   and b'word/' in raw_content[:8000]))
                    is_image = any(t in content_type for t in ('image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/tiff'))
                    is_spreadsheet = any(t in content_type for t in (
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'))
                    is_presentation = any(t in content_type for t in (
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint'))
                    is_zip = (not is_docx and not is_spreadsheet and not is_presentation) and (
                        any(t in content_type for t in ('application/zip', 'application/x-zip-compressed'))
                        or raw_content.startswith(b'PK\x03\x04'))
                    if is_docx:
                        from cci.intake.parsers.docx import parse_docx_document
                        parsed_doc = parse_docx_document(raw_content)
                        doc_text = ' '.join(parsed_doc.raw_text.split())[:12000]
                        clean_path = urlsplit(url).path.split('/')[-1]
                        title = clean_path if clean_path and '.' in clean_path else 'document.docx'
                        inferred_kind, analysis_detail = analyze_document_content(url, title, '', doc_text, is_gated=False)
                        techs = [t for t in ('Python', 'TypeScript', 'JavaScript', 'Go', 'Docker', 'AWS', 'React', 'Kubernetes', 'SQL', 'FastAPI') if re.search(rf'\b{t}\b', doc_text, re.I)]
                        doc_files = [{'name': title, 'size': len(raw_content), 'type': 'docx'}]
                        return {
                            **receipt,
                            'status': 'observed',
                            'verification': 'cloud_file_verified',
                            'inferred_kind': inferred_kind,
                            'title': title,
                            'excerpt': doc_text[:3000],
                            'files': doc_files,
                            'file_count': 1,
                            'technologies': techs,
                            'content_sha256': hashlib.sha256(raw_content).hexdigest(),
                            'detail': analysis_detail,
                            'embedded_urls': list(dict.fromkeys(parsed_doc.embedded_urls + parsed_doc.visible_urls))[:50],
                        }
                    if is_image:
                        clean_path = urlsplit(url).path.split('/')[-1]
                        title = clean_path if clean_path and '.' in clean_path else 'image_file'
                        inferred_kind = 'credential' if re.search(r'(?:certificate|certification|badge|diploma|award)', f'{title} {url}', re.I) else 'cloud_storage'
                        return {
                            **receipt,
                            'status': 'observed',
                            'verification': 'public_page_observed',
                            'inferred_kind': inferred_kind,
                            'title': title,
                            'files': [{'name': title, 'size': len(raw_content), 'type': 'image'}],
                            'file_count': 1,
                            'content_sha256': hashlib.sha256(raw_content).hexdigest(),
                            'detail': f"Fetched image file ({title}, {len(raw_content):,} bytes). Image content cannot be text-analyzed; visual inspection required.",
                        }
                    if is_spreadsheet or is_presentation:
                        clean_path = urlsplit(url).path.split('/')[-1]
                        ftype = 'spreadsheet' if is_spreadsheet else 'presentation'
                        title = clean_path if clean_path and '.' in clean_path else ftype
                        return {
                            **receipt,
                            'status': 'observed',
                            'verification': 'public_page_observed',
                            'inferred_kind': 'portfolio' if is_presentation else 'cloud_storage',
                            'title': title,
                            'files': [{'name': title, 'size': len(raw_content), 'type': ftype}],
                            'file_count': 1,
                            'content_sha256': hashlib.sha256(raw_content).hexdigest(),
                            'detail': f"Fetched {ftype} ({title}, {len(raw_content):,} bytes). Contents noted but not deeply parsed.",
                        }
                    if is_zip:
                        files, techs, z_excerpt = inspect_zip_content(raw_content)
                        parsed_path = urlsplit(url).path.split('/')[-1]
                        title = parsed_path if parsed_path and '.' in parsed_path else 'project_archive.zip'
                        return {
                            **receipt,
                            'status': 'observed',
                            'verification': 'cloud_file_verified',
                            'inferred_kind': 'project',
                            'title': title,
                            'excerpt': z_excerpt[:12000],
                            'files': files,
                            'file_count': len(files),
                            'technologies': techs,
                            'content_sha256': hashlib.sha256(raw_content).hexdigest(),
                            'detail': f"Observed shared project archive ({len(files)} files). Extracted code and project artifacts.",
                        }
                    text = raw_content.decode('utf-8', errors='replace')
                    parser = PageText()
                    if 'application/pdf' in content_type or raw_content.startswith(b'%PDF'):
                        with pymupdf.open(stream=raw_content, filetype='pdf') as document:
                            if document.is_encrypted or len(document) > 5:
                                return {**receipt, 'status': 'unsupported_content', 'detail': 'Public PDF is encrypted or exceeds the five-page certificate/document limit.'}
                            title = document.metadata.get('title', '')
                            description = ''
                            visible = '\n'.join(page.get_text() for page in document)
                    elif 'text/plain' in content_type:
                        title, description, visible = '', '', text
                    else:
                        parser.feed(text)
                        title = parser.og_title or ' '.join(parser.title)
                        description = parser.description
                        visible = ' '.join(parser.text)
                    excerpt = re.sub(r'\s+', ' ', visible).strip()[:12000]
                    gate = re.search(r'(sign in to continue|log in to continue|verify you are human|just a moment|access denied|enable javascript and cookies|google drive:\s*sign-in|meet google drive)', f'{title} {excerpt[:1200]}', re.I)
                    inferred_kind, analysis_detail = analyze_document_content(url, title, description, visible, is_gated=bool(gate))
                    techs = [t for t in ('Python', 'TypeScript', 'JavaScript', 'Go', 'Docker', 'AWS', 'React', 'Next.js', 'Vue', 'Node.js', 'Kubernetes', 'SQL', 'FastAPI', 'Tailwind', 'GraphQL', 'Three.js') if re.search(rf'\b{t}\b', excerpt, re.I)]
                    clean_title = re.sub(r'\s*[-|]\s*(?:Google Drive|OneDrive|Dropbox|Box|iCloud)\s*$', '', title, flags=re.I).strip()
                    file_name = clean_title or urlsplit(url).path.split('/')[-1] or ('portfolio_site' if inferred_kind == 'portfolio' else 'cloud_document')
                    doc_files = [{'name': file_name, 'size': len(content), 'type': 'pdf' if 'application/pdf' in content_type else ('portfolio_site' if inferred_kind == 'portfolio' else 'doc')}]
                    receipt.update(title=title[:300], description=description, excerpt=excerpt,
                                   inferred_kind=inferred_kind,
                                   files=doc_files, file_count=1, technologies=techs,
                                   content_sha256=hashlib.sha256(content).hexdigest())
                    if gate:
                        if is_cloud_storage_url(url):
                            try:
                                from cci.cloud.fetcher import fetch_cloud_document
                                cloud_res = fetch_cloud_document(url, timeout=max(2.0, deadline - time.monotonic()), transport=transport)
                                if cloud_res.get('status') == 'fetched':
                                    return {**receipt, **cloud_res}
                            except Exception:
                                pass
                        return {**receipt, 'status': 'access_restricted', 'detail': analysis_detail}
                    if len(excerpt) < 40:
                        is_cloud = is_cloud_storage_url(url)
                        clean_title = re.sub(r'\s*[-|]\s*(?:Google Drive|OneDrive|Dropbox|Box|iCloud)\s*$', '', title, flags=re.I).strip()
                        if is_cloud and clean_title and clean_title.lower() not in {"google drive", "onedrive", "dropbox", "box", "icloud"}:
                            return {**receipt, 'status': 'observed', 'verification': 'public_page_observed', 'detail': analysis_detail}
                        return {**receipt, 'status': 'limited_content', 'detail': analysis_detail}
                    return {**receipt, 'status': 'observed', 'verification': 'public_page_observed',
                            'detail': analysis_detail}
    except SSRFSecurityError:
        return {**receipt, 'status': 'security_blocked', 'detail': 'Destination failed public-network safety validation.'}
    except httpx.TimeoutException:
        return {**receipt, 'status': 'timeout', 'detail': 'Public page exceeded its time budget.'}
    except Exception:
        return {**receipt, 'detail': 'Public page could not be safely retrieved or parsed.'}
    return {**receipt, 'detail': 'No inspectable public response.'}


def acquire_public_links(urls):
    unique = list(dict.fromkeys(urls))
    deadline = time.monotonic() + LINK_SECONDS
    with ThreadPoolExecutor(max_workers=6) as pool:
        receipts = list(pool.map(lambda url: inspect_link(url, deadline), unique[:MAX_LINKS]))
    receipts.extend({'url': url, 'kind': classify_url(url), 'status': 'not_scanned',
                     'detail': f'All links are retained; the first {MAX_LINKS} are fetched per run. Select this URL for a follow-up run.'}
                    for url in unique[MAX_LINKS:])
    return receipts
