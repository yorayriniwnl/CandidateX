#!/usr/bin/env python3
"""Database Seeding Script for Candidate Capability Intelligence (CCI).

Seeds multi-tenant organizations, recruiter users, job descriptions across
all canonical roles, and diverse candidate cohorts with mathematically rigorous,
paper-aligned dossiers, immutable evidence rows, and interview probe inquiries.
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

# Add backend src directory to Python path
BACKEND_SRC = Path(__file__).resolve().parent.parent / "services" / "backend" / "src"
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_SRC))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cci.config import settings
from cci.db.base import Base
import cci.db.repository as repo
from cci.domain.contracts import (
    CandidateManifest,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NormalizedRequirement,
    RoleProfile,
)
from cci.domain.enums import (
    CanonicalRole,
    CapabilityKey,
    RequirementPriority,
    SourceFamily,
)
from cci.jobs.parser import extract_requirements_from_jd
from cci.pipeline.orchestrator import execute_analysis_pipeline
from cci.scoring.weights import build_role_profile


def read_fixture(filename: str, fallback_text: str = "") -> str:
    """Reads fixture file from examples/ directory if it exists."""
    p = ROOT_DIR / "examples" / filename
    if p.exists():
        return p.read_text(encoding="utf-8")
    return fallback_text


def create_evidence_record(
    locator: str,
    target_cap: CapabilityKey,
    score: float,
    is_pos: bool = True,
    artifact_integrity: float = 0.95,
    ownership_score: float = 0.92,
    recency_factor: float = 0.90,
    verification_level: float = 0.90,
    depth_specificity: float = 0.85,
    source_reliability: float = 0.88,
    raw_support: str = "Verified static observation in codebase",
    artifact_path: str = "src/main.py",
) -> EvidenceRecord:
    """Helper to construct calibrated EvidenceRecord with 6-factor confidence."""
    cf = EvidenceConfidenceFactors(
        artifact_integrity=artifact_integrity,
        ownership_score=ownership_score,
        recency_factor=recency_factor,
        verification_level=verification_level,
        depth_specificity=depth_specificity,
        source_reliability=source_reliability,
    )
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint=f"fp_{target_cap.value}_{uuid4().hex[:12]}",
        source_family=SourceFamily.GITHUB,
        source_locator=locator,
        immutable_revision="HEAD",
        target_capability=target_cap,
        support_score=score,
        is_positive_support=is_pos,
        confidence_factors=cf,
        confidence=cf.composite_confidence,
        provenance={
            "source_locator": locator,
            "artifact_path": artifact_path,
            "raw_support_text": raw_support,
            "analyzer_version": "1.0.0",
        },
    )


def seed_database(db_url: str, reset: bool = False, samples_count: int = 7) -> None:
    """Orchestrates database table initialization and comprehensive data seeding."""
    print("=" * 76)
    print("  Candidate Capability Intelligence (CCI) — Database Seeder")
    print("=" * 76)
    print(f"Target Database: {db_url}")

    # Create engine and session
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(db_url, connect_args=connect_args)

    if reset:
        print("[*] Reset requested: Dropping all existing database tables...")
        Base.metadata.drop_all(bind=engine)
        print("[+] Tables dropped successfully.")

    print("[*] Ensuring all 38+ paper-aligned tables exist...")
    repo.init_db(engine)
    print("[+] Database schema verified.")

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    try:
        # ----------------------------------------------------------------------
        # 1. Multi-Tenant Organizations & Users
        # ----------------------------------------------------------------------
        print("\n[*] Seeding Multi-Tenant Organizations and Recruiters...")
        org_acme = repo.save_organization(
            session=session,
            name="Acme Distributed Systems Corp",
            slug="acme-systems",
            settings={"tier": "enterprise", "enable_ml_analysis": True},
        )
        org_apex = repo.save_organization(
            session=session,
            name="Apex AI Research Labs",
            slug="apex-ai-labs",
            settings={"tier": "research", "enable_ml_analysis": True},
        )

        user1 = repo.save_user(
            session=session,
            organization_id=org_acme.id,
            email="sarah.jenkins@acmesystems.com",
            full_name="Sarah Jenkins",
            role="lead_interviewer",
        )
        user2 = repo.save_user(
            session=session,
            organization_id=org_acme.id,
            email="recruiter@acmesystems.com",
            full_name="David Miller",
            role="recruiter",
        )
        user3 = repo.save_user(
            session=session,
            organization_id=org_apex.id,
            email="rachel.vance@apexlabs.ai",
            full_name="Dr. Rachel Vance",
            role="hiring_manager",
        )
        session.commit()
        print(f"  [+] Organizations: {org_acme.name}, {org_apex.name}")
        print(f"  [+] Users: {user1.email}, {user2.email}, {user3.email}")

        # ----------------------------------------------------------------------
        # 2. Job Descriptions Across Canonical Roles
        # ----------------------------------------------------------------------
        print("\n[*] Seeding Canonical Job Descriptions and Softmax Role Profiles...")
        jd_specs = [
            (
                "Senior Backend Distributed Infrastructure Engineer",
                CanonicalRole.BACKEND,
                org_acme.id,
                read_fixture("sample_backend_jd.txt", "Senior Backend Engineer with Python, Go, PostgreSQL, Kafka."),
            ),
            (
                "Staff Frontend Platform & Web Applications Engineer",
                CanonicalRole.FRONTEND,
                org_acme.id,
                read_fixture("sample_frontend_jd.txt", "Staff Frontend Engineer with React, TypeScript, Next.js, Web Vitals."),
            ),
            (
                "Senior Machine Learning & Applied AI Systems Engineer",
                CanonicalRole.ML_ENGINEER,
                org_apex.id,
                read_fixture("sample_ml_jd.txt", "Senior ML Engineer with PyTorch, Transformers, vLLM, Evaluation."),
            ),
            (
                "Staff Site Reliability & Infrastructure Engineer",
                CanonicalRole.DEVOPS_CLOUD,
                org_acme.id,
                read_fixture("sample_devops_jd.txt", "Staff SRE with Kubernetes, Terraform, Prometheus, Incident Command."),
            ),
            (
                "Lead Fullstack Product Engineer",
                CanonicalRole.FULLSTACK,
                org_acme.id,
                read_fixture("sample_fullstack_jd.txt", "Lead Fullstack Engineer with React, Node.js, PostgreSQL, Redis."),
            ),
        ]

        saved_jds = {}
        for title, role, org_id, jd_raw in jd_specs:
            reqs = extract_requirements_from_jd(jd_raw)
            profile = build_role_profile(reqs, role)
            jd_entity = repo.save_job_description(
                session=session,
                organization_id=org_id,
                title=title,
                canonical_role=role,
                raw_text=jd_raw,
                role_profile=profile,
                requirements=reqs,
            )
            saved_jds[role] = jd_entity
            print(f"  [+] JD: {title} ({len(reqs)} requirements extracted, role: {role.value})")

        session.commit()

        # ----------------------------------------------------------------------
        # 3. Seed Candidate Cohorts & Execute Analysis Pipelines
        # ----------------------------------------------------------------------
        print("\n[*] Executing CCI Pipeline and Generating Dossiers for Seed Candidates...")

        # Cohort definitions
        cohorts = [
            {
                "id": UUID("11111111-1111-1111-1111-111111111111"),
                "name": "Ayush Roy",
                "email": "2329027@kiit.ac.in",
                "role": CanonicalRole.BACKEND,
                "org_id": org_acme.id,
                "cv_file": "sample_backend_cv.txt",
                "jd_role": CanonicalRole.BACKEND,
                "repos": [
                    "https://github.com/alicechen-dev/distributed-payment-engine",
                    "https://github.com/alicechen-dev/pg-partition-manager",
                ],
                "evidence": [
                    create_evidence_record("https://github.com/alicechen-dev/distributed-payment-engine", CapabilityKey.BACKEND_ENGINEERING, 88.0, artifact_path="src/reconciler.go"),
                    create_evidence_record("https://github.com/alicechen-dev/distributed-payment-engine", CapabilityKey.BACKEND_ENGINEERING, 92.0, artifact_path="src/outbox/publisher.go"),
                    create_evidence_record("https://github.com/alicechen-dev/pg-partition-manager", CapabilityKey.DATABASE_ENGINEERING, 89.0, artifact_path="alembic/versions/partition_table.py"),
                    create_evidence_record("https://github.com/alicechen-dev/pg-partition-manager", CapabilityKey.DATABASE_ENGINEERING, 85.0, artifact_path="src/partition/manager.py"),
                    create_evidence_record("https://github.com/alicechen-dev/distributed-payment-engine", CapabilityKey.TESTING_QUALITY, 87.0, artifact_path="tests/integration/reconciler_test.go"),
                    create_evidence_record("https://github.com/alicechen-dev/distributed-payment-engine", CapabilityKey.SOFTWARE_ARCHITECTURE, 90.0, artifact_path="docs/adr/0002-transactional-outbox.md"),
                    create_evidence_record("https://github.com/alicechen-dev/distributed-payment-engine", CapabilityKey.DEVOPS_CLOUD, 78.0, artifact_path="deploy/k8s/deployment.yaml"),
                ],
            },
            {
                "id": UUID("22222222-2222-2222-2222-222222222222"),
                "name": "Archi Srivastava",
                "email": "2329100@kiit.ac.in",
                "role": CanonicalRole.FRONTEND,
                "org_id": org_acme.id,
                "cv_file": "sample_frontend_cv.txt",
                "jd_role": CanonicalRole.FRONTEND,
                "repos": [
                    "https://github.com/erostova-web/a11y-kit-react",
                    "https://github.com/erostova-web/next-vitals-booster",
                ],
                "evidence": [
                    create_evidence_record("https://github.com/erostova-web/a11y-kit-react", CapabilityKey.FRONTEND_ENGINEERING, 93.0, artifact_path="src/primitives/dialog.tsx"),
                    create_evidence_record("https://github.com/erostova-web/a11y-kit-react", CapabilityKey.FRONTEND_ENGINEERING, 91.0, artifact_path="src/primitives/combobox.tsx"),
                    create_evidence_record("https://github.com/erostova-web/next-vitals-booster", CapabilityKey.FRONTEND_ENGINEERING, 89.0, artifact_path="src/vitals/prefetch.ts"),
                    create_evidence_record("https://github.com/erostova-web/a11y-kit-react", CapabilityKey.TESTING_QUALITY, 94.0, artifact_path="tests/a11y/axe.spec.ts"),
                    create_evidence_record("https://github.com/erostova-web/a11y-kit-react", CapabilityKey.SOFTWARE_ARCHITECTURE, 86.0, artifact_path="docs/design-system-tokens.md"),
                    create_evidence_record("https://github.com/erostova-web/a11y-kit-react", CapabilityKey.DOCUMENTATION_COMMUNICATION, 90.0, artifact_path="README.md"),
                ],
            },
            {
                "id": UUID("33333333-3333-3333-3333-333333333333"),
                "name": "Atmaja Tripathy",
                "email": "2329179@kiit.ac.in",
                "role": CanonicalRole.ML_ENGINEER,
                "org_id": org_apex.id,
                "cv_file": "sample_ml_cv.txt",
                "jd_role": CanonicalRole.ML_ENGINEER,
                "repos": [
                    "https://github.com/mthorne-ai/fast-alignment",
                    "https://github.com/mthorne-ai/vector-gateway-service",
                ],
                "evidence": [
                    create_evidence_record("https://github.com/mthorne-ai/fast-alignment", CapabilityKey.MACHINE_LEARNING, 94.0, artifact_path="src/calibration/dpo_loss.py"),
                    create_evidence_record("https://github.com/mthorne-ai/fast-alignment", CapabilityKey.MACHINE_LEARNING, 90.0, artifact_path="src/evaluation/leakage_guard.py"),
                    create_evidence_record("https://github.com/mthorne-ai/vector-gateway-service", CapabilityKey.BACKEND_ENGINEERING, 86.0, artifact_path="service/grpc_server.py"),
                    create_evidence_record("https://github.com/mthorne-ai/vector-gateway-service", CapabilityKey.SOFTWARE_ARCHITECTURE, 88.0, artifact_path="docs/architecture_grpc.md"),
                    create_evidence_record("https://github.com/mthorne-ai/fast-alignment", CapabilityKey.TESTING_QUALITY, 85.0, artifact_path="tests/test_dpo_gradient.py"),
                ],
            },
            {
                "id": UUID("44444444-4444-4444-4444-444444444444"),
                "name": "Shreya",
                "email": "2329065@kiit.ac.in",
                "role": CanonicalRole.DEVOPS_CLOUD,
                "org_id": org_acme.id,
                "cv_file": "sample_devops_cv.txt",
                "jd_role": CanonicalRole.DEVOPS_CLOUD,
                "repos": [
                    "https://github.com/tmansour-infra/tf-blast-guard",
                    "https://github.com/tmansour-infra/k8s-region-failover",
                ],
                "evidence": [
                    create_evidence_record("https://github.com/tmansour-infra/tf-blast-guard", CapabilityKey.DEVOPS_CLOUD, 95.0, artifact_path="policies/rds_drop_guard.rego"),
                    create_evidence_record("https://github.com/tmansour-infra/k8s-region-failover", CapabilityKey.DEVOPS_CLOUD, 92.0, artifact_path="controller/main.go"),
                    create_evidence_record("https://github.com/tmansour-infra/tf-blast-guard", CapabilityKey.SECURITY, 91.0, artifact_path="src/analyzer/blast_radius.go"),
                    create_evidence_record("https://github.com/tmansour-infra/k8s-region-failover", CapabilityKey.SOFTWARE_ARCHITECTURE, 89.0, artifact_path="docs/failover_sequence.md"),
                    create_evidence_record("https://github.com/tmansour-infra/tf-blast-guard", CapabilityKey.TESTING_QUALITY, 88.0, artifact_path="tests/e2e/blast_test.go"),
                ],
            },
            {
                "id": UUID("55555555-5555-5555-5555-555555555555"),
                "name": "Shreshth Nigam",
                "email": "2329064@kiit.ac.in",
                "role": CanonicalRole.FULLSTACK,
                "org_id": org_acme.id,
                "cv_file": "sample_fullstack_cv.txt",
                "jd_role": CanonicalRole.FULLSTACK,
                "repos": [
                    "https://github.com/soconnor-fullstack/type-safe-stack",
                    "https://github.com/soconnor-fullstack/collab-canvas",
                ],
                "evidence": [
                    create_evidence_record("https://github.com/soconnor-fullstack/type-safe-stack", CapabilityKey.FRONTEND_ENGINEERING, 87.0, artifact_path="apps/web/pages/index.tsx"),
                    create_evidence_record("https://github.com/soconnor-fullstack/type-safe-stack", CapabilityKey.BACKEND_ENGINEERING, 88.0, artifact_path="packages/api/src/router.ts"),
                    create_evidence_record("https://github.com/soconnor-fullstack/type-safe-stack", CapabilityKey.DATABASE_ENGINEERING, 84.0, artifact_path="prisma/schema.prisma"),
                    create_evidence_record("https://github.com/soconnor-fullstack/type-safe-stack", CapabilityKey.TESTING_QUALITY, 86.0, artifact_path="tests/trpc/mutations.test.ts"),
                    create_evidence_record("https://github.com/soconnor-fullstack/collab-canvas", CapabilityKey.SOFTWARE_ARCHITECTURE, 89.0, artifact_path="docs/crdt_model.md"),
                ],
            },
            {
                "id": UUID("66666666-6666-6666-6666-666666666666"),
                "name": "Jordan Blake (Sparse / Junior)",
                "email": "jordan.blake@example.com",
                "role": CanonicalRole.BACKEND,
                "org_id": org_acme.id,
                "cv_file": "",
                "jd_role": CanonicalRole.BACKEND,
                "repos": [
                    "https://github.com/jordanblake-dev/mini-calculator-script",
                ],
                "evidence": [
                    create_evidence_record(
                        "https://github.com/jordanblake-dev/mini-calculator-script",
                        CapabilityKey.BACKEND_ENGINEERING,
                        62.0,
                        artifact_integrity=0.80,
                        ownership_score=0.70,
                        recency_factor=0.60,
                        verification_level=0.50,
                        depth_specificity=0.40,
                        source_reliability=0.70,
                        raw_support="Simple single-file script without modular abstractions or tests",
                        artifact_path="calc.py",
                    ),
                ],
            },
            {
                "id": UUID("77777777-7777-7777-7777-777777777777"),
                "name": "Devin Vance (Contradictory / Discrepancy)",
                "email": "devin.vance@example.com",
                "role": CanonicalRole.BACKEND,
                "org_id": org_acme.id,
                "cv_file": "",
                "jd_role": CanonicalRole.BACKEND,
                "repos": [
                    "https://github.com/devinvance-dev/distributed-order-service",
                ],
                "evidence": [
                    create_evidence_record(
                        "https://github.com/devinvance-dev/distributed-order-service",
                        CapabilityKey.DATABASE_ENGINEERING,
                        88.0,
                        is_pos=True,
                        raw_support="Declared high-performance relational storage architecture",
                        artifact_path="docs/database_claims.md",
                    ),
                    create_evidence_record(
                        "https://github.com/devinvance-dev/distributed-order-service",
                        CapabilityKey.DATABASE_ENGINEERING,
                        15.0,
                        is_pos=False,
                        raw_support="Direct observation: No schema indices, raw SELECT * in unpaginated loops, no transaction rollback handling",
                        artifact_path="src/db/queries.py",
                    ),
                    create_evidence_record(
                        "https://github.com/devinvance-dev/distributed-order-service",
                        CapabilityKey.BACKEND_ENGINEERING,
                        70.0,
                        is_pos=True,
                        artifact_path="src/server.py",
                    ),
                ],
            },
        ]

        summary_rows = []
        for candidate_data in cohorts[:samples_count]:
            cid = candidate_data["id"]
            name = candidate_data["name"]
            c_role = candidate_data["role"]
            org_id = candidate_data["org_id"]
            cv_raw = read_fixture(candidate_data["cv_file"], f"# {name}\nEngineer specializing in {c_role.value}.") if candidate_data["cv_file"] else f"# {name}\nCandidate CV for {c_role.value}."
            jd_raw = saved_jds[candidate_data["jd_role"]].raw_text

            manifest = CandidateManifest(
                display_name=name,
                email=candidate_data["email"],
                github_urls=candidate_data["repos"],
                claimed_skills=[c_role.value, "Git", "Clean Architecture"],
            )

            # Persist candidate
            cand_entity = repo.save_candidate(
                session=session,
                organization_id=org_id,
                manifest=manifest,
                candidate_id=cid,
            )

            # Execute the paper-aligned pipeline
            state = execute_analysis_pipeline(
                candidate_id=cid,
                role=c_role,
                jd_text=jd_raw,
                cv_text=cv_raw,
                repo_urls=candidate_data["repos"],
                custom_evidence=candidate_data["evidence"],
            )

            if state.dossier:
                repo.save_dossier(
                    session=session,
                    dossier=state.dossier,
                    organization_id=org_id,
                    custom_evidence=candidate_data["evidence"],
                )
                session.commit()

                # Register in-memory as well
                try:
                    from cci.api.routers.dossier import register_dossier
                    register_dossier(state.dossier, state.ceg_graph)
                except Exception:
                    pass

                d = state.dossier
                rci_str = f"{d.rci:.1f}" if d.rci is not None else "N/A"
                cov_str = f"{d.coverage * 100:.1f}%"
                warn_str = "INSUFFICIENT" if d.is_insufficient_evidence else "ROBUST"
                probes_cnt = len(d.interview_probes)

                # Check if conflict exists
                has_conflict = any(c.has_meaningful_conflict for c in d.capability_conflicts.values())
                flag_str = "CONFLICT FLAG" if has_conflict else ("SPARSE WARNING" if d.is_insufficient_evidence else "OK")

                summary_rows.append((name, c_role.value, rci_str, cov_str, warn_str, probes_cnt, flag_str))
                print(f"  [+] Seeded Candidate: {name:<35} | RCI: {rci_str:>5} | Cov: {cov_str:>6} | Status: {warn_str}")

        print("\n" + "=" * 88)
        print(f"  {'Candidate':<35} | {'Role':<12} | {'RCI':<6} | {'Cov':<7} | {'Evidence':<10} | {'Status'}")
        print("=" * 88)
        for row in summary_rows:
            print(f"  {row[0]:<35} | {row[1]:<12} | {row[2]:<6} | {row[3]:<7} | {row[4]:<10} | {row[6]}")
        print("=" * 88)
        print(f"\n[+] Seeding successfully completed. {len(summary_rows)} candidate dossiers committed to database.")

    except Exception as e:
        session.rollback()
        print(f"[!] Error occurred during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Candidate Capability Intelligence (CCI) Database Seeder")
    parser.add_argument(
        "--db-url",
        type=str,
        default=settings.DATABASE_URL,
        help="Database connection URL (defaults to settings.DATABASE_URL)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all database tables before seeding",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=7,
        help="Number of candidate cohorts to seed (default: 7)",
    )
    args = parser.parse_args()

    seed_database(
        db_url=args.db_url,
        reset=args.reset,
        samples_count=args.samples,
    )


if __name__ == "__main__":
    main()
