import base64
import hashlib
import io
import stat
import zipfile

import pytest

from cci.live.acquisition import AcquisitionError, inspect_archive, inspect_git_blobs
from cci.live.contracts import MAX_FILE_BYTES
from cci.security.repository_workspace import SafeRepositoryWorkspace


SHA = "a" * 40


def archive_bytes(files, *, symlinks=()):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"root/{name}", content)
        for name in symlinks:
            link = zipfile.ZipInfo(f"root/{name}")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, "elsewhere")
    return output.getvalue()


def git_blob(content):
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


class FakeFetcher:
    def __init__(self, files, *, truncated=False, missing=False):
        self.files = files
        self.truncated = truncated
        self.missing = missing
        self.requested_blobs = []

    def get(self, path):
        if "/git/trees/" in path:
            if self.missing:
                return {"truncated": False}
            return {"truncated": self.truncated, "tree": [
                {"path": name, "type": "blob", "mode": "100644", "size": len(content), "sha": git_blob(content)}
                for name, content in self.files.items()
            ]}
        reference = path.rsplit("/", 1)[-1]
        self.requested_blobs.append(reference)
        content = next(value for value in self.files.values() if git_blob(value) == reference)
        return {"encoding": "base64", "content": base64.b64encode(content).decode()}


def test_archive_file_cap_keeps_unselected_sources_in_denominator():
    files = {f"src/file_{i:03}.py": b"print('ok')\n" for i in range(101)}
    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = inspect_archive(archive_bytes(files), workspace)
        assert len(list(workspace.scan_files())) == 100
    source = receipt.categories["source"]
    assert omitted == 1
    assert source.eligible == 101
    assert source.inspected == 100
    assert source.skipped_reasons["file_cap"] == 1
    assert source.completeness == pytest.approx(100 / 101)
    assert receipt.categories["source:python"].eligible == 101


def test_archive_counts_oversize_binary_and_symlink_as_uninspected():
    data = archive_bytes({
        "ok.py": b"print(1)\n",
        "large.py": b"x" * (MAX_FILE_BYTES + 1),
        "binary.py": b"\0binary",
    }, symlinks=("link.py",))
    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = inspect_archive(data, workspace)
    source = receipt.categories["source"]
    assert omitted == 3
    assert (source.eligible, source.inspected) == (4, 1)
    assert dict(source.skipped_reasons) == {"byte_cap": 1, "decode_parse_failure": 1, "unsafe_symlink": 1}


def test_archive_report_allowlist_overrides_ignored_coverage_component():
    files = {
        "coverage/cobertura.xml": b'<coverage line-rate="1"/>',
        "coverage/lcov.info": b"SF:src/app.py\nDA:1,1\nLF:1\nLH:1\nend_of_record\n",
        "coverage/ignored.py": b"pass\n",
        "reports/coverage.xml": b"ignored",
        "benchmarks/a.json": b'{"schema":"1.0.0"}',
        "benchmarks/nested/b.json": b"ignored",
        "benchmark/b.json": b'{}',
        "benchmark/b.txt": b"ignored",
    }
    with SafeRepositoryWorkspace() as workspace:
        _, receipt = inspect_archive(archive_bytes(files), workspace)
        paths = {file.relative_path for file in workspace.scan_files()}
    assert (receipt.categories["coverage"].eligible, receipt.categories["coverage"].inspected) == (2, 2)
    assert (receipt.categories["benchmark"].eligible, receipt.categories["benchmark"].inspected) == (2, 2)
    assert "coverage/cobertura.xml" in paths
    assert "coverage/lcov.info" in paths
    assert "coverage/ignored.py" not in paths


def test_archive_receipt_mappings_are_immutable_and_empty_scope_is_zero():
    with SafeRepositoryWorkspace() as workspace:
        _, receipt = inspect_archive(archive_bytes({"notes.txt": b"hello"}), workspace)
    assert receipt.scope_version == "candidatex.negative-scan-scope/1.0.0"
    assert receipt.inventory_complete is True
    assert receipt.categories["source"].completeness == 0.0
    with pytest.raises(TypeError):
        receipt.categories["source"] = receipt.categories["manifest"]
    with pytest.raises(TypeError):
        receipt.categories["source"].skipped_reasons["file_cap"] = 9


def test_missing_archive_inventory_is_explicitly_incomplete():
    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = inspect_archive(None, workspace)
    assert omitted == 0
    assert receipt.inventory_complete is False
    assert receipt.categories["source"].completeness == 0.0


