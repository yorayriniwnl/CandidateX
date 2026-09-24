"""Iterative deep scan for large repository Git trees (Fix 24).

Replaces the 12-blob oversize fallback with an intelligent, multi-tier iterative deep scan:
1. Manifests
2. Entry points
3. Application routes
4. Database schema
5. Migrations
6. Tests, coverage, and benchmarks
7. CI configuration
8. Docker & containerization
9. Infrastructure & IaC
10. Security & auth policies
11. Architecture documentation
12. Project-specific modules

Then iteratively expands using static imports and project structure.
Invariants:
- Never executes candidate or repository code.
- Preserves bounded resource constraints (SafeRepositoryWorkspace timeout, byte caps).
- Accurately tracks inventory completeness and skip reasons for negative evidence.
"""

import base64
import hashlib
from pathlib import PurePosixPath, Path
import re
from typing import Any, Mapping, Sequence

from cci.analyzers.repository.indexer import categorize_file
from cci.live.contracts import MAX_FILE_BYTES
from cci.live.scan_inventory import IGNORED_COMPONENTS, InventoryCounter, report_is_parseable
from cci.security.repository_workspace import WorkspaceSecurityError

MAX_DEEP_SCAN_BLOBS = 50
CATEGORIES = {'manifests': 0, 'database': 1, 'tests': 2, 'ci': 3, 'infra': 4, 'openapi': 5, 'source': 6, 'docs': 7}
IGNORED = IGNORED_COMPONENTS


def classify_blob_architectural_tier(path_str: str) -> tuple[int, int]:
    """Assigns an architectural priority tier and sort weight to a repository path.

    Lower tier numbers indicate higher inspection priority (1 = highest).
    """
    p = PurePosixPath(path_str)
    name = p.name.lower()
    path_lower = path_str.lower()
    parts = [part.lower() for part in p.parts]

    # 1. Manifests
    if name in {
        "package.json", "requirements.txt", "pyproject.toml", "cargo.toml",
        "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "gemfile",
        "composer.json", "setup.py", "setup.cfg", "pipfile", "mix.exs",
    }:
        return (1, 0)

    # 2. Entry points
    if name in {
        "main.py", "app.py", "server.py", "index.ts", "index.js", "main.go",
        "main.rs", "application.java", "program.cs", "manage.py", "wsgi.py",
        "asgi.py", "app.ts", "server.ts", "cli.py", "run.py",
    }:
        return (2, 0)

    # 3. Application routes & API endpoints
    if (
        name in {"routes.py", "api.py", "router.py", "urls.py", "endpoints.py"}
        or any(part in {"routes", "api", "controllers", "handlers", "endpoints", "views"} for part in parts[:-1])
    ):
        return (3, 0)

    # 4. Database schema & entity models
    if (
        name in {"schema.sql", "models.py", "schema.prisma", "db.sql"}
        or any(part in {"models", "entities", "schema", "entity", "domain"} for part in parts[:-1])
    ):
        return (4, 0)

    # 5. Database migrations
    if any(part in {"migrations", "alembic", "db/migrate", "prisma/migrations", "flyway"} for part in parts[:-1]):
        return (5, 0)

    # 6. Tests, coverage reports, and benchmarks
    if (
        name in {"coverage.xml", "lcov.info", "cobertura.xml"}
        or name.startswith("benchmark")
        or name.endswith("_test.py") or name.startswith("test_")
        or name.endswith(".test.ts") or name.endswith(".spec.ts")
        or name.endswith(".test.js") or name.endswith(".spec.js")
        or name.endswith("_test.go") or name.endswith("_test.rs")
        or any(part in {"tests", "test", "spec", "benchmarks", "benchmark"} for part in parts[:-1])
    ):
        return (6, 0)

    # 7. CI & Build configuration
    if (
        any(part in {".github", "workflows", ".circleci"} for part in parts[:-1])
        or name in {".gitlab-ci.yml", "jenkinsfile", "makefile", "azure-pipelines.yml"}
    ):
        return (7, 0)

    # 8. Docker & containerization
    if (
        name in {"dockerfile", "containerfile", "docker-compose.yml", "docker-compose.yaml"}
        or name.startswith("dockerfile.")
    ):
        return (8, 0)

    # 9. Infrastructure & IaC
    if (
        name.endswith(".tf") or name.endswith(".tfvars")
        or any(part in {"terraform", "k8s", "kubernetes", "helm", "ansible", "infra"} for part in parts[:-1])
        or name in {"pulumi.yaml", "chart.yaml"}
    ):
        return (9, 0)

    # 10. Security policies & Auth modules
    if (
        name in {"security.md", "auth.py", "jwt.py", "security.py", "oauth.py", "permissions.py"}
        or any(part in {"auth", "security", "policies", "policy"} for part in parts[:-1])
    ):
        return (10, 0)

    # 11. Architecture & documentation
    if (
        name in {"readme.md", "architecture.md", "design.md", "contributing.md"}
        or any(part in {"docs", "doc", "adr"} for part in parts[:-1])
    ):
        return (11, 0)

    # 12. Primary source modules (src/, lib/, app/, pkg/)
    if any(part in {"src", "lib", "app", "pkg", "internal"} for part in parts[:-1]):
        return (12, len(parts))

    # 13. Other files
    return (13, len(parts))


