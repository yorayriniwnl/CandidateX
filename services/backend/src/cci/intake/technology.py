"""Deterministic technology normalization and exact-token matching.

The live workflow treats resume and public text as declarations. This module
only makes comparisons safer; it never turns a mention into capability
evidence by itself.
"""

import re
import unicodedata


_ALIASES = {
    "reactjs": "react",
    "react.js": "react",
    "nextjs": "nextjs",
    "next.js": "nextjs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "scikitlearn": "scikitlearn",
    "sklearn": "scikitlearn",
    "tailwind": "tailwindcss",
    "tailwindcss": "tailwindcss",
    "golang": "go",
    "cicd": "cicd",
    "ci/cd": "cicd",
    "cplusplus": "c++",
    "cpp": "c++",
}


def _comparison_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip().casefold()
    return re.sub(r"[^a-z0-9+#./]", "", normalized)


def normalize_technology(value: str) -> str:
    """Return a stable comparison key without changing user-facing spelling."""
    key = _comparison_key(value)
    compact = re.sub(r"[./_-]+", "", key)
    return _ALIASES.get(key, _ALIASES.get(compact, compact or key))


def technology_variants(term: str) -> tuple[str, ...]:
    """Return exact spellings that represent the same controlled technology."""
    canonical = normalize_technology(term)
    variants = {term.strip()}
    for alias, target in _ALIASES.items():
        if target == canonical:
            variants.add(alias)
    if canonical:
        variants.add(canonical)
    return tuple(sorted((variant for variant in variants if variant), key=len, reverse=True))


def technology_pattern(term: str) -> re.Pattern[str]:
    """Compile an exact technology token pattern.

    Word boundaries are insufficient for terms such as ``C++`` and ``CI/CD``
    and allow ``Java`` to match the prefix of ``JavaScript``. Alphanumeric,
    underscore, plus, and hash characters are treated as technology-token
    characters on both sides.
    """
    escaped = re.escape(term.strip())
    return re.compile(rf"(?<![A-Za-z0-9_+#]){escaped}(?![A-Za-z0-9_+#])", re.IGNORECASE)


def contains_technology(text: str, term: str) -> bool:
    """Return whether text contains an exact spelling or controlled alias."""
    return any(technology_pattern(variant).search(text or "") for variant in technology_variants(term))
