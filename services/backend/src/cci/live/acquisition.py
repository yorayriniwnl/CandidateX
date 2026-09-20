"""Fetch only explicitly supplied public GitHub accounts/repos, then inspect static files.

No search, git clone, hooks, package installation, repository execution, or arbitrary
network destinations. HTTP redirects are disabled. Archive files are copied selectively.
"""
import hashlib
import io
import json
import re
import stat
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from uuid import uuid5, NAMESPACE_URL

import httpx
from cci.analyzers.code.engine import run_code_intelligence
from cci.analyzers.db_test_infra_engine import run_db_test_infra_intelligence
from cci.analyzers.repository.indexer import categorize_file, index_repository_artifacts
from cci.config import settings
from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord, OwnershipAssessment
from cci.live.contracts import (MAX_REPOSITORIES, MAX_FILES, MAX_FILE_BYTES, MAX_ARCHIVE_BYTES,
    MAX_EXPANDED_BYTES, MAX_SECONDS, github_parts)
from cci.scoring.recency import calculate_elapsed_years, compute_recency_factor
from cci.scoring.reliability import compute_source_reliability
from cci.security.repository_workspace import SafeRepositoryWorkspace

HTTP_TRANSPORT = None  # Injectable only in tests; never configurable by request input.
IGNORED = {'node_modules', 'vendor', 'dist', 'build', '.git', '.next', 'coverage', '__pycache__', '.venv', 'venv'}
CATEGORIES = {'manifests': 0, 'database': 1, 'tests': 2, 'ci': 3, 'infra': 4, 'openapi': 5, 'source': 6, 'docs': 7}


