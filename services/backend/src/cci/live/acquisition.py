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
    ArtifactRecency,
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
from cci.contradictions.candidates import evaluate_repository_candidates
from cci.contradictions.expectations import ObservableClaimExpectation
from cci.live.scan_inventory import IGNORED_COMPONENTS, InventoryCounter, report_is_parseable
from cci.security.repository_workspace import WorkspaceSecurityError

HTTP_TRANSPORT = None  # Injectable only in tests; never configurable by request input.
IGNORED = IGNORED_COMPONENTS
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
    inventory = InventoryCounter()
    if data is None:
        inventory.inventory_complete = False
        return 0, inventory.receipt()
    try:
        archive_file = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        inventory.inventory_complete = False
        return 0, inventory.receipt()
    with archive_file as archive:
        infos = archive.infolist()
        if len(infos) > 20000 or sum(i.file_size for i in infos) > MAX_EXPANDED_BYTES:
            raise AcquisitionError('too_large', 'Repository exceeds the expanded archive/path limit.')
        selected, omitted = [], 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if info.is_dir() or len(path.parts) < 2:
                continue
            rel = PurePosixPath(*path.parts[1:]).as_posix()
            categories = inventory.add(rel)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or ':' in info.filename:
                inventory.inventory_complete = False
                inventory.skip(categories, 'unsafe_symlink')
                raise AcquisitionError('security_blocked', 'Unsafe archive path rejected.')
            if stat.S_ISLNK(info.external_attr >> 16):
                inventory.skip(categories, 'unsafe_symlink')
                omitted += 1
                continue
            category = categorize_file(rel)
            if any(p.lower() in IGNORED for p in path.parts) and not any(c in categories for c in ('coverage', 'benchmark')):
                omitted += 1
                continue
            if info.file_size > MAX_FILE_BYTES:
                inventory.skip(categories, 'byte_cap')
                omitted += 1
                continue
            if category not in CATEGORIES and not categories:
                omitted += 1
                continue
            priority = CATEGORIES.get(category, 0 if any(c in categories for c in ('coverage', 'benchmark')) else CATEGORIES['source'])
            selected.append((priority, rel, info, categories))
        selected.sort(key=lambda item: (item[0], item[1]))
        omitted += max(0, len(selected) - MAX_FILES)
        for _, _, _, categories in selected[MAX_FILES:]:
            inventory.skip(categories, 'file_cap')
        for index, (_, rel, info, categories) in enumerate(selected[:MAX_FILES]):
            try:
                workspace.check_timeout()
                content = archive.read(info)
            except WorkspaceSecurityError:
                for _, _, _, remaining in selected[index:MAX_FILES]:
                    inventory.skip(remaining, 'timeout')
                omitted += MAX_FILES - index
                break
            except (OSError, RuntimeError, zipfile.BadZipFile):
                inventory.skip(categories, 'decode_parse_failure')
                omitted += 1
                continue
            if len(content) > MAX_FILE_BYTES:
                inventory.skip(categories, 'byte_cap')
                omitted += 1
                continue
            try:
                content.decode('utf-8')
            except UnicodeDecodeError:
                inventory.skip(categories, 'decode_parse_failure')
                omitted += 1
                continue
            if b'\x00' in content[:8192]:
                inventory.skip(categories, 'decode_parse_failure')
                omitted += 1
                continue
            if not report_is_parseable(rel, content):
                inventory.skip(categories, 'decode_parse_failure')
                omitted += 1
                continue
            dest = Path(workspace.root, rel)
            if not dest.resolve().is_relative_to(Path(workspace.root).resolve()):
                inventory.inventory_complete = False
                inventory.skip(categories, 'unsafe_symlink')
                omitted += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            inventory.inspect(categories)
        return omitted, inventory.receipt()


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
    artifact_recencies: Mapping[str, ArtifactRecency],
    repository_last_activity: datetime | None,
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
            **observation.model_dump(
                mode="json", exclude={"observed_at", "signal_rule_id", "signal_rule_version"}
            ),
        }
        payload["observed_score"] = payload.pop("technical_signal_strength")
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
        if observation.artifact_path is None:
            artifact_attribution = None
            artifact_recency = None
            ownership_factor = repository_contribution.candidate_commit_ratio
            recency_factor = 1.0
        else:
            artifact_attribution = path_attributions.get(observation.artifact_path)
            if artifact_attribution is None:
                artifact_attribution = unknown_artifact_attribution(
                    immutable_revision,
                    observation.artifact_path,
                    "No path-specific commit history was available for this observation; repository contribution is not used as fallback.",
                )
            artifact_recency = artifact_recencies.get(observation.artifact_path)
            if artifact_recency is None:
                artifact_recency = unknown_artifact_recency(
                    repository_last_activity,
                    "Path history was unavailable or outside the bounded request budget; repository activity is not used as artifact recency.",
                )
            ownership_factor = artifact_attribution.ownership_score
            recency_factor = (
                compute_recency_factor(
                    calculate_elapsed_years(
                        artifact_recency.last_meaningful_modification_at
                    ),
                    observation.target_capability,
                )
                if artifact_recency.state == "known"
                else 1.0
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
            ownership_score=ownership_factor,
            recency_factor=recency_factor,
            verification_level=0.55,
            depth_specificity=0.5,
            source_reliability=compute_source_reliability(
                observation.source_family
            ).posterior_mean,
        )
        provenance = {
            "artifact_path": observation.artifact_path,
            "artifact_sha256": content_hash,
            "symbol_or_line": observation.symbol_or_line,
            "raw_support_text": observation.raw_support_text[:2000],
            "extractor_version": observation.extractor_version,
            "signal_rule_id": observation.signal_rule_id or "legacy_unknown",
            "signal_rule_version": observation.signal_rule_version or "legacy_unknown",
            "verification_status": "live_static_inspection",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "artifact_recency": (
                artifact_recency.model_dump(mode="json")
                if artifact_recency is not None
                else None
            ),
            "artifact_url": (
                f"{source_locator}/blob/{immutable_revision}/"
                f"{quote(observation.artifact_path, safe='/')}"
                if artifact and observation.artifact_path
                else source_locator
            ),
            "repository_association": repository_association.model_dump(
                mode="json"
            ),
            "repository_contribution": repository_contribution.model_dump(
                mode="json"
            ),
            "artifact_attribution": (
                artifact_attribution.model_dump(mode="json")
                if artifact_attribution is not None
                else None
            ),
            "evidence_family_basis": family_basis,
        }
        if observation.negative_evidence_details is not None:
            provenance["negative_evidence_details"] = observation.negative_evidence_details.model_dump(mode="json")
            provenance["negative_evidence_qualification"] = observation.negative_evidence_qualification
            if observation.artifact_path is None:
                provenance["ownership_basis"] = "repository_candidate_commit_ratio"
                provenance["ownership_limitations"] = [
                    "Repository commit ratio is used as ownership factor for repository-scope negative observation; it is not artifact authorship."
                ]
        records.append(
            EvidenceRecord(
                evidence_id=evidence_id,
                fingerprint=fingerprint,
                source_family=observation.source_family,
                source_locator=source_locator,
                immutable_revision=immutable_revision,
                artifact_id=artifact.artifact_id if artifact else None,
                target_capability=observation.target_capability,
                technical_signal_strength=observation.technical_signal_strength,
                is_positive_support=observation.is_positive_support,
                negative_evidence_details=observation.negative_evidence_details,
                confidence_factors=factors,
                confidence=factors.composite_confidence,
                artifact_attribution=artifact_attribution,
                artifact_recency=artifact_recency,
                cluster_id=cluster_id,
                evidence_family_id=family_id,
                observation_type=observation.observation_type,
                evidence_family_basis=family_basis,
                provenance=provenance,
            )
        )
    return records


