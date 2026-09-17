"""Technical identity linkage strictly grounded in candidate-supplied evidence."""

from dataclasses import dataclass, field
from urllib.parse import urlparse
from uuid import UUID, uuid4

from cci.domain.contracts import CandidateManifest


@dataclass(frozen=True)
class IdentityLinkRecord:
    """Provenance relationship connecting an external digital identity to candidate evidence."""

    link_id: UUID
    identity_id: UUID
    source_document_id: UUID | None
    extraction_method: str  # embedded_hyperlink, visible_url, manifest_field
    confidence: float
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IdentityRecord:
    """External platform account attributed strictly through candidate-supplied evidence."""

    identity_id: UUID
    candidate_id: UUID
    platform: str
    identifier: str  # username, repo slug, or unique handle
    profile_url: str
    is_verified: bool
    links: list[IdentityLinkRecord] = field(default_factory=list)


def extract_platform_identifier(url: str, platform: str) -> str:
    """Extracts deterministic username, handle, or path identifier from a platform URL."""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    if platform == "github":
        # github.com/user or github.com/user/repo
        if len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"
        elif len(path_parts) == 1:
            return path_parts[0]
        return parsed.netloc

    elif platform == "linkedin":
        # linkedin.com/in/user
        if "in" in path_parts:
            idx = path_parts.index("in")
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
        elif path_parts:
            return path_parts[-1]
        return parsed.netloc

    elif platform == "coding_profile":
        if path_parts:
            return f"{parsed.netloc}/{path_parts[-1]}"
        return parsed.netloc

    return parsed.netloc + parsed.path


class TechnicalIdentityLinker:
    """Deterministic identity linker operating strictly under closed-world assumptions.

    INVARIANTS:
    1. No name-based internet searching or discovery is ever initiated.
    2. Identity links are generated strictly from candidate-supplied evidence.
    """

    @staticmethod
    def link_manifest_identities(
        candidate_id: UUID,
        manifest: CandidateManifest,
        source_document_id: UUID | None = None,
    ) -> list[IdentityRecord]:
        """Derives verified digital identities from candidate manifest."""
        identities: list[IdentityRecord] = []

        # Platform URL mappings
        url_groups = [
            ("github", manifest.github_urls),
            ("linkedin", manifest.linkedin_urls),
            ("coding_profile", manifest.coding_profile_urls),
            ("credential", manifest.credential_urls),
            ("deployment", manifest.deployment_urls),
            ("portfolio", manifest.portfolio_urls),
            ("project", manifest.project_links),
        ]

        for platform, urls in url_groups:
            for url in urls:
                identity_id = uuid4()
                identifier = extract_platform_identifier(url, platform)

                link_rec = IdentityLinkRecord(
                    link_id=uuid4(),
                    identity_id=identity_id,
                    source_document_id=source_document_id,
                    extraction_method="candidate_supplied_manifest",
                    confidence=1.0,
                    metadata={"raw_url": url, "platform": platform},
                )

                identities.append(
                    IdentityRecord(
                        identity_id=identity_id,
                        candidate_id=candidate_id,
                        platform=platform,
                        identifier=identifier,
                        profile_url=url,
                        is_verified=False,
                        links=[link_rec],
                    )
                )

        return identities

    @staticmethod
    def apply_correction(
        current_identities: list[IdentityRecord],
        rejected_urls: list[str],
    ) -> list[IdentityRecord]:
        """Prunes incorrectly parsed or candidate-disputed URLs without modifying historical provenance."""
        rejected_set = set(rejected_urls)
        return [
            ident
            for ident in current_identities
            if ident.profile_url not in rejected_set
        ]
