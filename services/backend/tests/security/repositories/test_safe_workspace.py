"""Security tests verifying sandboxed repository workspace containment invariants."""

import os
import sys
import tempfile
import pytest

from cci.security.repository_workspace import (
    SafeRepositoryWorkspace,
    WorkspaceSecurityError,
    verify_path_containment,
)


def test_symlink_escape_detection_and_blocking():
    """Security test: Symlinks pointing outside the workspace must be detected and blocked."""
    with tempfile.TemporaryDirectory() as external_dir:
        sensitive_file = os.path.join(external_dir, "sensitive_system_file.txt")
        with open(sensitive_file, "w") as f:
            f.write("CONFIDENTIAL SYSTEM DATA")

        with SafeRepositoryWorkspace() as ws:
            # Create a normal file
            with open(os.path.join(ws.root, "normal.py"), "w") as f:
                f.write("print('hello')")

            # Attempt to create a malicious symlink pointing to external_dir
            symlink_path = os.path.join(ws.root, "malicious_escape_link")
            try:
                os.symlink(sensitive_file, symlink_path)
            except OSError:
                # On Windows without Developer Mode, symlink creation might require privileges.
                # In that case, test verify_path_containment directly.
                assert not verify_path_containment(sensitive_file, ws.root)
                return

            # Scanning must detect escape and raise WorkspaceSecurityError
            with pytest.raises(WorkspaceSecurityError, match="Symlink.*escape detected"):
                ws.scan_files()


def test_worktree_size_capacity_enforcement():
    """Security test: Repositories exceeding the worktree size cap must raise WorkspaceSecurityError."""
    # Set cap to 100 KB for testing
    max_bytes = 100 * 1024

    with SafeRepositoryWorkspace(max_worktree_bytes=max_bytes) as ws:
        # Write file exceeding limit (150 KB)
        large_file = os.path.join(ws.root, "large_blob.bin")
        with open(large_file, "wb") as f:
            f.write(b"0" * (150 * 1024))

        with pytest.raises(WorkspaceSecurityError, match="exceeded maximum worktree capacity"):
            ws.scan_files()


def test_path_count_limit_enforcement():
    """Security test: Repositories exceeding the path limit must raise WorkspaceSecurityError."""
    max_paths = 20

    with SafeRepositoryWorkspace(max_paths=max_paths) as ws:
        # Create 25 files
        for i in range(25):
            with open(os.path.join(ws.root, f"file_{i}.txt"), "w") as f:
                f.write("data")

        with pytest.raises(WorkspaceSecurityError, match="exceeded maximum path limit"):
            ws.scan_files()


def test_candidate_code_is_never_executed():
    """Security test: Candidate setup scripts, Makefiles, or .sh scripts are NEVER executed."""
    marker_file = tempfile.mktemp(prefix="should_never_exist_")

    with SafeRepositoryWorkspace() as ws:
        # Create a malicious setup.py that touches marker_file if run
        setup_script = os.path.join(ws.root, "setup.py")
        with open(setup_script, "w") as f:
            f.write(f"import os; os.system('touch {marker_file}')")

        # Create a malicious shell script
        sh_script = os.path.join(ws.root, "build.sh")
        with open(sh_script, "w") as f:
            f.write(f"touch {marker_file}\n")

        # Scan and index files
        files = ws.scan_files()
        assert len(files) == 2

        # Invariant: Marker file must NOT exist (no candidate code was executed)
        assert not os.path.exists(marker_file)


def test_large_text_file_boundary():
    """Security test: Files exceeding max_file_bytes must be marked is_too_large."""
    max_file = 50 * 1024  # 50 KB

    with SafeRepositoryWorkspace(max_file_bytes=max_file) as ws:
        with open(os.path.join(ws.root, "big.txt"), "w") as f:
            f.write("A" * (60 * 1024))

        with open(os.path.join(ws.root, "small.txt"), "w") as f:
            f.write("A" * (10 * 1024))

        files = ws.scan_files()
        by_name = {f.relative_path: f for f in files}

        assert by_name["big.txt"].is_too_large
        assert not by_name["small.txt"].is_too_large