def unknown_artifact_recency(repository_last_activity, reason):
    """Creates an explicit unknown state without substituting repository activity."""
    return ArtifactRecency(
        state="artifact_recency_unknown",
        repository_last_activity=repository_last_activity,
        limitations=[
            reason,
            "Repository last activity is retained separately and is not artifact recency.",
            "No freshness claim is made; the neutral recency factor must not be interpreted as recent activity.",
        ],
    )


def fetch_artifact_path_history(fetcher, owner, repo, revision_sha, artifact_path):
    """Fetches one bounded path history for both recency and attribution decisions."""
    endpoint = (
        f'/repos/{owner}/{repo}/commits?path={quote(artifact_path, safe="/")}'
        f'&sha={revision_sha}&per_page={MAX_RECENT_COMMITS}'
    )
    try:
        path_commits = fetcher.get(endpoint)
    except AcquisitionError as exc:
        return None, f"Path history was unavailable ({exc.status}).", exc.status in {
            "rate_limited",
            "timeout",
            "unavailable",
        }
    except (httpx.RequestError, ValueError, TypeError):
        return None, "Path history could not be safely parsed.", True
    if not isinstance(path_commits, list):
        return None, "Path history response was malformed.", False
    if not path_commits:
        return None, "Path history was empty.", False
    return path_commits[:MAX_RECENT_COMMITS], None, False


