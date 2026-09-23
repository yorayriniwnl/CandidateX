"""Versioned eligibility and immutable receipts for pinned repository scans."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import PurePosixPath
from types import MappingProxyType
import xml.etree.ElementTree as ET

from cci.analyzers.repository.indexer import categorize_file


SCAN_SCOPE_VERSION = "candidatex.negative-scan-scope/1.0.0"
IGNORED_COMPONENTS = frozenset({
    "node_modules", "vendor", "dist", "build", ".git", ".next",
    "coverage", "__pycache__", ".venv", "venv",
})
SOURCE_LANGUAGE_EXTENSIONS: Mapping[str, frozenset[str]] = MappingProxyType({
    "python": frozenset({".py"}),
    "javascript": frozenset({".js", ".jsx", ".mjs", ".cjs"}),
    "typescript": frozenset({".ts", ".tsx", ".mts", ".cts"}),
    "vue": frozenset({".vue"}),
    "svelte": frozenset({".svelte"}),
    "go": frozenset({".go"}),
    "java": frozenset({".java"}),
    "rust": frozenset({".rs"}),
    "c": frozenset({".c", ".h"}),
    "cpp": frozenset({".cpp", ".cc", ".hpp"}),
    "csharp": frozenset({".cs"}),
    "ruby": frozenset({".rb"}),
    "php": frozenset({".php"}),
    "scala": frozenset({".scala"}),
    "kotlin": frozenset({".kt"}),
    "swift": frozenset({".swift"}),
    "shell": frozenset({".sh", ".bash"}),
    "sql": frozenset({".sql"}),
})
EXTENSION_LANGUAGE = MappingProxyType({
    extension: language
    for language, extensions in SOURCE_LANGUAGE_EXTENSIONS.items()
    for extension in extensions
})
BASE_CATEGORIES = ("source", "manifest", "coverage", "benchmark")


def eligible_categories(relative_path: str) -> tuple[str, ...]:
    """Return all scan scopes containing a regular first-party path."""
    normalized = relative_path.replace("\\", "/")
    path = PurePosixPath(normalized)
    parts = path.parts
    lower = normalized.casefold()
    if lower in {"coverage.xml", "cobertura.xml", "coverage/cobertura.xml",
                 "lcov.info", "coverage/lcov.info"}:
        return ("coverage",)
    if (len(parts) == 2 and parts[0].casefold() in {"benchmarks", "benchmark"}
            and parts[1].casefold().endswith(".json")):
        return ("benchmark",)
    if any(part.casefold() in IGNORED_COMPONENTS for part in parts):
        return ()
    result = []
    language = EXTENSION_LANGUAGE.get(path.suffix.casefold())
    if language:
        result.extend(("source", f"source:{language}"))
    if categorize_file(normalized) == "manifests":
        result.append("manifest")
    return tuple(result)


def report_is_parseable(relative_path: str, content: bytes) -> bool:
    """Ensure a selected allowlisted report is readable before counting inspection."""
    categories = eligible_categories(relative_path)
    if "coverage" not in categories and "benchmark" not in categories:
        return True
    try:
        if "benchmark" in categories:
            def unique_object(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("duplicate JSON key")
                    result[key] = value
                return result

            def reject_constant(value):
                raise ValueError(f"invalid JSON constant: {value}")

            return isinstance(json.loads(content, object_pairs_hook=unique_object,
                                         parse_constant=reject_constant), dict)
        if relative_path.casefold().endswith(".xml"):
            return ET.fromstring(content).tag == "coverage"
        lines = content.decode("utf-8").splitlines()
        fields = [line.split(":", 1) for line in lines if line.startswith(("LH:", "LF:", "BRH:", "BRF:"))]
        return bool(fields) and all(len(field) == 2 and field[1].isdigit() for field in fields)
    except (UnicodeDecodeError, ValueError, ET.ParseError):
        return False


@dataclass(frozen=True)
class ScanCategoryCounts:
    eligible: int
    inspected: int
    skipped_reasons: Mapping[str, int]

    def __post_init__(self):
        object.__setattr__(self, "skipped_reasons", MappingProxyType(dict(self.skipped_reasons)))

    @property
    def completeness(self) -> float:
        return self.inspected / self.eligible if self.eligible else 0.0


@dataclass(frozen=True)
class RepositoryScanCompleteness:
    scope_version: str
    inventory_complete: bool
    categories: Mapping[str, ScanCategoryCounts]

    def __post_init__(self):
        object.__setattr__(self, "categories", MappingProxyType(dict(self.categories)))


class InventoryCounter:
    """Mutable acquisition-local counter; freeze before handing it to consumers."""

    def __init__(self):
        self.eligible = Counter()
        self.inspected = Counter()
        self.skipped = {}
        self.inventory_complete = True

    def add(self, path: str) -> tuple[str, ...]:
        categories = eligible_categories(path)
        self.eligible.update(categories)
        return categories

    def inspect(self, categories: tuple[str, ...]) -> None:
        self.inspected.update(categories)

    def skip(self, categories: tuple[str, ...], reason: str) -> None:
        for category in categories:
            self.skipped.setdefault(category, Counter())[reason] += 1

    def receipt(self) -> RepositoryScanCompleteness:
        keys = (set(BASE_CATEGORIES) | set(self.eligible)
                | {f"source:{language}" for language in SOURCE_LANGUAGE_EXTENSIONS})
        counts = {
            key: ScanCategoryCounts(
                self.eligible[key], self.inspected[key], self.skipped.get(key, {}),
            ) for key in sorted(keys)
        }
        return RepositoryScanCompleteness(SCAN_SCOPE_VERSION, self.inventory_complete, counts)
