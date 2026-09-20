"""Unit tests verifying technical identity isolation and zero external discovery."""

from uuid import uuid4
import pytest

from cci.domain.contracts import CandidateManifest
from cci.identity.linker import TechnicalIdentityLinker


def test_identity_linkage_closed_world_invariant():
    """Identity links must be derived strictly from manifest URLs, never from name discovery."""
    manifest = CandidateManifest(
        display_name="John Doe Very Famous Engineer",  # Common or famous name
        email="john.doe@example.com",
        github_urls=["https://github.com/johndoe-explicit-account"],
        project_links=["https://gitlab.com/johndoe/my-private-tool"],
        linkedin_urls=["https://linkedin.com/in/john-doe-unique-id"],
    )

    candidate_id = uuid4()
    doc_id = uuid4()
    identities = TechnicalIdentityLinker.link_manifest_identities(
        candidate_id=candidate_id,
        manifest=manifest,
        source_document_id=doc_id,
    )

    # Must produce exactly the 3 identities supplied in manifest
    assert len(identities) == 3
    platforms = {i.platform for i in identities}
    assert platforms == {"github", "project", "linkedin"}

    # Identifiers must be derived strictly from URLs
    github_ident = next(i for i in identities if i.platform == "github")
    assert github_ident.identifier == "johndoe-explicit-account"
    assert github_ident.profile_url == "https://github.com/johndoe-explicit-account"

    # Verify provenance link
    assert len(github_ident.links) == 1
    link = github_ident.links[0]
    assert link.source_document_id == doc_id
    assert link.extraction_method == "candidate_supplied_manifest"


def test_identity_correction_request_pruning():
    """Recruiter/candidate correction must safely prune disputed URLs."""
    manifest = CandidateManifest(
        display_name="Sarah Connor",
        github_urls=[
            "https://github.com/sarah-real",
            "https://github.com/sarah-connor-wrong-person",
        ],
    )
    identities = TechnicalIdentityLinker.link_manifest_identities(uuid4(), manifest)
    assert len(identities) == 2

    # Prune misattributed URL
    corrected = TechnicalIdentityLinker.apply_correction(
        current_identities=identities,
        rejected_urls=["https://github.com/sarah-connor-wrong-person"],
    )
    assert len(corrected) == 1
    assert corrected[0].profile_url == "https://github.com/sarah-real"