def _parse_github_timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_artifact_recency(
    path_commits,
    identity,
    repository_last_activity,
    history_error=None,
):
    """Derives modification dates only from commit history for the exact artifact path."""
    if history_error:
        return unknown_artifact_recency(repository_last_activity, history_error)
    if not isinstance(path_commits, list) or not path_commits:
        return unknown_artifact_recency(
            repository_last_activity,
            "No usable path-specific history was available for this artifact.",
        )

    unique = {}
    for commit in path_commits[:MAX_RECENT_COMMITS]:
        if not isinstance(commit, dict):
            return unknown_artifact_recency(
                repository_last_activity,
                "Path history contained malformed commit metadata.",
            )
        commit_sha = commit.get("sha")
        if not isinstance(commit_sha, str) or not re.fullmatch(
            r"[a-fA-F0-9]{40}", commit_sha
        ):
            return unknown_artifact_recency(
                repository_last_activity,
                "Path history contained a commit without a valid immutable SHA.",
            )
        commit_details = commit.get("commit")
        committer = commit_details.get("committer") if isinstance(commit_details, dict) else None
        raw_date = committer.get("date") if isinstance(committer, dict) else None
        modified_at = _parse_github_timestamp(raw_date)
        if modified_at is None:
            return unknown_artifact_recency(
                repository_last_activity,
                "Path history contained a commit without a usable committer timestamp.",
            )
        author = commit.get("author")
        login = author.get("login") if isinstance(author, dict) else None
        normalized_sha = commit_sha.lower()
        entry = (modified_at, login)
        if normalized_sha in unique and unique[normalized_sha] != entry:
            return unknown_artifact_recency(
                repository_last_activity,
                "Duplicate path-history rows conflicted on timestamp or GitHub account.",
            )
        unique[normalized_sha] = entry

    if not unique:
        return unknown_artifact_recency(
            repository_last_activity,
            "Path history had no valid commit rows.",
        )

    latest_sha, (latest_at, _) = max(
        unique.items(), key=lambda item: (item[1][0], item[0])
    )
    matching = [
        (commit_sha, modified_at)
        for commit_sha, (modified_at, login) in unique.items()
        if identity and isinstance(login, str) and login.casefold() == identity.casefold()
    ]
    candidate_contribution_at = None
    candidate_contribution_sha = None
    if matching:
        candidate_contribution_sha, candidate_contribution_at = max(
            matching, key=lambda item: (item[1], item[0])
        )

    limitations = [
        f"Artifact recency uses at most the latest {MAX_RECENT_COMMITS} commits touching this path.",
        "A matching GitHub account is not independent verification of the candidate's human identity.",
        "Git committer timestamps are repository metadata and are not independently time-attested.",
    ]
    if any(not isinstance(login, str) or not login for _, login in unique.values()):
        limitations.append(
            "Some path commits have no linked GitHub account; candidate contribution time may be incomplete."
        )
        candidate_contribution_at = None
        candidate_contribution_sha = None

    return ArtifactRecency(
        state="known",
        last_meaningful_modification_at=latest_at,
        last_meaningful_revision_sha=latest_sha,
        candidate_contribution_at=candidate_contribution_at,
        candidate_contribution_revision_sha=candidate_contribution_sha,
        repository_last_activity=repository_last_activity,
        limitations=limitations,
    )


