"""Fetch only explicitly supplied public GitHub accounts/repos, then inspect static files.

No search, git clone, hooks, package installation, repository execution, or arbitrary
network destinations. HTTP redirects are disabled. Archive files are copied selectively.
"""
import hashlib
import base64
import io
import json
import re
import stat
import time
import zipfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
from cci.analyzers.code.engine import run_code_intelligence
from cci.analyzers.db_test_infra_engine import run_db_test_infra_intelligence
from cci.analyzers.repository.indexer import (
    categorize_file,
    index_repository_artifacts,
)
from cci.config import settings
from cci.domain.contracts import (
    ArtifactAttribution,
    EvidenceConfidenceFactors,
    EvidenceInput,
    EvidenceRecord,
    OwnershipAssessment,
    RepositoryAssociation,
    RepositoryContribution,
)
from cci.domain.enums import ArtifactAttributionState
from cci.domain.evidence_families import build_fallback_evidence_family_identity
from cci.live.contracts import (MAX_REPOSITORIES, MAX_FILES, MAX_FILE_BYTES, MAX_ARCHIVE_BYTES,
    MAX_EXPANDED_BYTES, MAX_SECONDS, MAX_RECENT_COMMITS, MAX_ARTIFACT_ATTRIBUTION_PATHS, github_parts)
from cci.scoring.recency import calculate_elapsed_years, compute_recency_factor
from cci.scoring.reliability import compute_source_reliability
from cci.security.repository_workspace import SafeRepositoryWorkspace
from cci.live.repository_review import review_repository

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


def unknown_artifact_attribution(revision_sha, artifact_path, reason):
    return ArtifactAttribution(
        artifact_path=artifact_path,
        revision_sha=revision_sha,
        state=ArtifactAttributionState.UNKNOWN,
        ownership_score=0.0,
        attribution_confidence=0.0,
        candidate_commit_count=0,
        sampled_path_commit_count=0,
        limitations=[reason, 'GitHub account association does not verify the human behind the account.'],
    )


def commit_matches_account(commit, identity):
    author = commit.get('author') if isinstance(commit, dict) else None
    login = author.get('login') if isinstance(author, dict) else None
    return bool(identity and isinstance(login, str) and login.lower() == identity.lower())


def evidence_ids_for_fingerprints(
    analysis_run_id: UUID,
    fingerprints: Sequence[str],
) -> list[UUID]:
    """Returns unique, deterministic evidence IDs for ordered fingerprint occurrences."""
    occurrences: dict[str, int] = {}
    evidence_ids: list[UUID] = []
    for fingerprint in fingerprints:
        occurrence = occurrences.get(fingerprint, 0)
        occurrences[fingerprint] = occurrence + 1
        evidence_ids.append(
            uuid5(
                NAMESPACE_URL,
                f"{analysis_run_id}:{fingerprint}:{occurrence}",
            )
        )
    return evidence_ids


def normalized_repository_identity(source_locator: str) -> str:
    """Canonicalizes a repository URL for cluster grouping and family fallback."""
    owner, repository = github_parts(source_locator)
    if repository is None:
        raise ValueError("A repository URL is required to build a live cluster identity")
    return f"https://github.com/{owner.casefold()}/{repository.casefold()}"


