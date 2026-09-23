"""Comprehensive tests for Agent 05 Database, Testing, and DevOps Analyzers."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pytest
from cci.analyzers.database.schema_analyzer import (
    analyze_sql_content,
    analyze_alembic_migration,
    analyze_prisma_schema,
)
from cci.analyzers.testing.test_analyzer import (
    analyze_python_test_file,
    analyze_js_ts_test_file,
    analyze_go_test_file,
)
from cci.analyzers.infra.devops_analyzer import (
    analyze_dockerfile,
    analyze_docker_compose,
    analyze_ci_workflow,
    analyze_kubernetes_manifest,
    analyze_terraform_hcl,
)
from cci.analyzers.db_test_infra_engine import run_db_test_infra_intelligence
from cci.security.repository_workspace import SafeRepositoryWorkspace
from cci.analyzers.repository.indexer import index_repository_artifacts
from cci.domain.enums import CapabilityKey, SourceFamily
from tests.golden.db_infra_golden.fixtures import create_golden_db_infra_repo


def test_sql_schema_analysis():
    sql = """
CREATE TABLE users (id UUID PRIMARY KEY, email VARCHAR NOT NULL);
CREATE UNIQUE INDEX idx_users_email ON users (email);
CREATE INDEX idx_orders_composite ON orders (user_id, created_at);
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE metrics (recorded_at TIMESTAMP) PARTITION BY RANGE (recorded_at);
"""
    evidence = analyze_sql_content(
        sql, "migrations/001.sql", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(evidence) >= 4
    for ev in evidence:
        assert ev.target_capability == CapabilityKey.DATABASE_ENGINEERING
        assert ev.source_family == SourceFamily.GITHUB
        assert 0.0 <= ev.observed_score <= 100.0
        expected_id, expected_score = {
            "CREATE TABLE": ("candidatex.database.sql_table", 72.0),
            "CREATE INDEX": ("candidatex.database.sql_index", None),
            "FOREIGN KEY": ("candidatex.database.sql_foreign_key", 80.0),
            "Advanced Database Feature": ("candidatex.database.sql_advanced_feature", 88.0),
        }[next(
            label for label in ("CREATE TABLE", "CREATE INDEX", "FOREIGN KEY", "Advanced Database Feature")
            if label in ev.symbol_or_line
        )]
        assert (ev.signal_rule_id, ev.signal_rule_version) == (expected_id, "1.0.0")
        if expected_score is not None:
            assert ev.technical_signal_strength == expected_score

    # Verify composite index received elevated score
    composite_ev = [e for e in evidence if "idx_orders_composite" in (e.symbol_or_line or "")]
    assert len(composite_ev) > 0
    assert composite_ev[0].observed_score >= 85.0
    assert composite_ev[0].technical_signal_strength == 86.0
    unique_ev = [e for e in evidence if "idx_users_email" in (e.symbol_or_line or "")]
    assert unique_ev[0].technical_signal_strength == 82.0

    # Verify partitioning detected
    partition_ev = [e for e in evidence if "Advanced Database Feature" in (e.symbol_or_line or "")]
    assert len(partition_ev) > 0


def test_alembic_and_prisma_analysis():
    # Alembic with reversible downgrade
    alembic_code = """
from alembic import op
def upgrade():
    op.create_table('items')
    op.create_index('ix_items_id', 'items', ['id'])
def downgrade():
    op.drop_table('items')
"""
    alembic_ev = analyze_alembic_migration(
        alembic_code, "alembic/001.py", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(alembic_ev) == 1
    assert alembic_ev[0].target_capability == CapabilityKey.DATABASE_ENGINEERING
    assert alembic_ev[0].observed_score == 85.0  # Reversible migration bonus
    assert (alembic_ev[0].signal_rule_id, alembic_ev[0].signal_rule_version, alembic_ev[0].technical_signal_strength) == (
        "candidatex.database.alembic_migration", "1.0.0", 85.0
    )

    # Prisma schema
    prisma_code = """