def get_artifact_attribution(
    fetcher,
    owner,
    repo,
    revision_sha,
    artifact_path,
    identity,
    path_commits=None,
    history_error=None,
    history_stop_requests=False,
):
    """Reads bounded path history; repository-wide contribution is never a fallback."""
    if not identity:
        return unknown_artifact_attribution(
            revision_sha, artifact_path, 'No candidate-declared GitHub account was supplied.'
        ), False

    if history_error:
        return unknown_artifact_attribution(
            revision_sha, artifact_path,
            f'{history_error} Artifact attribution remains unknown.',
        ), history_stop_requests
    if path_commits is None:
        path_commits, history_error, history_stop_requests = fetch_artifact_path_history(
            fetcher, owner, repo, revision_sha, artifact_path
        )
    if history_error:
        return unknown_artifact_attribution(
            revision_sha, artifact_path,
            f'{history_error} Artifact attribution remains unknown.',
        ), history_stop_requests

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
    observable_expectations: Sequence[ObservableClaimExpectation] = (),
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
    latest_commit_details = commits[0].get('commit')
    latest_committer = (
        latest_commit_details.get('committer')
        if isinstance(latest_commit_details, dict)
        else None
    )
    repository_last_activity = _parse_github_timestamp(
        latest_committer.get('date') if isinstance(latest_committer, dict) else None
    )
    if repository_last_activity is None:
        repository_last_activity = _parse_github_timestamp(metadata.get('pushed_at'))
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
            omitted, completeness = inspect_archive(archive, workspace) if archive else inspect_git_blobs(fetcher, owner, repo, sha, workspace)
        except AcquisitionError as exc:
            if exc.status != 'too_large' or method != 'commit_archive':
                raise
            method = 'bounded_git_blobs'
            omitted, completeness = inspect_git_blobs(fetcher, owner, repo, sha, workspace)
        if not completeness.inventory_complete:
            raise AcquisitionError('too_large', 'Repository inventory was missing or truncated; no reliable selection can be made.')
        snapshot, artifacts = index_repository_artifacts(workspace, url, sha)
        raw = run_code_intelligence(workspace.root, url, sha, artifacts)
        raw += run_db_test_infra_intelligence(workspace.root, url, sha, artifacts)
        artifacts_bytes = {
            artifact.relative_path: (Path(workspace.root) / artifact.relative_path).read_bytes()
            for artifact in artifacts
            if (Path(workspace.root) / artifact.relative_path).is_file()
        }
        negative_candidates = evaluate_repository_candidates(
            observable_expectations, url, sha, artifacts_bytes, completeness
        )
        if negative_candidates:
            raw.extend(negative_candidates)
        by_path = {a.relative_path: a for a in artifacts}
        path_scores = {}
        for observation in raw:
            if observation.artifact_path in by_path:
                path_scores[observation.artifact_path] = max(
                    path_scores.get(observation.artifact_path, 0.0), observation.technical_signal_strength
                )
        ordered_paths = sorted(path_scores, key=lambda path: (-path_scores[path], path))
        selected_paths = ordered_paths[:max(0, attribution_path_budget)]
        path_attributions, artifact_recencies = {}, {}
        requested_paths, history_paths_requested = [], []
        stop_path_requests = False
        for path in selected_paths:
            if stop_path_requests:
                path_attributions[path] = unknown_artifact_attribution(
                    sha, path, 'Path history requests stopped after a source or time-budget failure; repository contribution is not used as fallback.'
                )
                artifact_recencies[path] = unknown_artifact_recency(
                    repository_last_activity,
                    'Path history requests stopped after a source or time-budget failure; repository activity is not used as artifact recency.',
                )
                continue
            if identity:
                requested_paths.append(path)
            history_paths_requested.append(path)
            path_commits, history_error, stop_path_requests = fetch_artifact_path_history(
                fetcher, owner, repo, sha, path
            )
            artifact_recencies[path] = build_artifact_recency(
                path_commits,
                identity,
                repository_last_activity,
                history_error=history_error,
            )
            path_attribution, attribution_stop_requests = get_artifact_attribution(
                fetcher,
                owner,
                repo,
                sha,
                path,
                identity,
                path_commits=path_commits,
                history_error=history_error,
                history_stop_requests=stop_path_requests,
            )
            path_attributions[path] = path_attribution
            stop_path_requests = stop_path_requests or attribution_stop_requests
        for path in ordered_paths[len(selected_paths):]:
            path_attributions[path] = unknown_artifact_attribution(
                sha, path, 'Path history was outside the bounded request budget; repository contribution is not used as fallback.'
            )
            artifact_recencies[path] = unknown_artifact_recency(
                repository_last_activity,
                'Path history was outside the bounded request budget; repository activity is not used as artifact recency.',
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
            artifact_recencies=artifact_recencies,
            repository_last_activity=repository_last_activity,
            repository_association=association,
            repository_contribution=contribution,
        )
        receipt = {'url': url, 'status': 'observed', 'detail': 'Fetched public commit and statically inspected selected files.',
            'commit_sha': sha, 'fetched_at': datetime.now(timezone.utc).isoformat(), 'files_inspected': len(artifacts),
            'repository_last_activity': (
                repository_last_activity.isoformat()
                if repository_last_activity is not None
                else None
            ),
            'files_omitted': omitted, 'evidence_count': len(records), 'snapshot_fingerprint': snapshot.snapshot_fingerprint,
            'ownership_score': ownership, 'candidate_sampled_commits': authored, 'sampled_commits': len(commits),
            'repository_association': association.model_dump(mode='json'),
            'repository_contribution': contribution.model_dump(mode='json'),
            'artifact_attributions': [path_attributions[path].model_dump(mode='json') for path in ordered_paths],
            'artifact_recencies': [
                {
                    'artifact_path': path,
                    **artifact_recencies[path].model_dump(mode='json'),
                }
                for path in ordered_paths
            ],
            'attribution_paths_considered': len(ordered_paths),
            'attribution_paths_requested': len(requested_paths),
            'artifact_recency_paths_requested': len(history_paths_requested),
            'attribution_paths_deferred': max(0, len(ordered_paths) - len(selected_paths)),
            'kind': 'repository', 'acquisition_method': method,
            'repository_review': review_repository(workspace.root, artifacts, url, sha, metadata)}
    return records, assessment, receipt