def build_live_evidence_records(
    observations: Sequence[EvidenceInput],
    *,
    analysis_run_id: UUID,
    source_locator: str,
    immutable_revision: str,
    cluster_id: str,
    artifacts_by_path: Mapping[str, Any],
    snapshot_fingerprint: str,
    path_attributions: Mapping[str, ArtifactAttribution],
    commit_date: datetime,
    repository_association: RepositoryAssociation,
    repository_contribution: RepositoryContribution,
) -> list[EvidenceRecord]:
    """Converts every analyzer observation to a run-scoped immutable record."""
    prepared: list[tuple[EvidenceInput, Any, str, str]] = []
    for observation in observations:
        artifact = artifacts_by_path.get(observation.artifact_path)
        content_hash = (
            artifact.content_sha256 if artifact else snapshot_fingerprint
        )
        payload = {
            "artifact_sha256": content_hash,
            **observation.model_dump(mode="json", exclude={"observed_at"}),
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        prepared.append((observation, artifact, content_hash, fingerprint))

    evidence_ids = evidence_ids_for_fingerprints(
        analysis_run_id, [fingerprint for _, _, _, fingerprint in prepared]
    )
    records: list[EvidenceRecord] = []
    for (observation, artifact, content_hash, fingerprint), evidence_id in zip(
        prepared, evidence_ids
    ):
        artifact_attribution = path_attributions.get(observation.artifact_path)
        if artifact_attribution is None:
            artifact_attribution = unknown_artifact_attribution(
                immutable_revision,
                observation.artifact_path,
                "No path-specific commit history was available for this observation; repository contribution is not used as fallback.",
            )

        family_id = observation.evidence_family_id
        family_basis = observation.evidence_family_basis
        if family_id is None:
            identity = build_fallback_evidence_family_identity(
                source_family=observation.source_family,
                cluster_id=cluster_id,
                artifact_path=observation.artifact_path,
                capability=observation.target_capability,
                observation_type=observation.observation_type,
                fingerprint=fingerprint,
            )
            family_id = identity.evidence_family_id
            family_basis = identity.basis

        factors = EvidenceConfidenceFactors(
            artifact_integrity=1.0,
            ownership_score=artifact_attribution.ownership_score,
            recency_factor=compute_recency_factor(
                calculate_elapsed_years(commit_date), observation.target_capability
            ),
            verification_level=0.55,
            depth_specificity=0.5,
            source_reliability=compute_source_reliability(
                observation.source_family
            ).posterior_mean,
        )
        records.append(
            EvidenceRecord(
                evidence_id=evidence_id,
                fingerprint=fingerprint,
                source_family=observation.source_family,
                source_locator=source_locator,
                immutable_revision=immutable_revision,
                artifact_id=artifact.artifact_id if artifact else None,
                target_capability=observation.target_capability,
                support_score=observation.observed_score,
                is_positive_support=observation.is_positive_support,
                confidence_factors=factors,
                confidence=factors.composite_confidence,
                artifact_attribution=artifact_attribution,
                cluster_id=cluster_id,
                evidence_family_id=family_id,
                observation_type=observation.observation_type,
                evidence_family_basis=family_basis,
                provenance={
                    "artifact_path": observation.artifact_path,
                    "artifact_sha256": content_hash,
                    "symbol_or_line": observation.symbol_or_line,
                    "raw_support_text": observation.raw_support_text[:2000],
                    "extractor_version": observation.extractor_version,
                    "verification_status": "live_static_inspection",
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "commit_date": commit_date.isoformat(),
                    "artifact_url": (
                        f"{source_locator}/blob/{immutable_revision}/"
                        f"{quote(observation.artifact_path, safe='/')}"
                        if artifact
                        else source_locator
                    ),
                    "repository_association": repository_association.model_dump(
                        mode="json"
                    ),
                    "repository_contribution": repository_contribution.model_dump(
                        mode="json"
                    ),
                    "artifact_attribution": artifact_attribution.model_dump(
                        mode="json"
                    ),
                    "evidence_family_basis": family_basis,
                },
            )
        )
    return records


def get_artifact_attribution(fetcher, owner, repo, revision_sha, artifact_path, identity):
    """Reads bounded history for one path; repository-wide contribution is never a fallback."""
    if not identity:
        return unknown_artifact_attribution(
            revision_sha, artifact_path, 'No candidate-declared GitHub account was supplied.'
        ), False

    endpoint = (f'/repos/{owner}/{repo}/commits?path={quote(artifact_path, safe="/")}'
                f'&sha={revision_sha}&per_page={MAX_RECENT_COMMITS}')
    try:
        path_commits = fetcher.get(endpoint)
    except AcquisitionError as exc:
        return unknown_artifact_attribution(
            revision_sha, artifact_path,
            f'Path history was unavailable ({exc.status}); artifact attribution remains unknown.',
        ), exc.status in {'rate_limited', 'timeout', 'unavailable'}
    except (httpx.RequestError, ValueError, TypeError):
        return unknown_artifact_attribution(
            revision_sha, artifact_path, 'Path history could not be safely parsed; artifact attribution remains unknown.'
        ), True

    if not isinstance(path_commits, list) or not path_commits:
        return unknown_artifact_attribution(
            revision_sha, artifact_path, 'Path history was empty or malformed; artifact attribution remains unknown.'
        ), False
    unique_path_commits = {}
    author_missing = False
    for commit in path_commits[:MAX_RECENT_COMMITS]:
        if not isinstance(commit, dict):
            return unknown_artifact_attribution(
                revision_sha, artifact_path, 'Path history contained malformed commit metadata.'
            ), False
        commit_sha = commit.get('sha')
        if not isinstance(commit_sha, str) or not re.fullmatch('[a-fA-F0-9]{40}', commit_sha):
            return unknown_artifact_attribution(
                revision_sha, artifact_path, 'Path history contained a commit without a valid immutable SHA.'
            ), False
        author = commit.get('author')
        login = author.get('login') if isinstance(author, dict) else None
        commit_key = commit_sha.lower()
        if commit_key in unique_path_commits:
            if unique_path_commits[commit_key] != login:
                return unknown_artifact_attribution(
                    revision_sha, artifact_path, 'Duplicate commit metadata conflicted on its GitHub account.'
                ), False
            continue
        unique_path_commits[commit_key] = login
        if not isinstance(login, str) or not login:
            author_missing = True
    candidate_shas = [
        commit_sha for commit_sha, login in unique_path_commits.items()
        if isinstance(login, str) and login.lower() == identity.lower()
    ]

    path_count = len(unique_path_commits)
    if candidate_shas:
        score = len(candidate_shas) / path_count
        state = (ArtifactAttributionState.WEAK_ATTRIBUTION if score < 0.10 else
                 ArtifactAttributionState.PARTIAL_ATTRIBUTION if score < 0.80 else
                 ArtifactAttributionState.STRONG_ATTRIBUTION)
        limitations = [
            f'Attribution covers at most the latest {MAX_RECENT_COMMITS} commits touching this path; no line-level blame is asserted.',
            'A matching GitHub author account is not independent verification of the candidate identity.',
        ]
        if author_missing:
            limitations.append('Some path history entries could not be linked to an immutable GitHub account and commit SHA.')
        return ArtifactAttribution(
            artifact_path=artifact_path,
            revision_sha=revision_sha,
            state=state,
            ownership_score=score,
            attribution_confidence=0.5,
            candidate_commit_count=len(candidate_shas),
            sampled_path_commit_count=path_count,
            candidate_commit_shas=candidate_shas,
            limitations=limitations,
        ), False

    if author_missing:
        state = ArtifactAttributionState.UNKNOWN
        reason = 'Path history had entries that could not be linked to a GitHub account and immutable commit SHA.'
    elif path_count < MAX_RECENT_COMMITS:
        state = ArtifactAttributionState.UNATTRIBUTED
        reason = 'Complete available path history contains no commit linked to the declared GitHub account.'
    else:
        state = ArtifactAttributionState.REPOSITORY_ASSOCIATION_ONLY
        reason = f'No matching account appears in the latest {MAX_RECENT_COMMITS} path commits; older path history was not checked.'

    return ArtifactAttribution(
        artifact_path=artifact_path,
        revision_sha=revision_sha,
        state=state,
        ownership_score=0.0,
        attribution_confidence=0.0,
        candidate_commit_count=0,
        sampled_path_commit_count=path_count,
        limitations=[reason, 'Repository association and repository-wide contribution do not establish artifact authorship.'],
    ), False


def acquire_repository(
    fetcher,
    url,
    identity,
    association_basis,
    attribution_path_budget,
    analysis_run_id: UUID | None = None,
):
    analysis_run_id = analysis_run_id or uuid4()
    owner, repo = github_parts(url)
    metadata = fetcher.get(f'/repos/{owner}/{repo}')
    if not isinstance(metadata, dict):
        raise AcquisitionError('parse_failed', 'GitHub returned malformed repository metadata.')
    if metadata.get('private'):
        raise AcquisitionError('unavailable', 'Only public repositories are analyzed.')
    commits = fetcher.get(f'/repos/{owner}/{repo}/commits?per_page={MAX_RECENT_COMMITS}')
    if not isinstance(commits, list) or not commits:
        raise AcquisitionError('unavailable', 'No commit snapshot is available.')
    unique_commits = {}
    for commit in commits[:MAX_RECENT_COMMITS]:
        if not isinstance(commit, dict):
            raise AcquisitionError('parse_failed', 'GitHub returned malformed commit metadata.')
        commit_sha = commit.get('sha')
        if not isinstance(commit_sha, str) or not re.fullmatch('[a-fA-F0-9]{40}', commit_sha):
            raise AcquisitionError('parse_failed', 'GitHub returned an invalid commit reference.')
        unique_commits.setdefault(commit_sha.lower(), commit)
    commits = list(unique_commits.values())
    if not commits:
        raise AcquisitionError('unavailable', 'No unique commit snapshot is available.')
    sha = commits[0]['sha']
    if not re.fullmatch('[a-fA-F0-9]{40}', sha):
        raise AcquisitionError('parse_failed', 'GitHub returned an invalid commit reference.')
    candidate_commit_shas = [
        c.get('sha').lower() for c in commits
        if commit_matches_account(c, identity)
        and isinstance(c.get('sha'), str) and re.fullmatch('[a-fA-F0-9]{40}', c.get('sha', ''))
    ]
    authored = len(candidate_commit_shas)
    # A link is not identity verification. Never use repo owner as an implicit author.
    ownership = min(.9, authored / len(commits)) if identity else 0.0
    if metadata.get('fork'):
        ownership = min(.5, ownership)
    try:
        commit_date = commits[0]['commit']['committer']['date']
        if not isinstance(commit_date, str):
            raise TypeError('Commit date is missing or malformed.')
        observed_date = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise AcquisitionError('parse_failed', 'GitHub returned malformed commit date metadata.') from exc
    association = RepositoryAssociation(
        repository_url=url,
        candidate_identifier=identity or None,
        basis=association_basis,
        identity_verified=False,
        limitations=['A supplied repository URL or profile inventory link establishes association only.'],
    )
    contribution = RepositoryContribution(
        repository_url=url,
        candidate_identifier=identity or None,
        sampled_commit_count=len(commits),
        candidate_commit_count=authored,
        candidate_commit_ratio=authored / len(commits),
        candidate_commit_shas=candidate_commit_shas,
        is_fork=bool(metadata.get('fork')),
        limitations=['Recent repository commits are a contribution summary, not artifact authorship or human identity verification.'],
    )
    assessment = OwnershipAssessment(repository_url=url, candidate_identifier=identity or 'undeclared',
        ownership_score=ownership, attribution_confidence=.5 if identity else 0,
        feature_vector={'sampled_commits': len(commits), 'candidate_sampled_commits': authored,
                        'repository_commit_ratio': authored / len(commits)},
        is_fork=bool(metadata.get('fork')), model_name='DeclaredAccountRecentCommitShare',
        limitations=['Declared account association is not identity verification.',
                     'Attribution uses up to 30 recent commits; no line-level blame or full-history authorship is asserted.'])
    archive = None
    method = 'commit_archive'
    try:
        archive = fetcher.get(f'/{owner}/{repo}/zip/{sha}', archive=True)
    except AcquisitionError as exc:
        if exc.status != 'too_large':
            raise
        method = 'bounded_git_blobs'
    with SafeRepositoryWorkspace(max_worktree_bytes=MAX_EXPANDED_BYTES, max_file_bytes=MAX_FILE_BYTES,
                                 timeout_seconds=MAX_SECONDS) as workspace:
        try:
            omitted = inspect_archive(archive, workspace) if archive else inspect_git_blobs(fetcher, owner, repo, sha, workspace)
        except AcquisitionError as exc:
            if exc.status != 'too_large' or method != 'commit_archive':
                raise
            method = 'bounded_git_blobs'
            omitted = inspect_git_blobs(fetcher, owner, repo, sha, workspace)
        snapshot, artifacts = index_repository_artifacts(workspace, url, sha)
        raw = run_code_intelligence(workspace.root, url, sha, artifacts)
        raw += run_db_test_infra_intelligence(workspace.root, url, sha, artifacts)
        by_path = {a.relative_path: a for a in artifacts}
        path_scores = {}
        for observation in raw:
            if observation.artifact_path in by_path:
                path_scores[observation.artifact_path] = max(
                    path_scores.get(observation.artifact_path, 0.0), observation.observed_score
                )
        ordered_paths = sorted(path_scores, key=lambda path: (-path_scores[path], path))
        selected_paths = ordered_paths[:max(0, attribution_path_budget)]
        path_attributions, requested_paths = {}, []
        stop_path_requests = False
        for path in selected_paths:
            if stop_path_requests:
                path_attributions[path] = unknown_artifact_attribution(
                    sha, path, 'Path history requests stopped after a source or time-budget failure; repository contribution is not used as fallback.'
                )
                continue
            if identity:
                requested_paths.append(path)
            path_attribution, stop_path_requests = get_artifact_attribution(
                fetcher, owner, repo, sha, path, identity
            )
            path_attributions[path] = path_attribution
        for path in ordered_paths[len(selected_paths):]:
            path_attributions[path] = unknown_artifact_attribution(
                sha, path, 'Path history was outside the bounded request budget; repository contribution is not used as fallback.'
            )
        cluster_id = normalized_repository_identity(url)
        records = build_live_evidence_records(
            raw,
            analysis_run_id=analysis_run_id,
            source_locator=url,
            immutable_revision=sha,
            cluster_id=cluster_id,
            artifacts_by_path=by_path,
            snapshot_fingerprint=snapshot.snapshot_fingerprint,
            path_attributions=path_attributions,
            commit_date=observed_date,
            repository_association=association,
            repository_contribution=contribution,
        )
        receipt = {'url': url, 'status': 'observed', 'detail': 'Fetched public commit and statically inspected selected files.',
            'commit_sha': sha, 'fetched_at': datetime.now(timezone.utc).isoformat(), 'files_inspected': len(artifacts),
            'files_omitted': omitted, 'evidence_count': len(records), 'snapshot_fingerprint': snapshot.snapshot_fingerprint,
            'ownership_score': ownership, 'candidate_sampled_commits': authored, 'sampled_commits': len(commits),
            'repository_association': association.model_dump(mode='json'),
            'repository_contribution': contribution.model_dump(mode='json'),
            'artifact_attributions': [path_attributions[path].model_dump(mode='json') for path in ordered_paths],
            'attribution_paths_considered': len(ordered_paths),
            'attribution_paths_requested': len(requested_paths),
            'attribution_paths_deferred': max(0, len(ordered_paths) - len(selected_paths)),
            'kind': 'repository', 'acquisition_method': method,
            'repository_review': review_repository(workspace.root, artifacts, url, sha, metadata)}
    return records, assessment, receipt


def inspect_git_blobs(fetcher, owner, repo, sha, workspace):
    """For oversized archives, inspect a small selection of commit-pinned Git blobs."""
    tree = fetcher.get(f'/repos/{owner}/{repo}/git/trees/{sha}?recursive=1')
    if tree.get('truncated'):
        raise AcquisitionError('too_large', 'GitHub truncated the repository tree; a reliable bounded selection could not be made.')
    files = [item for item in tree.get('tree', []) if item.get('type') == 'blob']
    groups = {}
    for item in files:
        path = PurePosixPath(item.get('path', ''))
        if path.is_absolute() or '..' in path.parts or '\\' in str(path) or ':' in str(path):
            raise AcquisitionError('security_blocked', 'Unsafe repository tree path rejected.')
        category = categorize_file(str(path))
        if (item.get('mode') not in {'100644', '100755'} or category not in CATEGORIES
                or item.get('size', MAX_FILE_BYTES + 1) > MAX_FILE_BYTES
                or any(part.lower() in IGNORED for part in path.parts)):
            continue
        groups.setdefault(category, []).append(item)
    # Rotate file categories so manifests cannot crowd out source and test code.
    selected = []
    for items in groups.values():
        items.sort(key=lambda item: item['path'])
    while len(selected) < 12 and any(groups.values()):
        for category in CATEGORIES:
            if groups.get(category) and len(selected) < 12:
                selected.append(groups[category].pop(0))
    stored = 0
    for item in selected:
        reference = item.get('sha', '')
        if not re.fullmatch('[a-fA-F0-9]{40}', reference):
            raise AcquisitionError('parse_failed', 'Invalid Git blob reference.')
        data = fetcher.get(f'/repos/{owner}/{repo}/git/blobs/{reference}')
        if data.get('encoding') != 'base64':
            continue
        content = base64.b64decode(re.sub(r'\s', '', data.get('content', '')), validate=True)
        if len(content) > MAX_FILE_BYTES or b'\x00' in content[:8192]:
            continue
        actual = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
        if actual != reference.lower():
            raise AcquisitionError('parse_failed', 'Git blob content does not match its immutable reference.')
        destination = Path(workspace.root, item['path'])
        if not destination.resolve().is_relative_to(Path(workspace.root).resolve()):
            raise AcquisitionError('security_blocked', 'Repository tree containment check failed.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        stored += 1
    return len(files) - stored


def acquire_sources(urls, identity, analysis_run_id: UUID | None = None):
    analysis_run_id = analysis_run_id or uuid4()
    records, ownership, receipts, repos = [], [], [], []
    association_basis = {}
    fetcher = Fetcher()
    try:
        # Explicit repository links take priority over bounded profile expansion.
        repos = [u for u in urls if github_parts(u)[1]]
        association_basis.update({u.lower(): 'supplied_repository_url' for u in repos})
        profiles = [u for u in urls if not github_parts(u)[1]]
        for url in profiles:
            owner, repo = github_parts(url)
            if repo:
                continue
            try:
                profile = {}
                profile_error = None
                try:
                    info = fetcher.get(f'/users/{owner}')
                    profile = {key: info.get(key) for key in ('login', 'name', 'bio', 'company', 'blog', 'location',
                        'public_repos', 'public_gists', 'followers', 'following', 'created_at', 'updated_at', 'type')}
                except Exception as exc:
                    profile_error = error_receipt(url, exc)['detail']
                data = []
                for page in (1, 2):
                    items = fetcher.get(f'/users/{owner}/repos?sort=updated&per_page=100&type=owner&page={page}')
                    data.extend(items)
                    if len(items) < 100:
                        break
                expanded = []
                inventory = []
                for item in data:
                    if item.get('private'):
                        continue
                    name = item.get('name', '')
                    candidate_url = f'https://github.com/{owner}/{name}'
                    github_parts(candidate_url)
                    inventory.append({'url': candidate_url, 'name': name, 'description': item.get('description'),
                        'language': item.get('language'), 'stars': item.get('stargazers_count', 0),
                        'fork': bool(item.get('fork')), 'archived': bool(item.get('archived')),
                        'pushed_at': item.get('pushed_at'), 'size_kb': item.get('size'),
                        'topics': item.get('topics', [])[:20]})
                    if (len(repos) < MAX_REPOSITORIES and not item.get('fork') and not item.get('archived')
                            and candidate_url.lower() not in {r.lower() for r in repos}):
                        repos.append(candidate_url)
                        association_basis[candidate_url.lower()] = 'public_profile_inventory'
                        expanded.append(candidate_url)
                receipts.append({'url': url, 'kind': 'github_profile', 'status': 'observed' if not profile_error else 'partial',
                    'detail': 'Public profile and repository inventory retrieved; recent non-fork repositories selected within the scan budget.',
                    'profile': profile, 'profile_error': profile_error, 'inventory': inventory,
                    'inventory_truncated': len(data) == 200, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                    'expanded_repositories': expanded})
            except Exception as exc:
                receipts.append(error_receipt(url, exc))
        for url in repos[MAX_REPOSITORIES:]:
            receipts.append({'url': url, 'status': 'not_scanned', 'detail': f'Limit of {MAX_REPOSITORIES} repositories per analysis.'})
        selected_repos = repos[:MAX_REPOSITORIES]
        base_path_budget, extra_path_budget = divmod(
            MAX_ARTIFACT_ATTRIBUTION_PATHS, max(1, len(selected_repos))
        )
        for index, url in enumerate(selected_repos):
            try:
                path_budget = base_path_budget + (1 if index < extra_path_budget else 0)
                evidence, assessment, receipt = acquire_repository(
                    fetcher, url, identity,
                    association_basis=association_basis.get(url.lower(), 'selected_repository_url'),
                    attribution_path_budget=path_budget,
                    analysis_run_id=analysis_run_id,
                )
                records.extend(evidence)
                ownership.append(assessment)
                receipts.append(receipt)
            except Exception as exc:
                receipts.append(error_receipt(url, exc))
    finally:
        fetcher.close()
    scanned = {r['url'].lower(): r['status'] for r in receipts if r.get('kind') != 'github_profile'}
    for receipt in receipts:
        for repo in receipt.get('inventory', []):
            repo['inspection_status'] = scanned.get(repo['url'].lower(), 'inventory_only')
    evidence_ids = evidence_ids_for_fingerprints(
        analysis_run_id, [record.fingerprint for record in records]
    )
    records = [
        record.model_copy(update={"evidence_id": evidence_id})
        for record, evidence_id in zip(records, evidence_ids)
    ]
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
