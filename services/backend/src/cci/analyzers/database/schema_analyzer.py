"""Database schema, migration, and SQL static analyzer.

INVARIANT: Candidate database code or migrations are NEVER executed or applied.
All analysis is strictly static AST/regex inspection of schema definitions.
"""

import re

from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.signal_rules import signal_rule_fields

EXTRACTOR_VERSION = "1.0.0"


def analyze_sql_content(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects raw SQL schema and migration files for tables, indexes, keys, and partitioning."""
    evidence: list[EvidenceInput] = []
    lines = content.split("\n")

    for idx, line in enumerate(lines, start=1):
        trimmed = line.strip()

        # 1. CREATE TABLE
        tbl_match = re.search(
            r"\bCREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.\"`]+)",
            trimmed,
            re.IGNORECASE,
        )
        if tbl_match:
            tbl_name = tbl_match.group(2)
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.database.sql_table"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: CREATE TABLE {tbl_name}",
                    target_capability=CapabilityKey.DATABASE_ENGINEERING,
                    technical_signal_strength=72.0,
                    is_positive_support=True,
                    raw_support_text=f"SQL table definition in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 2. Indexes: CREATE INDEX, UNIQUE INDEX, Composite Indexes
        idx_match = re.search(
            r"\bCREATE\s+(UNIQUE\s+)?INDEX\s+(IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_.\"`]+)\s+ON\s+([a-zA-Z0-9_.\"`]+)\s*\(([^)]+)\)",
            trimmed,
            re.IGNORECASE,
        )
        if idx_match:
            is_unique = bool(idx_match.group(1))
            idx_name = idx_match.group(3)
            tbl_target = idx_match.group(4)
            cols = [c.strip() for c in idx_match.group(5).split(",")]
            is_composite = len(cols) > 1
            score = 86.0 if is_composite else (82.0 if is_unique else 78.0)

            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.database.sql_index"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: CREATE INDEX {idx_name}",
                    target_capability=CapabilityKey.DATABASE_ENGINEERING,
                    technical_signal_strength=score,
                    is_positive_support=True,
                    raw_support_text=f"SQL indexing strategy ({'Composite' if is_composite else 'Single-column'}) on table '{tbl_target}':\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 3. Foreign key constraints / Referential integrity
        if re.search(
            r"\bFOREIGN\s+KEY\b|\bREFERENCES\s+[a-zA-Z0-9_.\"`]+\s*\(",
            trimmed,
            re.IGNORECASE,
        ):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.database.sql_foreign_key"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: FOREIGN KEY",
                    target_capability=CapabilityKey.DATABASE_ENGINEERING,
                    technical_signal_strength=80.0,
                    is_positive_support=True,
                    raw_support_text=f"Relational foreign key integrity constraint in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

        # 4. Advanced: Partitioning / Stored Procedures / Triggers
        if re.search(
            r"\bPARTITION\s+BY\b|\bCREATE\s+TRIGGER\b|\bCREATE\s+(OR\s+REPLACE\s+)?FUNCTION\b",
            trimmed,
            re.IGNORECASE,
        ):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.database.sql_advanced_feature"),
                    source_family=SourceFamily.GITHUB,
                    source_locator=repo_url,
                    immutable_revision=commit_sha,
                    artifact_path=file_path,
                    symbol_or_line=f"Line {idx}: Advanced Database Feature",
                    target_capability=CapabilityKey.DATABASE_ENGINEERING,
                    technical_signal_strength=88.0,
                    is_positive_support=True,
                    raw_support_text=f"Advanced SQL database architecture feature in {file_path}:\n{trimmed}",
                    extractor_version=extractor_version,
                )
            )

    return evidence


def analyze_alembic_migration(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Python Alembic migration scripts for operations and bidirectional reversibility."""
    evidence: list[EvidenceInput] = []

    has_upgrade = "def upgrade()" in content
    has_downgrade = "def downgrade()" in content
    # Check if downgrade actually contains operations rather than 'pass'
    has_reversible_downgrade = False
    if has_downgrade:
        down_part = content.split("def downgrade()")[1].split("def ")[0]
        has_reversible_downgrade = (
            "op." in down_part and "pass" not in down_part.strip()
        )

    # Operations detected
    ops = re.findall(
        r"op\.(create_table|add_column|create_index|create_foreign_key|alter_column|drop_table)",
        content,
    )
    unique_ops = sorted(set(ops))

    if has_upgrade and unique_ops:
        score = 85.0 if has_reversible_downgrade else 76.0
        downgrade_desc = (
            "Fully bidirectional / reversible migration"
            if has_reversible_downgrade
            else "One-way / unreversed migration"
        )
        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.database.alembic_migration"),
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: upgrade()",
                target_capability=CapabilityKey.DATABASE_ENGINEERING,
                technical_signal_strength=score,
                is_positive_support=True,
                raw_support_text=f"Alembic migration ({downgrade_desc}) performing operations: {', '.join(unique_ops)}",
                extractor_version=extractor_version,
            )
        )

    return evidence


def analyze_prisma_schema(
    content: str,
    file_path: str,
    repo_url: str,
    commit_sha: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> list[EvidenceInput]:
    """Inspects Prisma schema.prisma for models, relations, and composite indices."""
    evidence: list[EvidenceInput] = []
    models = re.findall(r"\bmodel\s+([a-zA-Z0-9_]+)\s*\{", content)
    has_relations = "@relation" in content
    has_indices = "@@index" in content
    has_unique = "@@unique" in content

    if models:
        score = 72.0
        features = [
            f"{len(models)} models ({', '.join(models[:4])}{'...' if len(models) > 4 else ''})"
        ]
        if has_relations:
            score += 6.0
            features.append("relational references (@relation)")
        if has_indices or has_unique:
            score += 8.0
            features.append("explicit indexing (@@index / @@unique)")

        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.database.prisma_schema"),
                source_family=SourceFamily.GITHUB,
                source_locator=repo_url,
                immutable_revision=commit_sha,
                artifact_path=file_path,
                symbol_or_line=f"{file_path}: {len(models)} models",
                target_capability=CapabilityKey.DATABASE_ENGINEERING,
                technical_signal_strength=min(score, 90.0),
                is_positive_support=True,
                raw_support_text=f"Prisma ORM schema definition featuring: {'; '.join(features)}",
                extractor_version=extractor_version,
            )
        )

    return evidence