model Account {
    id String @id
    user User @relation(fields: [userId], references: [id])
    userId String
    @@index([userId])
}
"""
    prisma_ev = analyze_prisma_schema(
        prisma_code, "prisma/schema.prisma", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(prisma_ev) == 1
    assert prisma_ev[0].target_capability == CapabilityKey.DATABASE_ENGINEERING
    assert prisma_ev[0].observed_score >= 80.0
    assert (prisma_ev[0].signal_rule_id, prisma_ev[0].signal_rule_version, prisma_ev[0].technical_signal_strength) == (
        "candidatex.database.prisma_schema", "1.0.0", 86.0
    )


@pytest.mark.parametrize("sql, expected", [
    ("CREATE INDEX ix_a ON users (email);", 78.0),
    ("CREATE UNIQUE INDEX ix_a ON users (email);", 82.0),
    ("CREATE INDEX ix_a ON users (email, id);", 86.0),
])
def test_sql_index_rule_variants(sql, expected):
    ev = analyze_sql_content(sql, "schema.sql", "https://github.com/test", "sha1")[0]
    assert (ev.signal_rule_id, ev.signal_rule_version, ev.technical_signal_strength) == (
        "candidatex.database.sql_index", "1.0.0", expected
    )


@pytest.mark.parametrize("sql", [
    "FOREIGN KEY",
    "REFERENCES users(id)",
])
def test_sql_foreign_key_rule_accepts_either_regex_alternative(sql):
    evidence = analyze_sql_content(sql, "schema.sql", "https://github.com/test", "sha1")
    assert [(ev.signal_rule_id, ev.technical_signal_strength) for ev in evidence] == [
        ("candidatex.database.sql_foreign_key", 80.0)
    ]


@pytest.mark.parametrize("features, expected", [
    ("", 72.0),
    ("  user User @relation(fields: [userId], references: [id])", 78.0),
    ("  @@index([userId])", 80.0),
    ("  @@unique([userId])", 80.0),
    ("  user User @relation(fields: [userId], references: [id])\n  @@index([userId])", 86.0),
])
def test_prisma_rule_feature_variants(features, expected):
    ev = analyze_prisma_schema(
        f"model Account {{\n id String @id\n{features}\n}}",
        "schema.prisma", "https://github.com/test", "sha1"
    )[0]
    assert (ev.signal_rule_id, ev.signal_rule_version, ev.technical_signal_strength) == (
        "candidatex.database.prisma_schema", "1.0.0", expected
    )


def test_python_testing_analyzer():
    test_code = """
import pytest
from unittest.mock import patch
from hypothesis import given, strategies as st

@pytest.fixture
def sample_data():
    return [1, 2, 3]

@pytest.mark.parametrize("x, y", [(1, 2), (3, 4)])
def test_addition(sample_data, x, y):
    assert x + 1 == y

@given(st.integers())
def test_commutative(n):
    assert n + 1 == 1 + n

def test_mocking():
    with patch("os.path.exists") as m:
        m.return_value = True
        assert True
"""
    evidence = analyze_python_test_file(
        test_code, "tests/test_math.py", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(evidence) >= 4
    for ev in evidence:
        assert ev.target_capability == CapabilityKey.TESTING_QUALITY

    # Verify Hypothesis property testing receives high score (92.0)
    hypo_ev = [e for e in evidence if "Hypothesis" in (e.symbol_or_line or "")]
    assert len(hypo_ev) == 1
    assert hypo_ev[0].observed_score == 92.0
    assert {
        ev.signal_rule_id: (ev.signal_rule_version, ev.technical_signal_strength)
        for ev in evidence
    } == {
        "candidatex.testing.python_suite": ("1.0.0", 72.0),
        "candidatex.testing.python_fixtures": ("1.0.0", 80.0),
        "candidatex.testing.python_parameterized": ("1.0.0", 84.0),
        "candidatex.testing.python_mocks": ("1.0.0", 85.0),
        "candidatex.testing.python_property_based": ("1.0.0", 92.0),
    }


def test_polyglot_testing_analyzers():
    # TS / Jest
    ts_test = """
import request from 'supertest';
describe('App', () => {
    beforeEach(() => {});
    it('works', async () => {});
});
"""
    ts_ev = analyze_js_ts_test_file(
        ts_test, "test.spec.ts", "https://github.com/test", "sha1", "1.0.0"
    )
    assert any(e.target_capability == CapabilityKey.TESTING_QUALITY for e in ts_ev)
    assert any("Supertest" in (e.symbol_or_line or "") for e in ts_ev)
    assert {
        ev.signal_rule_id: (ev.signal_rule_version, ev.technical_signal_strength)
        for ev in ts_ev
    } == {
        "candidatex.testing.javascript_suite": ("1.0.0", 72.0),
        "candidatex.testing.javascript_lifecycle": ("1.0.0", 78.0),
        "candidatex.testing.javascript_supertest": ("1.0.0", 86.0),
    }

    # Go table-driven
    go_test = """
