"""Versioned eligibility and immutable receipts for pinned repository scans."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import PurePosixPath
import re
from types import MappingProxyType
import defusedxml.ElementTree as ET

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
        return _lcov_is_parseable(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, ET.ParseError):
        return False


def _lcov_is_parseable(text: str) -> bool:
    """Require complete source-file records before treating LCOV as inspected."""
    allowed_fields = {"TN", "SF", "FN", "FNDA", "FNF", "FNH", "BRDA",
                      "BRF", "BRH", "DA", "LF", "LH"}
    count_fields = {"LF", "LH", "BRF", "BRH", "FNF", "FNH"}
    in_record = False
    completed = 0
    counters = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "end_of_record":
            if not in_record or not ({"LF", "LH"} <= counters or {"BRF", "BRH"} <= counters):
                return False
            completed += 1
            in_record = False
            counters.clear()
            continue
        field, separator, value = line.partition(":")
        if not separator or field not in allowed_fields:
            return False
        if field == "SF":
            if in_record or not value:
                return False
            in_record = True
            continue
        if field == "TN" and not in_record:
            continue
        if not in_record:
            return False
        if field == "DA":
            parts = value.split(",")
            if (len(parts) not in {2, 3} or not parts[0].isdecimal()
                    or int(parts[0]) == 0 or not parts[1].isdecimal()
                    or (len(parts) == 3 and not parts[2])):
                return False
        if field == "FNDA":
            count, separator, name = value.partition(",")
            if not separator or not count.isdecimal() or not name:
                return False
        if field == "FN":
            start, separator, remainder = value.partition(",")
            if not separator or not start.isdecimal() or int(start) == 0 or not remainder:
                return False
            end, separator, name = remainder.partition(",")
            if separator and end.isdecimal() and (int(end) == 0 or not name):
                return False
        if field == "BRDA":
            parts = value.split(",", 3)
            if (len(parts) != 4 or not parts[0].isdecimal() or int(parts[0]) == 0
                    or re.fullmatch(r"[eEfFuU]*[0-9]+", parts[1]) is None or not parts[2]
                    or (parts[3] != "-" and not parts[3].isdecimal())):
                return False
        if field in count_fields:
            if not value.isdecimal():
                return False
            if field in {"LF", "LH", "BRF", "BRH"}:
                counters.add(field)
    return completed > 0 and not in_record


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
