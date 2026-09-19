"""Job description parser converting raw JD text into NormalizedRequirement objects."""

import re
from uuid import uuid4

from cci.domain.contracts import NormalizedRequirement
from cci.domain.enums import CapabilityKey, RequirementPriority

# Controlled synonym ontology mapping technical terms and keywords to canonical capabilities
CONTROLLED_SYNONYM_MAP: dict[str, tuple[CapabilityKey, float]] = {
    # Backend Engineering
    "python": (CapabilityKey.BACKEND_ENGINEERING, 0.7),
    "java": (CapabilityKey.BACKEND_ENGINEERING, 0.7),
    "golang": (CapabilityKey.BACKEND_ENGINEERING, 0.8),
    "go": (CapabilityKey.BACKEND_ENGINEERING, 0.6),
    "c++": (CapabilityKey.BACKEND_ENGINEERING, 0.8),
    "rust": (CapabilityKey.BACKEND_ENGINEERING, 0.8),
    "fastapi": (CapabilityKey.BACKEND_ENGINEERING, 0.9),
    "django": (CapabilityKey.BACKEND_ENGINEERING, 0.85),
    "flask": (CapabilityKey.BACKEND_ENGINEERING, 0.8),
    "spring": (CapabilityKey.BACKEND_ENGINEERING, 0.85),
    "spring boot": (CapabilityKey.BACKEND_ENGINEERING, 0.9),
    "node.js": (CapabilityKey.BACKEND_ENGINEERING, 0.75),
    "nodejs": (CapabilityKey.BACKEND_ENGINEERING, 0.75),
    "microservices": (CapabilityKey.BACKEND_ENGINEERING, 0.85),
    "distributed systems": (CapabilityKey.BACKEND_ENGINEERING, 0.9),
    "rest": (CapabilityKey.BACKEND_ENGINEERING, 0.7),
    "restful": (CapabilityKey.BACKEND_ENGINEERING, 0.7),
    "graphql": (CapabilityKey.BACKEND_ENGINEERING, 0.85),
    "grpc": (CapabilityKey.BACKEND_ENGINEERING, 0.9),
    "concurrency": (CapabilityKey.BACKEND_ENGINEERING, 0.85),
    "asynchronous": (CapabilityKey.BACKEND_ENGINEERING, 0.8),
    # Frontend Engineering
    "react": (CapabilityKey.FRONTEND_ENGINEERING, 0.85),
    "react.js": (CapabilityKey.FRONTEND_ENGINEERING, 0.85),
    "next.js": (CapabilityKey.FRONTEND_ENGINEERING, 0.9),
    "nextjs": (CapabilityKey.FRONTEND_ENGINEERING, 0.9),
    "typescript": (CapabilityKey.FRONTEND_ENGINEERING, 0.8),
    "javascript": (CapabilityKey.FRONTEND_ENGINEERING, 0.65),
    "vue": (CapabilityKey.FRONTEND_ENGINEERING, 0.8),
    "vue.js": (CapabilityKey.FRONTEND_ENGINEERING, 0.8),
    "angular": (CapabilityKey.FRONTEND_ENGINEERING, 0.85),
    "tailwind": (CapabilityKey.FRONTEND_ENGINEERING, 0.8),
    "tailwindcss": (CapabilityKey.FRONTEND_ENGINEERING, 0.8),
    "css": (CapabilityKey.FRONTEND_ENGINEERING, 0.6),
    "html": (CapabilityKey.FRONTEND_ENGINEERING, 0.5),
    "redux": (CapabilityKey.FRONTEND_ENGINEERING, 0.8),
    "accessibility": (CapabilityKey.FRONTEND_ENGINEERING, 0.75),
    "a11y": (CapabilityKey.FRONTEND_ENGINEERING, 0.85),
    # Database Engineering
    "postgres": (CapabilityKey.DATABASE_ENGINEERING, 0.85),
    "postgresql": (CapabilityKey.DATABASE_ENGINEERING, 0.85),
    "mysql": (CapabilityKey.DATABASE_ENGINEERING, 0.8),
    "sqlite": (CapabilityKey.DATABASE_ENGINEERING, 0.7),
    "mongodb": (CapabilityKey.DATABASE_ENGINEERING, 0.8),
    "redis": (CapabilityKey.DATABASE_ENGINEERING, 0.85),
    "sql": (CapabilityKey.DATABASE_ENGINEERING, 0.65),
    "orm": (CapabilityKey.DATABASE_ENGINEERING, 0.75),
    "sqlalchemy": (CapabilityKey.DATABASE_ENGINEERING, 0.9),
    "prisma": (CapabilityKey.DATABASE_ENGINEERING, 0.85),
    "database design": (CapabilityKey.DATABASE_ENGINEERING, 0.8),
    "schema design": (CapabilityKey.DATABASE_ENGINEERING, 0.85),
    "indexing": (CapabilityKey.DATABASE_ENGINEERING, 0.85),
    "transactions": (CapabilityKey.DATABASE_ENGINEERING, 0.8),
    "query optimization": (CapabilityKey.DATABASE_ENGINEERING, 0.9),
    # DevOps / Cloud
    "docker": (CapabilityKey.DEVOPS_CLOUD, 0.8),
    "kubernetes": (CapabilityKey.DEVOPS_CLOUD, 0.9),
    "k8s": (CapabilityKey.DEVOPS_CLOUD, 0.9),
    "terraform": (CapabilityKey.DEVOPS_CLOUD, 0.9),
    "helm": (CapabilityKey.DEVOPS_CLOUD, 0.85),
    "aws": (CapabilityKey.DEVOPS_CLOUD, 0.8),
    "gcp": (CapabilityKey.DEVOPS_CLOUD, 0.8),
    "azure": (CapabilityKey.DEVOPS_CLOUD, 0.8),
    "ci/cd": (CapabilityKey.DEVOPS_CLOUD, 0.85),
    "github actions": (CapabilityKey.DEVOPS_CLOUD, 0.85),
    "linux": (CapabilityKey.DEVOPS_CLOUD, 0.7),
    "infrastructure as code": (CapabilityKey.DEVOPS_CLOUD, 0.9),
    # Machine Learning
    "pytorch": (CapabilityKey.MACHINE_LEARNING, 0.9),
    "tensorflow": (CapabilityKey.MACHINE_LEARNING, 0.9),
    "scikit-learn": (CapabilityKey.MACHINE_LEARNING, 0.85),
    "sklearn": (CapabilityKey.MACHINE_LEARNING, 0.85),
    "transformers": (CapabilityKey.MACHINE_LEARNING, 0.9),
    "huggingface": (CapabilityKey.MACHINE_LEARNING, 0.85),
    "llm": (CapabilityKey.MACHINE_LEARNING, 0.9),
    "deep learning": (CapabilityKey.MACHINE_LEARNING, 0.85),
    "machine learning": (CapabilityKey.MACHINE_LEARNING, 0.75),
    "mlops": (CapabilityKey.MACHINE_LEARNING, 0.9),
    # Data Engineering
    "spark": (CapabilityKey.DATA_ENGINEERING, 0.9),
    "pyspark": (CapabilityKey.DATA_ENGINEERING, 0.9),
    "kafka": (CapabilityKey.DATA_ENGINEERING, 0.9),
    "airflow": (CapabilityKey.DATA_ENGINEERING, 0.85),
    "dbt": (CapabilityKey.DATA_ENGINEERING, 0.85),
    "snowflake": (CapabilityKey.DATA_ENGINEERING, 0.85),
    "bigquery": (CapabilityKey.DATA_ENGINEERING, 0.85),
    "etl": (CapabilityKey.DATA_ENGINEERING, 0.8),
    "data warehouse": (CapabilityKey.DATA_ENGINEERING, 0.8),
    # Algorithms & Problem Solving
    "data structures": (CapabilityKey.ALGORITHMS_PROBLEM_SOLVING, 0.8),
    "algorithms": (CapabilityKey.ALGORITHMS_PROBLEM_SOLVING, 0.8),
    "optimization": (CapabilityKey.ALGORITHMS_PROBLEM_SOLVING, 0.75),
    "computational complexity": (CapabilityKey.ALGORITHMS_PROBLEM_SOLVING, 0.9),
    # Testing & Quality
    "pytest": (CapabilityKey.TESTING_QUALITY, 0.85),
    "jest": (CapabilityKey.TESTING_QUALITY, 0.85),
    "vitest": (CapabilityKey.TESTING_QUALITY, 0.85),
    "unit testing": (CapabilityKey.TESTING_QUALITY, 0.75),
    "integration testing": (CapabilityKey.TESTING_QUALITY, 0.8),
    "e2e": (CapabilityKey.TESTING_QUALITY, 0.8),
    "tdd": (CapabilityKey.TESTING_QUALITY, 0.85),
    "cypress": (CapabilityKey.TESTING_QUALITY, 0.85),
    "playwright": (CapabilityKey.TESTING_QUALITY, 0.85),
    # Security
    "security": (CapabilityKey.SECURITY, 0.65),
    "authentication": (CapabilityKey.SECURITY, 0.8),
    "authorization": (CapabilityKey.SECURITY, 0.8),
    "oauth": (CapabilityKey.SECURITY, 0.85),
    "jwt": (CapabilityKey.SECURITY, 0.8),
    "owasp": (CapabilityKey.SECURITY, 0.9),
    "encryption": (CapabilityKey.SECURITY, 0.85),
    "cryptography": (CapabilityKey.SECURITY, 0.9),
    # Software Architecture
    "system design": (CapabilityKey.SOFTWARE_ARCHITECTURE, 0.85),
    "software architecture": (CapabilityKey.SOFTWARE_ARCHITECTURE, 0.85),
    "design patterns": (CapabilityKey.SOFTWARE_ARCHITECTURE, 0.8),
    "clean architecture": (CapabilityKey.SOFTWARE_ARCHITECTURE, 0.9),
    "scalability": (CapabilityKey.SOFTWARE_ARCHITECTURE, 0.8),
    "high availability": (CapabilityKey.SOFTWARE_ARCHITECTURE, 0.85),
    # Collaboration
    "git": (CapabilityKey.COLLABORATION, 0.7),
    "code review": (CapabilityKey.COLLABORATION, 0.75),
    "agile": (CapabilityKey.COLLABORATION, 0.65),
    "scrum": (CapabilityKey.COLLABORATION, 0.65),
    "cross-functional": (CapabilityKey.COLLABORATION, 0.7),
    "mentoring": (CapabilityKey.COLLABORATION, 0.75),
    # Documentation & Communication
    "documentation": (CapabilityKey.DOCUMENTATION_COMMUNICATION, 0.7),
    "technical writing": (CapabilityKey.DOCUMENTATION_COMMUNICATION, 0.8),
    "openapi": (CapabilityKey.DOCUMENTATION_COMMUNICATION, 0.85),
    "swagger": (CapabilityKey.DOCUMENTATION_COMMUNICATION, 0.8),
    "communication skills": (CapabilityKey.DOCUMENTATION_COMMUNICATION, 0.6),
}