package main
import "testing"
func TestAdd(t *testing.T) {
    tests := []struct{ a, b int }{}
    for _, tt := range tests {
        t.Run("sub", func(t *testing.T) {})
    }
}
"""
    go_ev = analyze_go_test_file(
        go_test, "add_test.go", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(go_ev) > 0
    assert go_ev[0].target_capability == CapabilityKey.TESTING_QUALITY
    assert go_ev[0].observed_score >= 84.0  # Table-driven score
    assert (go_ev[0].signal_rule_id, go_ev[0].signal_rule_version, go_ev[0].technical_signal_strength) == (
        "candidatex.testing.go_suite", "1.0.0", 84.0
    )


def test_devops_and_infra_analyzers():
    # Dockerfile
    dockerfile = """
FROM golang:1.22 AS builder
WORKDIR /src
COPY . .
RUN go build -o /bin/app

FROM alpine:3.19
COPY --from=builder /bin/app /bin/app
USER nonroot
HEALTHCHECK CMD /bin/app --health || exit 1
ENTRYPOINT ["/bin/app"]
"""
    docker_ev = analyze_dockerfile(
        dockerfile, "Dockerfile", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(docker_ev) == 1
    assert docker_ev[0].target_capability == CapabilityKey.DEVOPS_CLOUD
    assert docker_ev[0].observed_score >= 88.0  # Multi-stage + nonroot + healthcheck
    assert (docker_ev[0].signal_rule_id, docker_ev[0].signal_rule_version, docker_ev[0].technical_signal_strength) == (
        "candidatex.infra.dockerfile", "1.0.0", min(72.0 + 12.0 + 6.0 + 4.0, 92.0)
    )

    # Docker Compose
    compose = """
version: '3'
services:
  api:
    image: myapi
    networks: [app-net]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/ping"]
  redis:
    image: redis:alpine
    networks: [app-net]
networks:
  app-net:
"""
    compose_ev = analyze_docker_compose(
        compose, "docker-compose.yml", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(compose_ev) == 1
    assert compose_ev[0].target_capability == CapabilityKey.DEVOPS_CLOUD
    assert compose_ev[0].observed_score >= 80.0
    assert (compose_ev[0].signal_rule_id, compose_ev[0].signal_rule_version, compose_ev[0].technical_signal_strength) == (
        "candidatex.infra.docker_compose", "1.0.0", min(74.0 + 5.0 + 5.0, 90.0)
    )

    # CI Workflow
    ci = """
name: Test
on: [push]
jobs:
  unit:
    strategy:
      matrix:
        node: [18, 20]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache@v3
      - run: npm test
