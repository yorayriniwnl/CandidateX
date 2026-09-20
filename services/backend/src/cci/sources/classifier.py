"""Repository deep vs. light scan classification."""

from dataclasses import dataclass
from urllib.parse import urlparse

from cci.domain.contracts import CandidateManifest
from cci.domain.enums import ScanDepth
from cci.intake.canonicalizer import normalize_url


@dataclass(frozen=True)
class RepositoryClassification:
    """Outcome of repository scanning depth evaluation."""

    repo_url: str
    scan_depth: ScanDepth
    is_ambiguous: bool
    rationale: str


def classify_repository_scan_depth(
    repo_url: str,
    manifest: CandidateManifest,
) -> RepositoryClassification:
    """Classifies repository into DEEP or LIGHT scan according to paper rules:

    1. Explicit CV project repo -> DEEP
    2. Remaining repo on supplied account -> LIGHT
    3. Ambiguous mapping -> uncertainty flag (never guess).
    """
    norm_target = normalize_url(repo_url) or repo_url.lower().rstrip("/")
    parsed_target = urlparse(norm_target)
    target_parts = [p for p in parsed_target.path.strip("/").split("/") if p]

    # Gather explicit candidate project links
    explicit_project_urls = set()
    for u in manifest.project_links:
        nu = normalize_url(u)
        if nu:
            explicit_project_urls.add(nu)

    # Also check github_urls that specify an exact repository (path >= 2)
    explicit_repo_urls = set()
    candidate_usernames = set()
    for u in manifest.github_urls:
        nu = normalize_url(u)
        if not nu:
            continue
        p = urlparse(nu)
        parts = [part for part in p.path.strip("/").split("/") if part]
        if len(parts) == 1:
            candidate_usernames.add(parts[0].lower())
        elif len(parts) >= 2:
            explicit_repo_urls.add(nu)
            candidate_usernames.add(parts[0].lower())

    # Check for explicit project claim URLs
    for claim in manifest.project_claims:
        claim_url = claim.get("url") or claim.get("repo_url")
        if claim_url:
            nu = normalize_url(claim_url)
            if nu:
                explicit_project_urls.add(nu)

    # 1. Explicit CV project repo -> DEEP
    if norm_target in explicit_project_urls or norm_target in explicit_repo_urls:
        return RepositoryClassification(
            repo_url=norm_target,
            scan_depth=ScanDepth.DEEP,
            is_ambiguous=False,
            rationale="Explicitly supplied CV project repository designated for deep analysis.",
        )

    # Check ownership username match
    if len(target_parts) >= 1:
        target_owner = target_parts[0].lower()
        if target_owner in candidate_usernames:
            # 2. Remaining repo on supplied account -> LIGHT
            return RepositoryClassification(
                repo_url=norm_target,
                scan_depth=ScanDepth.LIGHT,
                is_ambiguous=False,
                rationale="Repository found on candidate profile but not cited as explicit CV project.",
            )

    # 3. Ambiguous mapping -> uncertainty
    return RepositoryClassification(
        repo_url=norm_target,
        scan_depth=ScanDepth.LIGHT,
        is_ambiguous=True,
        rationale="Repository belongs to external organization or account not directly matched to candidate.",
    )
