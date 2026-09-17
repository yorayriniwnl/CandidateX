"""Synthetic golden repositories for precision testing of Database, Testing, and DevOps analyzers."""

import os


def create_golden_db_infra_repo(root_dir: str):
    """Populates a repository workspace with realistic database, testing, and devops artifacts."""
    # Directories
    os.makedirs(os.path.join(root_dir, "migrations"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "alembic", "versions"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "prisma"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "tests", "unit"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "tests", "integration"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, ".github", "workflows"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "k8s"), exist_ok=True)
    os.makedirs(os.path.join(root_dir, "terraform"), exist_ok=True)

    # 1. SQL Migration
    with open(os.path.join(root_dir, "migrations", "001_initial_schema.sql"), "w") as f:
        f.write("""-- Initial database schema
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX idx_users_email ON users (email);
CREATE INDEX idx_orders_user_amount ON orders (user_id, amount);

CREATE TABLE audit_logs (
    id UUID NOT NULL,
    logged_at TIMESTAMP NOT NULL
) PARTITION BY RANGE (logged_at);
""")

    # 2. Alembic Migration
    with open(os.path.join(root_dir, "alembic", "versions", "0002_add_tenancy.py"), "w") as f:
        f.write("""from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])

def downgrade():
    op.drop_table('tenants')
""")

    # 3. Prisma Schema
    with open(os.path.join(root_dir, "prisma", "schema.prisma"), "w") as f:
        f.write("""datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Organization {
  id        String   @id @default(uuid())
  name      String
  members   Member[]
  @@unique([name])
}

model Member {
  id             String       @id @default(uuid())
  orgId          String
  organization   Organization @relation(fields: [orgId], references: [id])
  @@index([orgId])
}
""")

    # 4. Python Tests (pytest + fixtures + parametrize + hypothesis)
    with open(os.path.join(root_dir, "tests", "unit", "test_user_service.py"), "w") as f:
        f.write("""import pytest
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st

@pytest.fixture
def mock_db():
    client = MagicMock()
    yield client
    client.close()

@pytest.mark.parametrize("input_val, expected", [
    (1, 2),
    (2, 4),
])
def test_doubler(mock_db, input_val, expected):
    assert input_val * 2 == expected

@given(st.integers())
def test_invariance(x):
    assert x + 0 == x

def test_mocked_network():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        assert mock_get().status_code == 200
""")

    # 5. TypeScript Tests (Jest / Supertest)
    with open(os.path.join(root_dir, "tests", "integration", "api.spec.ts"), "w") as f:
        f.write("""import request from "supertest";

describe("API Test Suite", () => {
    beforeEach(() => {
        // setup
    });

    it("should return healthy status", async () => {
        // test logic
    });
});
""")

    # 6. Go Tests (table-driven + t.Run)
    with open(os.path.join(root_dir, "tests", "calc_test.go"), "w") as f:
        f.write("""package tests
import "testing"

func TestCalculator(t *testing.T) {
    tests := []struct{
        name string
        in   int
        want int
    }{
        {"positive", 2, 4},
        {"zero", 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if tt.in*2 != tt.want {
                t.Errorf("got %d, want %d", tt.in*2, tt.want)
            }
        })
    }
}
""")

    # 7. Multi-stage Dockerfile
    with open(os.path.join(root_dir, "Dockerfile"), "w") as f:
        f.write("""FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM python:3.11-slim AS runner
WORKDIR /app
COPY --from=builder /app /app
USER appuser
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["python", "main.py"]
""")

    # 8. Docker Compose
    with open(os.path.join(root_dir, "docker-compose.yml"), "w") as f:
        f.write("""version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    networks:
      - backend-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
  postgres:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - backend-net
networks:
  backend-net:
    driver: bridge
volumes:
  pgdata:
""")

    # 9. GitHub Actions CI
    with open(os.path.join(root_dir, ".github", "workflows", "ci.yml"), "w") as f:
        f.write("""name: CI Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - name: Run Pytest
        run: pytest -v
""")

    # 10. Kubernetes Manifest
    with open(os.path.join(root_dir, "k8s", "deployment.yaml"), "w") as f:
        f.write("""apiVersion: apps/v1
kind: Deployment
metadata:
  name: core-service
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: app
          image: cci/app:latest
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8000
""")

    # 11. Terraform HCL
    with open(os.path.join(root_dir, "terraform", "main.tf"), "w") as f:
        f.write("""resource "aws_s3_bucket" "storage" {
  bucket = "candidatex-artifacts"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
}
""")