def extract_static_import_references(file_path: str, content_bytes: bytes) -> set[str]:
    """Statically extracts imported module/file references from content without execution."""
    refs: set[str] = set()
    try:
        text = content_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return refs

    path_lower = file_path.lower()
    curr_dir = str(PurePosixPath(file_path).parent)

    # Python imports
    if path_lower.endswith(".py"):
        for m in re.finditer(r'^\s*import\s+([^\r\n#]+)', text, re.MULTILINE):
            for part in m.group(1).split(","):
                mod = part.strip().split()[0] if part.strip() else ""
                if mod and mod.replace(".", "").isalnum():
                    rel_candidate = mod.replace(".", "/")
                    refs.add(rel_candidate + ".py")
                    refs.add(rel_candidate + "/__init__.py")
                    if curr_dir and curr_dir != ".":
                        refs.add(f"{curr_dir}/{rel_candidate}.py")
                        refs.add(f"{curr_dir}/{rel_candidate}/__init__.py")

        for m in re.finditer(r'^\s*from\s+([a-zA-Z0-9_\.]+)\s+import\s+([^\r\n#]+)', text, re.MULTILINE):
            raw_mod = m.group(1)
            raw_targets = m.group(2).replace("(", "").replace(")", "").split(",")
            leading_dots = len(raw_mod) - len(raw_mod.lstrip("."))
            mod_remainder = raw_mod.lstrip(".")

            base_dir = PurePosixPath(curr_dir) if curr_dir and curr_dir != "." else PurePosixPath("")
            if leading_dots > 0:
                for _ in range(leading_dots - 1):
                    base_dir = base_dir.parent
                rel_base = (base_dir / mod_remainder.replace(".", "/")) if mod_remainder else base_dir
            else:
                rel_base = PurePosixPath(raw_mod.replace(".", "/"))

            rel_str = str(rel_base).replace("\\", "/")
            if rel_str and rel_str != ".":
                refs.add(f"{rel_str}.py")
                refs.add(f"{rel_str}/__init__.py")
                if leading_dots == 0 and curr_dir and curr_dir != ".":
                    refs.add(f"{curr_dir}/{rel_str}.py")
                    refs.add(f"{curr_dir}/{rel_str}/__init__.py")

            for tgt in raw_targets:
                item = tgt.strip().split()[0] if tgt.strip() else ""
                if item and item.isidentifier():
                    if rel_str and rel_str != ".":
                        refs.add(f"{rel_str}/{item}.py")
                        refs.add(f"{rel_str}/{item}/__init__.py")
                    else:
                        refs.add(f"{item}.py")

    # JavaScript / TypeScript imports
    elif any(path_lower.endswith(ext) for ext in (".ts", ".js", ".tsx", ".jsx", ".mjs")):
        for m in re.finditer(r'(?:import|from|require)\s*\(?[\'"](\.[^\'"]+)[\'"]\)?', text):
            target = m.group(1)
            norm_target = str(PurePosixPath(curr_dir, target)).replace("\\", "/")
            for ext in (".ts", ".js", ".tsx", ".jsx", "/index.ts", "/index.js"):
                refs.add(norm_target + ext)
                refs.add(norm_target.removesuffix(ext) + ext)

    # Go imports
    elif path_lower.endswith(".go"):
        for m in re.finditer(r'["\']([a-zA-Z0-9_\-\./]+)["\']', text):
            pkg = m.group(1)
            parts = pkg.split("/")
            if len(parts) > 1:
                refs.add(parts[-1] + ".go")

    # Rust module references
    elif path_lower.endswith(".rs"):
        for m in re.finditer(r'^\s*(?:mod\s+([a-zA-Z0-9_]+);|use\s+crate::([a-zA-Z0-9_]+))', text, re.MULTILINE):
            mod = m.group(1) or m.group(2)
            if mod:
                refs.add(f"{mod}.rs")
                refs.add(f"{mod}/mod.rs")

    return refs