def inspect_git_blobs(fetcher, owner, repo, sha, workspace):
    """For oversized archives, inspect a small selection of commit-pinned Git blobs."""
    inventory = InventoryCounter()
    tree = fetcher.get(f'/repos/{owner}/{repo}/git/trees/{sha}?recursive=1')
    if not isinstance(tree, dict) or not isinstance(tree.get('tree'), list) or tree.get('truncated'):
        inventory.inventory_complete = False
        return 0, inventory.receipt()
    files = [item for item in tree.get('tree', []) if item.get('type') == 'blob']
    groups = {}
    for item in files:
        path = PurePosixPath(item.get('path', ''))
        categories = inventory.add(str(path))
        if path.is_absolute() or '..' in path.parts or '\\' in str(path) or ':' in str(path):
            inventory.inventory_complete = False
            inventory.skip(categories, 'unsafe_symlink')
            continue
        category = categorize_file(str(path))
        if item.get('mode') not in {'100644', '100755'}:
            inventory.skip(categories, 'unsafe_symlink')
            continue
        if (any(part.lower() in IGNORED for part in path.parts)
                and not any(c in categories for c in ('coverage', 'benchmark'))):
            continue
        size = item.get('size')
        if not isinstance(size, int) or size > MAX_FILE_BYTES:
            inventory.skip(categories, 'byte_cap')
            continue
        if category not in CATEGORIES and not categories:
            continue
        group = category if category in CATEGORIES else 'reports' if any(c in categories for c in ('coverage', 'benchmark')) else 'source'
        groups.setdefault(group, []).append((item, categories))
    # Rotate file categories so manifests cannot crowd out source and test code.
    selected = []
    for items in groups.values():
        items.sort(key=lambda entry: entry[0]['path'])
    while len(selected) < 12 and any(groups.values()):
        for category in (*CATEGORIES, 'reports'):
            if groups.get(category) and len(selected) < 12:
                selected.append(groups[category].pop(0))
    for remaining in groups.values():
        for _, categories in remaining:
            inventory.skip(categories, 'file_cap')
    stored = 0
    for index, (item, categories) in enumerate(selected):
        try:
            workspace.check_timeout()
        except WorkspaceSecurityError:
            for _, remaining in selected[index:]:
                inventory.skip(remaining, 'timeout')
            break
        reference = item.get('sha', '')
        if not re.fullmatch('[a-fA-F0-9]{40}', reference):
            inventory.skip(categories, 'decode_parse_failure')
            continue
        try:
            data = fetcher.get(f'/repos/{owner}/{repo}/git/blobs/{reference}')
            if not isinstance(data, dict) or data.get('encoding') != 'base64':
                inventory.skip(categories, 'unsupported_format')
                continue
            content = base64.b64decode(re.sub(r'\s', '', data.get('content', '')), validate=True)
        except AcquisitionError as exc:
            if exc.status == 'security_blocked':
                raise
            if exc.status in {'timeout', 'rate_limited'}:
                reason = 'timeout' if exc.status == 'timeout' else 'unreadable'
                for _, remaining in selected[index:]:
                    inventory.skip(remaining, reason)
                break
            inventory.skip(categories, 'byte_cap' if exc.status == 'too_large' else 'unreadable')
            continue
        except (TypeError, ValueError, base64.binascii.Error):
            inventory.skip(categories, 'decode_parse_failure')
            continue
        if len(content) > MAX_FILE_BYTES:
            inventory.skip(categories, 'byte_cap')
            continue
        try:
            content.decode('utf-8')
        except UnicodeDecodeError:
            inventory.skip(categories, 'decode_parse_failure')
            continue
        if b'\x00' in content[:8192]:
            inventory.skip(categories, 'decode_parse_failure')
            continue
        if not report_is_parseable(item['path'], content):
            inventory.skip(categories, 'decode_parse_failure')
            continue
        actual = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
        if actual != reference.lower():
            raise AcquisitionError('parse_failed', 'Git blob content does not match its immutable reference.')
        destination = Path(workspace.root, item['path'])
        if not destination.resolve().is_relative_to(Path(workspace.root).resolve()):
            inventory.inventory_complete = False
            inventory.skip(categories, 'unsafe_symlink')
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        inventory.inspect(categories)
        stored += 1
    return len(files) - stored, inventory.receipt()


def acquire_sources(
    urls,
    identity,
    analysis_run_id: UUID | None = None,
    observable_expectations: Sequence[ObservableClaimExpectation] = (),
):
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
                    observable_expectations=observable_expectations,
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