class AcquisitionError(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail
        super().__init__(detail)


class Fetcher:
    def __init__(self):
        self.deadline = time.monotonic() + MAX_SECONDS
        self.client = httpx.Client(transport=HTTP_TRANSPORT, follow_redirects=False, trust_env=False,
            headers={'User-Agent': 'CandidateX-LiveEvidence/1.0', 'Accept': 'application/vnd.github+json'})

    def close(self):
        self.client.close()

    def get(self, path, *, archive=False):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AcquisitionError('timeout', 'The live acquisition time budget was reached.')
        host = 'https://codeload.github.com' if archive else 'https://api.github.com'
        headers = {}
        if not archive and settings.GITHUB_TOKEN:
            headers['Authorization'] = f'Bearer {settings.GITHUB_TOKEN}'
        limit = MAX_ARCHIVE_BYTES if archive else 2 * 1024 * 1024
        with self.client.stream('GET', host + path, headers=headers, timeout=min(10, remaining)) as response:
            code = response.status_code
            if code in (403, 429):
                raise AcquisitionError('rate_limited', 'GitHub refused or rate-limited this request. Retry later; a server GitHub token can raise API limits.')
            if code in (401, 404):
                raise AcquisitionError('unavailable', 'Public source not found or requires authentication.')
            if 300 <= code < 400:
                raise AcquisitionError('unavailable', 'The source moved. Update the supplied URL; redirects are not followed.')
            if code != 200:
                raise AcquisitionError('unavailable', f'GitHub returned HTTP {code}.')
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > limit:
                    raise AcquisitionError('too_large', f'Source exceeds the {limit // 1024} KB transfer limit.')
                if time.monotonic() >= self.deadline:
                    raise AcquisitionError('timeout', 'The live acquisition time budget was reached.')
                chunks.append(chunk)
        content = b''.join(chunks)
        return content if archive else json.loads(content)


def inspect_archive(data, workspace):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > 20000 or sum(i.file_size for i in infos) > MAX_EXPANDED_BYTES:
            raise AcquisitionError('too_large', 'Repository exceeds the expanded archive/path limit.')
        selected, omitted = [], 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename:
                raise AcquisitionError('security_blocked', 'Unsafe archive path rejected.')
            if stat.S_ISLNK(info.external_attr >> 16):
                omitted += 1
                continue
            if info.is_dir() or len(path.parts) < 2:
                continue
            rel = PurePosixPath(*path.parts[1:]).as_posix()
            category = categorize_file(rel)
            if any(p.lower() in IGNORED for p in path.parts) or category not in CATEGORIES or info.file_size > MAX_FILE_BYTES:
                omitted += 1
                continue
            selected.append((CATEGORIES[category], rel, info))
        selected.sort(key=lambda item: (item[0], item[1]))
        omitted += max(0, len(selected) - MAX_FILES)
        for _, rel, info in selected[:MAX_FILES]:
            workspace.check_timeout()
            content = archive.read(info)
            if b'\x00' in content[:8192]:
                omitted += 1
                continue
            dest = Path(workspace.root, rel)
            if not dest.resolve().is_relative_to(Path(workspace.root).resolve()):
                raise AcquisitionError('security_blocked', 'Archive containment check failed.')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        return omitted


def acquire_repository(fetcher, url, identity):
    owner, repo = github_parts(url)
    metadata = fetcher.get(f'/repos/{owner}/{repo}')
    if metadata.get('private'):
        raise AcquisitionError('unavailable', 'Only public repositories are analyzed.')
    commits = fetcher.get(f'/repos/{owner}/{repo}/commits?per_page=30')
    if not isinstance(commits, list) or not commits:
        raise AcquisitionError('unavailable', 'No commit snapshot is available.')
    sha = commits[0].get('sha', '')
    if not re.fullmatch('[a-fA-F0-9]{40}', sha):
        raise AcquisitionError('parse_failed', 'GitHub returned an invalid commit reference.')
    authored = sum(1 for c in commits if identity and (c.get('author') or {}).get('login', '').lower() == identity.lower())
    # A link is not identity verification. Never use repo owner as an implicit author.
    ownership = min(.9, authored / len(commits)) if identity else 0.0
    if metadata.get('fork'):
        ownership = min(.5, ownership)
    observed_date = datetime.fromisoformat(commits[0]['commit']['committer']['date'].replace('Z', '+00:00'))
    assessment = OwnershipAssessment(repository_url=url, candidate_identifier=identity or 'undeclared',
        ownership_score=ownership, attribution_confidence=.5 if identity else 0,
        feature_vector={'sampled_commits': len(commits), 'candidate_sampled_commits': authored},
        is_fork=bool(metadata.get('fork')), model_name='DeclaredAccountRecentCommitShare',
        limitations=['Declared account association is not identity verification.',
                     'Attribution uses up to 30 recent commits; no line-level blame or full-history authorship is asserted.'])
    archive = fetcher.get(f'/{owner}/{repo}/zip/{sha}', archive=True)
    with SafeRepositoryWorkspace(max_worktree_bytes=MAX_EXPANDED_BYTES, max_file_bytes=MAX_FILE_BYTES,
                                 timeout_seconds=MAX_SECONDS) as workspace:
        omitted = inspect_archive(archive, workspace)
        snapshot, artifacts = index_repository_artifacts(workspace, url, sha)
        raw = run_code_intelligence(workspace.root, url, sha, artifacts)
        raw += run_db_test_infra_intelligence(workspace.root, url, sha, artifacts)
        by_path = {a.relative_path: a for a in artifacts}
        records, seen, per_group = [], set(), Counter()
        for observation in raw:
            artifact = by_path.get(observation.artifact_path)
            # Structural observations spanning paths use the actual snapshot hash.
            content_hash = artifact.content_sha256 if artifact else snapshot.snapshot_fingerprint
            group = (observation.artifact_path, observation.target_capability)
            payload = {'artifact_sha256': content_hash, **observation.model_dump(mode='json', exclude={'observed_at'})}
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if fingerprint in seen or per_group[group] >= 2 or len(records) >= 180:
                continue
            seen.add(fingerprint)
            per_group[group] += 1
            factors = EvidenceConfidenceFactors(artifact_integrity=1.0, ownership_score=ownership,
                recency_factor=compute_recency_factor(calculate_elapsed_years(observed_date), observation.target_capability),
                verification_level=.55, depth_specificity=.5,
                source_reliability=compute_source_reliability(observation.source_family).posterior_mean)
            records.append(EvidenceRecord(evidence_id=uuid5(NAMESPACE_URL, fingerprint), fingerprint=fingerprint,
                source_family=observation.source_family, source_locator=url, immutable_revision=sha,
                artifact_id=artifact.artifact_id if artifact else None, target_capability=observation.target_capability,
                support_score=observation.observed_score, is_positive_support=observation.is_positive_support,
                confidence_factors=factors, confidence=factors.composite_confidence, cluster_id=url,
                provenance={'artifact_path': observation.artifact_path, 'artifact_sha256': content_hash,
                    'symbol_or_line': observation.symbol_or_line, 'raw_support_text': observation.raw_support_text[:2000],
                    'extractor_version': observation.extractor_version, 'verification_status': 'live_static_inspection',
                    'observed_at': datetime.now(timezone.utc).isoformat(), 'commit_date': observed_date.isoformat(),
                    'artifact_url': f'{url}/blob/{sha}/{quote(observation.artifact_path, safe="/")}' if artifact else url,
                    'ownership_basis': assessment.model_dump(mode='json')}))
        receipt = {'url': url, 'status': 'observed', 'detail': 'Fetched public commit and statically inspected selected files.',
            'commit_sha': sha, 'fetched_at': datetime.now(timezone.utc).isoformat(), 'files_inspected': len(artifacts),
            'files_omitted': omitted, 'evidence_count': len(records), 'snapshot_fingerprint': snapshot.snapshot_fingerprint,
            'ownership_score': ownership, 'candidate_sampled_commits': authored, 'sampled_commits': len(commits)}
    return records, assessment, receipt


def acquire_sources(urls, identity):
    records, ownership, receipts, repos = [], [], [], []
    fetcher = Fetcher()
    try:
        # Explicit repository links take priority over bounded profile expansion.
        repos = [u for u in urls if github_parts(u)[1]]
        for url in urls:
            owner, repo = github_parts(url)
            if repo:
                continue
            if len(repos) >= MAX_REPOSITORIES:
                receipts.append({'url': url, 'status': 'not_scanned', 'detail': 'Explicit repository links filled the scan budget.'})
                continue
            try:
                data = fetcher.get(f'/users/{owner}/repos?sort=updated&per_page=30&type=owner')
                expanded = []
                for item in data:
                    if item.get('private') or item.get('fork') or item.get('archived'):
                        continue
                    name = item.get('name', '')
                    candidate_url = f'https://github.com/{owner}/{name}'
                    github_parts(candidate_url)
                    if candidate_url.lower() not in {r.lower() for r in repos}:
                        repos.append(candidate_url)
                        expanded.append(candidate_url)
                    if len(repos) >= MAX_REPOSITORIES:
                        break
                receipts.append({'url': url, 'status': 'observed', 'detail': 'Listed public owned repositories; newest non-fork repositories selected within the scan budget.', 'expanded_repositories': expanded})
            except Exception as exc:
                receipts.append(error_receipt(url, exc))
        for url in repos[MAX_REPOSITORIES:]:
            receipts.append({'url': url, 'status': 'not_scanned', 'detail': f'Limit of {MAX_REPOSITORIES} repositories per analysis.'})
        for url in repos[:MAX_REPOSITORIES]:
            try:
                evidence, assessment, receipt = acquire_repository(fetcher, url, identity)
                records.extend(evidence)
                ownership.append(assessment)
                receipts.append(receipt)
            except Exception as exc:
                receipts.append(error_receipt(url, exc))
    finally:
        fetcher.close()
    return records, ownership, receipts


def error_receipt(url, exc):
    if isinstance(exc, AcquisitionError):
        status, detail = exc.status, exc.detail
    elif isinstance(exc, httpx.TimeoutException):
        status, detail = 'timeout', 'GitHub request timed out; retry this source later.'
    elif isinstance(exc, httpx.RequestError):
        status, detail = 'unavailable', 'The public source could not be reached.'
    else:
        status, detail = 'parse_failed', 'This source could not be safely parsed or analyzed.'
    return {'url': url, 'status': status, 'detail': detail, 'evidence_count': 0}
