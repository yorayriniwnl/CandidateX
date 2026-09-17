from typing import Any

"""Safe sandboxed repository workspace enforcing strict containment invariants."""

import os
import shutil
import stat
import tempfile
import time
from dataclasses import dataclass

# Security limits
DEFAULT_MAX_WORKTREE_BYTES = 500 * 1024 * 1024  # 500 MB
DEFAULT_MAX_PATHS = 100_000  # 100k paths
DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB per text file
DEFAULT_TIMEOUT_SECONDS = 120  # 2 minutes wall-clock timeout


class WorkspaceSecurityError(Exception):
    """Raised when repository workspace security boundaries are violated."""


@dataclass(frozen=True)
class InspectedFile:
    """Safe representation of an inspected repository file."""

    relative_path: str
    absolute_path: str
    byte_size: int
    is_binary: bool
    is_symlink: bool
    is_too_large: bool


def is_binary_file(file_path: str, sample_size: int = 8192) -> bool:
    """Detects whether a file is binary by sniffing for null bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
            return b"\x00" in chunk
    except Exception:
        return True


def verify_path_containment(target_path: str, workspace_root: str) -> bool:
    """Verifies that target_path (resolving any symlinks) remains strictly inside workspace_root."""
    real_root = os.path.realpath(workspace_root)
    real_target = os.path.realpath(target_path)

    # Must start with real_root and a path separator (or be identical)
    return real_target == real_root or real_target.startswith(real_root + os.sep)


class SafeRepositoryWorkspace:
    """Context manager providing sandboxed repository file inspection.

    SECURITY INVARIANTS:
    1. Candidate repository code is NEVER executed, built, installed, or tested.
    2. Git hooks are disabled.
    3. Git submodules are not recursed or executed.
    4. Worktree size capped at 500MB.
    5. Path count capped at 100,000.
    6. Text file size capped at 5MB.
    7. Symlink escape attempts raise WorkspaceSecurityError.
    8. Guaranteed ephemeral cleanup.
    """

    def __init__(
        self,
        base_dir: str | None = None,
        max_worktree_bytes: int = DEFAULT_MAX_WORKTREE_BYTES,
        max_paths: int = DEFAULT_MAX_PATHS,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_dir = base_dir
        self.max_worktree_bytes = max_worktree_bytes
        self.max_paths = max_paths
        self.max_file_bytes = max_file_bytes
        self.timeout_seconds = timeout_seconds

        self.workspace_dir: str | None = None
        self.start_time: float = 0.0

    def __enter__(self) -> "SafeRepositoryWorkspace":
        self.workspace_dir = tempfile.mkdtemp(prefix="cci_repo_", dir=self.base_dir)
        self.start_time = time.time()
        return self

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Deterministically removes the temporary workspace directory."""
        if self.workspace_dir and os.path.exists(self.workspace_dir):
            try:
                # Force write permissions to remove read-only git pack files on Windows
                for root, dirs, files in os.walk(self.workspace_dir):
                    for fname in files:
                        p = os.path.join(root, fname)
                        try:
                            os.chmod(p, stat.S_IWRITE)
                        except Exception:
                            pass
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
            except Exception:
                pass
            finally:
                self.workspace_dir = None

    @property
    def root(self) -> str:
        if not self.workspace_dir:
            raise RuntimeError("SafeRepositoryWorkspace has not been entered.")
        return self.workspace_dir

    def check_timeout(self) -> None:
        """Enforces wall-clock timeout."""
        if time.time() - self.start_time > self.timeout_seconds:
            raise WorkspaceSecurityError(
                f"Repository inspection exceeded wall-clock timeout of {self.timeout_seconds}s."
            )

    def scan_files(self) -> list[InspectedFile]:
        """Walks the workspace under strict containment rules and returns safe file metadata."""
        if not self.workspace_dir:
            raise RuntimeError("Workspace not active.")

        total_bytes = 0
        total_paths = 0
        inspected: list[InspectedFile] = []

        for root, dirs, files in os.walk(self.workspace_dir, followlinks=False):
            self.check_timeout()

            # Prevent stepping into .git internal directory
            if ".git" in dirs:
                dirs.remove(".git")

            for dirname in list(dirs):
                dirpath = os.path.join(root, dirname)
                total_paths += 1
                if total_paths > self.max_paths:
                    raise WorkspaceSecurityError(
                        f"Repository exceeded maximum path limit of {self.max_paths} paths."
                    )
                # Check directory symlink containment
                if os.path.islink(dirpath):
                    if not verify_path_containment(dirpath, self.workspace_dir):
                        dirs.remove(dirname)
                        raise WorkspaceSecurityError(
                            f"Symlink directory escape detected: {dirname} points outside workspace."
                        )

            for fname in files:
                filepath = os.path.join(root, fname)
                total_paths += 1

                if total_paths > self.max_paths:
                    raise WorkspaceSecurityError(
                        f"Repository exceeded maximum path limit of {self.max_paths} paths."
                    )

                is_symlink = os.path.islink(filepath)
                if is_symlink:
                    if not verify_path_containment(filepath, self.workspace_dir):
                        raise WorkspaceSecurityError(
                            f"Symlink file escape detected: {fname} points outside workspace."
                        )

                try:
                    stat_res = os.stat(filepath)
                    file_size = stat_res.st_size
                except Exception:
                    continue

                total_bytes += file_size
                if total_bytes > self.max_worktree_bytes:
                    raise WorkspaceSecurityError(
                        f"Repository exceeded maximum worktree capacity of {self.max_worktree_bytes} bytes."
                    )

                rel_path = os.path.relpath(filepath, self.workspace_dir).replace(
                    "\\", "/"
                )
                is_too_large = file_size > self.max_file_bytes
                binary = False if is_too_large else is_binary_file(filepath)

                inspected.append(
                    InspectedFile(
                        relative_path=rel_path,
                        absolute_path=filepath,
                        byte_size=file_size,
                        is_binary=binary,
                        is_symlink=is_symlink,
                        is_too_large=is_too_large,
                    )
                )

        return inspected