"""
    ci_ev = analyze_ci_workflow(
        ci, ".github/workflows/ci.yml", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(ci_ev) == 1
    assert ci_ev[0].target_capability == CapabilityKey.DEVOPS_CLOUD
    assert ci_ev[0].observed_score >= 88.0  # Matrix + cache + test
    assert (ci_ev[0].signal_rule_id, ci_ev[0].signal_rule_version, ci_ev[0].technical_signal_strength) == (
        "candidatex.infra.ci_workflow", "1.0.0", min(75.0 + 6.0 + 7.0 + 4.0, 94.0)
    )

    # Kubernetes
    k8s = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deploy
spec:
  template:
    spec:
      containers:
        - name: api
          resources:
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
"""
    k8s_ev = analyze_kubernetes_manifest(
        k8s, "k8s/deploy.yaml", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(k8s_ev) == 1
    assert k8s_ev[0].target_capability == CapabilityKey.DEVOPS_CLOUD
    assert k8s_ev[0].observed_score >= 88.0
    assert (k8s_ev[0].signal_rule_id, k8s_ev[0].signal_rule_version, k8s_ev[0].technical_signal_strength) == (
        "candidatex.infra.kubernetes_manifest", "1.0.0", min(80.0 + 7.0 + 5.0, 92.0)
    )

    # Terraform
    tf = """
resource "aws_s3_bucket" "b" {
  bucket = "test-bucket"
}
module "network" {
  source = "./modules/net"
}
"""
    tf_ev = analyze_terraform_hcl(
        tf, "main.tf", "https://github.com/test", "sha1", "1.0.0"
    )
    assert len(tf_ev) == 1
    assert tf_ev[0].target_capability == CapabilityKey.DEVOPS_CLOUD
    assert tf_ev[0].observed_score >= 88.0
    assert (tf_ev[0].signal_rule_id, tf_ev[0].signal_rule_version, tf_ev[0].technical_signal_strength) == (
        "candidatex.infra.terraform_hcl", "1.0.0", min(82.0 + 4.0 + 5.0, 92.0)
    )


def test_testing_fallback_js_mock_and_go_score_branches():
    fallback = analyze_python_test_file(
        "def test_broken(:\n", "test_broken.py", "https://github.com/test", "sha1"
    )[0]
    assert (fallback.signal_rule_id, fallback.signal_rule_version, fallback.technical_signal_strength) == (
        "candidatex.testing.python_regex_fallback", "1.0.0", 70.0
    )

    js_mock = analyze_js_ts_test_file(
        "test('works', () => {}); jest.mock('dep');", "test.js", "https://github.com/test", "sha1"
    )
    assert {
        ev.signal_rule_id: (ev.signal_rule_version, ev.technical_signal_strength)
        for ev in js_mock
    } == {
        "candidatex.testing.javascript_suite": ("1.0.0", 72.0),
        "candidatex.testing.javascript_mocks": ("1.0.0", 84.0),
    }

    for body, expected in (("", 74.0), ('t.Run("case", func(t *testing.T) {})', 80.0)):
        go = analyze_go_test_file(
            f"package p\nimport \"testing\"\nfunc TestThing(t *testing.T) {{ {body} }}",
            "thing_test.go", "https://github.com/test", "sha1",
        )[0]
        assert (go.signal_rule_id, go.signal_rule_version, go.technical_signal_strength) == (
            "candidatex.testing.go_suite", "1.0.0", expected
        )


def test_javascript_supertest_regex_requires_trailing_word_boundary():
    ordinary_call = analyze_js_ts_test_file(
        "request(app).get('/health')", "api.test.js", "https://github.com/test", "sha1"
    )
    named_library = analyze_js_ts_test_file(
        "import supertest from 'supertest'", "api.test.js", "https://github.com/test", "sha1"
    )
    assert ordinary_call == []
    assert [(ev.signal_rule_id, ev.technical_signal_strength) for ev in named_library] == [
        ("candidatex.testing.javascript_supertest", 86.0)
    ]


@pytest.mark.parametrize("compose, expected", [
    ("services: {}", 74.0),
    (
        "services:\n  api:\n    image: app\n    networks: [internal]\n"
        "    volumes: [data:/data]\n    healthcheck:\n      test: [CMD, true]\n",
        88.0,
    ),
])
def test_docker_compose_rule_conditional_strength(compose, expected):
    evidence = analyze_docker_compose(
        compose, "compose.yml", "https://github.com/test", "sha1"
    )
    assert [(ev.signal_rule_id, ev.technical_signal_strength) for ev in evidence] == [
        ("candidatex.infra.docker_compose", expected)
    ]


@pytest.mark.parametrize("services", ["null", "[]"])
def test_docker_compose_non_mapping_services_is_unsupported(services):
    with pytest.raises(AttributeError):
        analyze_docker_compose(
            f"services: {services}\n", "compose.yml", "https://github.com/test", "sha1"
        )


def test_ci_score_cap_keeps_rule_identity():
    ci = """jobs:
  test:
    strategy:
      matrix:
        python: ['3.11']
    steps:
      - uses: actions/cache@v3
      - run: pytest && deploy
"""
    ev = analyze_ci_workflow(ci, "ci.yml", "https://github.com/test", "sha1")[0]
    assert (ev.signal_rule_id, ev.signal_rule_version, ev.technical_signal_strength) == (
        "candidatex.infra.ci_workflow", "1.0.0", 94.0
    )


def test_full_db_test_infra_operational_engine():
    """Validates end-to-end operational engine against golden multi-artifact workspace."""
    with SafeRepositoryWorkspace() as ws:
        create_golden_db_infra_repo(ws.root)

        metadata, artifacts = index_repository_artifacts(
            workspace=ws,
            repo_url="https://github.com/candidate/full-platform",
            commit_sha="deadbeef9999",
        )
        assert len(artifacts) >= 8

        evidence = run_db_test_infra_intelligence(
            workspace_root=ws.root,
            repo_url="https://github.com/candidate/full-platform",
            commit_sha="deadbeef9999",
            artifacts=artifacts,
        )

        assert len(evidence) >= 10

        target_caps = {e.target_capability for e in evidence}
        assert CapabilityKey.DATABASE_ENGINEERING in target_caps
        assert CapabilityKey.TESTING_QUALITY in target_caps
        assert CapabilityKey.DEVOPS_CLOUD in target_caps

        for ev in evidence:
            assert ev.source_locator == "https://github.com/candidate/full-platform"
            assert ev.immutable_revision == "deadbeef9999"
            assert 0.0 <= ev.observed_score <= 100.0
            assert ev.artifact_path is not None
            assert ev.extractor_version == "1.0.0"
            assert len(ev.raw_support_text) > 0