MANDATORY_MARKERS = re.compile(
    r"\b(must\s+have|required|requirement|minimum\s+qualifications?|essential|mandatory)\b",
    re.IGNORECASE,
)
PREFERRED_MARKERS = re.compile(
    r"\b(preferred|nice\s+to\s+have|plus|bonus|optional|desired|good\s+to\s+have)\b",
    re.IGNORECASE,
)


def extract_requirements_from_jd(
    jd_text: str,
    ontology_version: str = "1.0.0",
) -> list[NormalizedRequirement]:
    """Parses raw JD text into NormalizedRequirement models.

    INVARIANT: Does NOT compute final numeric role weights.
    Ambiguous terms are marked with lower mapping confidence rather than invented certainty.
    """
    lines = [line.strip() for line in jd_text.split("\n") if line.strip()]
    requirements: list[NormalizedRequirement] = []

    current_priority = RequirementPriority.MANDATORY

    # Count mention frequencies across the entire JD
    jd_lower = jd_text.lower()
    frequencies: dict[str, int] = {}
    for term in CONTROLLED_SYNONYM_MAP:
        # Match whole words
        pattern = r"\b" + re.escape(term) + r"\b"
        cnt = len(re.findall(pattern, jd_lower))
        if cnt > 0:
            frequencies[term] = cnt

    for line in lines:
        line_lower = line.lower()

        is_heading = line.endswith(":") or line_lower in {"requirements", "must have", "mandatory requirements", "preferred qualifications", "nice to have"}
        # Check for section header priority changes
        if MANDATORY_MARKERS.search(line_lower) and is_heading and len(line.split()) <= 6 and not any(re.search(r"\b" + re.escape(term) + r"\b", line_lower) for term in CONTROLLED_SYNONYM_MAP):
            current_priority = RequirementPriority.MANDATORY
            continue
        elif PREFERRED_MARKERS.search(line_lower) and is_heading and len(line.split()) <= 6 and not any(re.search(r"\b" + re.escape(term) + r"\b", line_lower) for term in CONTROLLED_SYNONYM_MAP):
            current_priority = RequirementPriority.PREFERRED
            continue

        # Check inline priority markers
        priority = current_priority
        if PREFERRED_MARKERS.search(line_lower):
            priority = RequirementPriority.PREFERRED
        elif MANDATORY_MARKERS.search(line_lower):
            priority = RequirementPriority.MANDATORY

        # Skip headers or meta text that are not requirements
        if line.endswith(":") and len(line.split()) <= 4:
            continue
        if len(line) < 5:
            continue

        # Match terms from controlled synonym map
        matched_caps: set[CapabilityKey] = set()
        matched_techs: list[str] = []
        spec_scores: list[float] = []
        max_freq = 1

        for term, (cap, spec) in CONTROLLED_SYNONYM_MAP.items():
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, line_lower):
                matched_caps.add(cap)
                matched_techs.append(term)
                spec_scores.append(spec)
                max_freq = max(max_freq, frequencies.get(term, 1))

        if matched_caps:
            # High confidence deterministic match
            avg_spec = sum(spec_scores) / len(spec_scores)
            clean_name = ", ".join(t.title() for t in matched_techs[:3])

            requirements.append(
                NormalizedRequirement(
                    requirement_id=uuid4(),
                    source_text=line,
                    normalized_name=clean_name or line[:60],
                    priority=priority,
                    capability_mappings=sorted(matched_caps, key=lambda cap: cap.value),
                    technology_mentions=matched_techs,
                    mention_frequency=max_freq,
                    semantic_specificity=avg_spec,
                    mapping_confidence=1.0,
                    mapping_method="controlled_synonym_map",
                    ontology_version=ontology_version,
                )
            )
        else:
            # Ambiguous requirement without direct ontology hit
            # Capture as uncertain rather than inventing certainty
            first_words = " ".join(line.split()[:4])
            requirements.append(
                NormalizedRequirement(
                    requirement_id=uuid4(),
                    source_text=line,
                    normalized_name=first_words,
                    priority=priority,
                    capability_mappings=[],  # unresolved text must not invent a capability
                    technology_mentions=[],
                    mention_frequency=1,
                    semantic_specificity=0.3,  # low specificity
                    mapping_confidence=0.4,  # low confidence captures uncertainty
                    mapping_method="unresolved_ambiguity_fallback",
                    ontology_version=ontology_version,
                )
            )

    return requirements