def iterative_deep_scan_git_blobs(
    fetcher: Any,
    owner: str,
    repo: str,
    sha: str,
    workspace: Any,
    *,
    max_blobs: int = MAX_DEEP_SCAN_BLOBS,
) -> tuple[int, Any]:
    """Iteratively inspects an architectural slice of an oversized repository using the immutable Git tree (Fix 24).

    1. Fetches full immutable Git tree.
    2. Filters unsafe symlinks, byte caps, and ignored directories.
    3. Categorizes and prioritizes candidates across 12 architectural tiers.
    4. Iteratively inspects top tier files and expands using statically extracted imports.
    5. Preserves SafeRepositoryWorkspace timeout and resource constraints.
    """
    inventory = InventoryCounter()
    tree = fetcher.get(f"/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list) or tree.get("truncated"):
        inventory.inventory_complete = False
        return 0, inventory.receipt()

    files = [item for item in tree.get("tree", []) if item.get("type") == "blob"]
    valid_items: list[tuple[dict[str, Any], list[str], tuple[int, int]]] = []

    for item in files:
        path = PurePosixPath(item.get("path", ""))
        categories = inventory.add(str(path))
        if path.is_absolute() or ".." in path.parts or "\\" in str(path) or ":" in str(path):
            inventory.inventory_complete = False
            inventory.skip(categories, "unsafe_symlink")
            continue
        category = categorize_file(str(path))
        if item.get("mode") not in {"100644", "100755"}:
            inventory.skip(categories, "unsafe_symlink")
            continue
        if (
            any(part.lower() in IGNORED for part in path.parts)
            and not any(c in categories for c in ("coverage", "benchmark"))
        ):
            continue
        size = item.get("size")
        if not isinstance(size, int) or size > MAX_FILE_BYTES:
            inventory.skip(categories, "byte_cap")
            continue
        if category not in CATEGORIES and not categories:
            continue

        tier = classify_blob_architectural_tier(str(path))
        valid_items.append((item, categories, tier))

    # Sort valid candidates by architectural tier ascending, then path alphabetically
    valid_items.sort(key=lambda entry: (entry[2], entry[0]["path"]))

    selected_queue: list[tuple[dict[str, Any], list[str]]] = []
    unselected_map: dict[str, tuple[dict[str, Any], list[str], tuple[int, int]]] = {
        item["path"]: (item, cats, tier) for item, cats, tier in valid_items
    }

    # If total eligible files are within budget, select all of them
    if len(valid_items) <= max_blobs:
        selected_queue = [(item, cats) for item, cats, _ in valid_items]
        unselected_map.clear()
    else:
        # Seed with high-priority architectural files (tiers 1-11)
        architectural_items = [entry for entry in valid_items if entry[2][0] <= 11]
        if len(architectural_items) >= max_blobs:
            # High-priority tiers fill the entire budget
            for item, cats, tier in architectural_items[:max_blobs]:
                selected_queue.append((item, cats))
                unselected_map.pop(item["path"], None)
        else:
            # Seed with all available architectural items, leaving headroom for iterative expansion
            for item, cats, tier in architectural_items:
                selected_queue.append((item, cats))
                unselected_map.pop(item["path"], None)

    stored = 0
    inspected_paths: set[str] = set()
    queue_index = 0

    while stored < max_blobs:
        # If queue is empty or exhausted, but budget remains, fill from highest available unselected tiers
        if queue_index >= len(selected_queue):
            if not unselected_map:
                break
            # Sort remaining unselected by tier ascending, then path
            remaining_sorted = sorted(unselected_map.values(), key=lambda entry: (entry[2], entry[0]["path"]))
            needed = max_blobs - stored
            for item, cats, _ in remaining_sorted[:needed]:
                selected_queue.append((item, cats))
                unselected_map.pop(item["path"], None)

        if queue_index >= len(selected_queue):
            break

        try:
            workspace.check_timeout()
        except WorkspaceSecurityError:
            for item, cats in selected_queue[queue_index:]:
                inventory.skip(cats, "timeout")
            for item, cats, _ in unselected_map.values():
                inventory.skip(cats, "timeout")
            break

        item, categories = selected_queue[queue_index]
        queue_index += 1
        path_str = item.get("path", "")
        inspected_paths.add(path_str)

        reference = item.get("sha", "")
        if not re.fullmatch(r"[a-fA-F0-9]{40}", reference):
            inventory.skip(categories, "decode_parse_failure")
            continue

        try:
            data = fetcher.get(f"/repos/{owner}/{repo}/git/blobs/{reference}")
            if not isinstance(data, dict) or data.get("encoding") != "base64":
                inventory.skip(categories, "unsupported_format")
                continue
            content = base64.b64decode(re.sub(r"\s", "", data.get("content", "")), validate=True)
        except Exception as exc:
            from cci.live.acquisition import AcquisitionError
            if isinstance(exc, AcquisitionError) and exc.status == "security_blocked":
                raise
            status = getattr(exc, "status", None)
            if status in {"timeout", "rate_limited"}:
                reason = "timeout" if status == "timeout" else "unreadable"
                inventory.skip(categories, reason)
                for rem_item, rem_cats in selected_queue[queue_index:]:
                    inventory.skip(rem_cats, reason)
                for rem_item, rem_cats, _ in unselected_map.values():
                    inventory.skip(rem_cats, reason)
                break
            inventory.skip(categories, "byte_cap" if status == "too_large" else "unreadable")
            continue

        if len(content) > MAX_FILE_BYTES:
            inventory.skip(categories, "byte_cap")
            continue
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            inventory.skip(categories, "decode_parse_failure")
            continue
        if b"\x00" in content[:8192]:
            inventory.skip(categories, "decode_parse_failure")
            continue
        if not report_is_parseable(path_str, content):
            inventory.skip(categories, "decode_parse_failure")
            continue

        actual = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        if actual != reference.lower():
            from cci.live.acquisition import AcquisitionError
            raise AcquisitionError("parse_failed", "Git blob content does not match its immutable reference.")

        destination = Path(workspace.root, path_str)
        if not destination.resolve().is_relative_to(Path(workspace.root).resolve()):
            inventory.inventory_complete = False
            inventory.skip(categories, "unsafe_symlink")
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        inventory.inspect(categories)
        stored += 1

        # Iterative expansion: find imports from inspected blob and promote referenced modules
        if (stored + (len(selected_queue) - queue_index)) < max_blobs and unselected_map:
            discovered_refs = extract_static_import_references(path_str, content)
            promoted_items: list[tuple[dict[str, Any], list[str]]] = []
            for ref in discovered_refs:
                ref_clean = ref.lstrip("/")
                for candidate_path, (cand_item, cand_cats, _) in list(unselected_map.items()):
                    if (
                        candidate_path == ref_clean
                        or candidate_path.endswith("/" + ref_clean)
                        or (len(ref_clean) > 3 and ref_clean.endswith("/" + candidate_path))
                    ):
                        if candidate_path not in inspected_paths:
                            promoted_items.append((cand_item, cand_cats))
                            unselected_map.pop(candidate_path, None)
                            break

            for p_item, p_cats in promoted_items:
                if (stored + (len(selected_queue) - queue_index)) < max_blobs:
                    selected_queue.append((p_item, p_cats))

    # Mark remaining unselected items as skipped due to file_cap
    for item, categories, _ in unselected_map.values():
        inventory.skip(categories, "file_cap")
    for item, categories in selected_queue[queue_index:]:
        if item.get("path") not in inspected_paths:
            inventory.skip(categories, "file_cap")

    return len(files) - stored, inventory.receipt()
