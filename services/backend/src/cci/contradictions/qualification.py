"""Centralized qualification predicate for negative evidence records."""

from cci.domain.contracts import EvidenceRecord


def is_qualified_negative(record: EvidenceRecord) -> bool:
    """Returns True if the record is a qualified negative evidence record.

    A record qualifies as negative evidence only if its polarity is negative
    (is_positive_support is False) and it carries validated negative evidence
    details registered under an approved signal rule.
    """
    return (
        not record.is_positive_support
        and record.negative_evidence_qualification == "qualified"
    )