def test_truncated_archive_cannot_claim_complete_inventory():
    with SafeRepositoryWorkspace() as workspace:
        _, receipt = inspect_archive(b"truncated zip data", workspace)
    assert receipt.inventory_complete is False


def test_malformed_allowlisted_report_keeps_report_category_incomplete():
    data = archive_bytes({
        "coverage.xml": b'<coverage line-rate="0.8"/>',
        "coverage/cobertura.xml": b"<coverage",
        "benchmarks/good.json": b'{"schema":"1.0.0"}',
        "benchmarks/bad.json": b"{broken",
    })
    with SafeRepositoryWorkspace() as workspace:
        _, receipt = inspect_archive(data, workspace)
    coverage = receipt.categories["coverage"]
    benchmark = receipt.categories["benchmark"]
    assert (coverage.eligible, coverage.inspected) == (2, 1)
    assert coverage.skipped_reasons["decode_parse_failure"] == 1
    assert (benchmark.eligible, benchmark.inspected) == (2, 1)
    assert benchmark.skipped_reasons["decode_parse_failure"] == 1


def test_lcov_with_unrecognized_content_and_lone_counter_is_not_inspected():
    data = archive_bytes({"coverage/lcov.info": b"garbage\nLH:1\n"})
    with SafeRepositoryWorkspace() as workspace:
        _, receipt = inspect_archive(data, workspace)
    coverage = receipt.categories["coverage"]
    assert (coverage.eligible, coverage.inspected) == (1, 0)
    assert coverage.skipped_reasons["decode_parse_failure"] == 1


def test_complete_git_tree_inspects_all_eligible_files():
    files = {"src/app.py": b"print(1)\n", "requirements.txt": b"fastapi\n", "coverage.xml": b'<coverage line-rate="1"/>'}
    fetcher = FakeFetcher(files)
    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = inspect_git_blobs(fetcher, "acme", "api", SHA, workspace)
        paths = {file.relative_path for file in workspace.scan_files()}
    assert omitted == 0
    assert receipt.inventory_complete is True
    assert (receipt.categories["source"].eligible, receipt.categories["source"].inspected) == (1, 1)
    assert (receipt.categories["manifest"].eligible, receipt.categories["manifest"].inspected) == (1, 1)
    assert (receipt.categories["coverage"].eligible, receipt.categories["coverage"].inspected) == (1, 1)
    assert paths == set(files)


def test_unreadable_git_report_is_skipped_and_sibling_is_inspected():
    files = {
        "cobertura.xml": b'<coverage line-rate="0.5"/>',
        "coverage.xml": b'<coverage line-rate="0.8"/>',
    }
    failing_sha = git_blob(files["cobertura.xml"])

    class UnreadableReportFetcher(FakeFetcher):
        def get(self, path):
            if path.endswith(f"/git/blobs/{failing_sha}"):
                raise AcquisitionError("unavailable", "Selected report could not be fetched.")
            return super().get(path)

    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = inspect_git_blobs(UnreadableReportFetcher(files), "acme", "api", SHA, workspace)
    coverage = receipt.categories["coverage"]
    assert omitted == 1
    assert (coverage.eligible, coverage.inspected) == (2, 1)
    assert coverage.skipped_reasons["unreadable"] == 1


def test_git_blob_selector_cap_does_not_shrink_inventory():
    files = {f"src/app_{i:02}.py": f"print({i})\n".encode() for i in range(13)}
    with SafeRepositoryWorkspace() as workspace:
        omitted, receipt = inspect_git_blobs(FakeFetcher(files), "acme", "api", SHA, workspace)
    source = receipt.categories["source"]
    assert omitted == 1
    assert (source.eligible, source.inspected, source.skipped_reasons["file_cap"]) == (13, 12, 1)


@pytest.mark.parametrize("missing", [False, True])
def test_truncated_or_missing_git_tree_never_claims_complete_inventory(missing):
    fetcher = FakeFetcher({"app.py": b"print(1)"}, truncated=not missing, missing=missing)
    with SafeRepositoryWorkspace() as workspace:
        _, receipt = inspect_git_blobs(fetcher, "acme", "api", SHA, workspace)
        assert workspace.scan_files() == []
    assert receipt.inventory_complete is False
    assert receipt.categories["source"].completeness < 1.0
    assert fetcher.requested_blobs == []
