"""Technical identity linkage package exports."""

from cci.identity.linker import (
    IdentityLinkRecord,
    IdentityRecord,
    TechnicalIdentityLinker,
    extract_platform_identifier,
)

__all__ = [
    "IdentityLinkRecord",
    "IdentityRecord",
    "TechnicalIdentityLinker",
    "extract_platform_identifier",
]
