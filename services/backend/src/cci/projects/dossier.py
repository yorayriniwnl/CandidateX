"""Project entity builder and dossier rebuilding module (Fix 40).

Enforces the core hardening invariants:
1. Every claimed project is modeled as a distinct, first-class traceable entity.
2. For each project, 16 key facets are extracted and preserved:
   - resume claim
   - repository
   - deployment
   - documentation
   - technologies
   - DB
   - backend
   - frontend
   - tests
   - infrastructure
   - candidate attribution
   - recency
   - credentials/publication relationship
   - quantitative claims
   - contradictions
   - limitations
3. The project is completely traceable: claim -> source -> artifact -> observation.
4. Candidate code is NEVER executed.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, uuid5

from cci.domain.contracts import EvidenceRecord, ProjectEntity, ProjectTraceLink


PROJECT_LIMITATIONS: list[str] = [
    "Project declarations on resume do not prove solo execution or production scale without independent verification.",
    "Candidate repository code is inspected statically and never executed.",
    "Repository presence establishes source existence, but candidate attribution requires commit authorship verification.",
    "Absence of specific architectural components in sampled files does not guarantee absence in un-sampled commits.",
]

DB_KEYWORDS: dict[str, str] = {
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "dynamodb": "DynamoDB",
    "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch",
    "prisma": "Prisma",
    "sqlalchemy": "SQLAlchemy",
    "alembic": "Alembic",
    "mongoose": "Mongoose",
    "typeorm": "TypeORM",
}

BACKEND_FRAMEWORKS: dict[str, str] = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "express": "Express",
    "nestjs": "NestJS",
    "spring": "Spring Boot",
    "gin": "Gin",
    "actix": "Actix",
    "rails": "Ruby on Rails",
    "asp.net": "ASP.NET",
    "tornado": "Tornado",
}

FRONTEND_FRAMEWORKS: dict[str, str] = {
    "react": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "angular": "Angular",
    "svelte": "Svelte",
    "tailwindcss": "TailwindCSS",
    "bootstrap": "Bootstrap",
    "redux": "Redux",
    "html": "HTML/CSS",
    "css": "HTML/CSS",
}

TEST_FRAMEWORKS: dict[str, str] = {
    "pytest": "pytest",
    "unittest": "unittest",
    "jest": "Jest",
    "mocha": "Mocha",
    "vitest": "Vitest",
    "cypress": "Cypress",
    "playwright": "Playwright",
    "junit": "JUnit",
}

INFRASTRUCTURE_KEYWORDS: dict[str, str] = {
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "docker-compose": "Docker Compose",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "helm": "Helm",
    "nginx": "Nginx",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
}


def extract_quantitative_claims(text: str) -> list[dict[str, Any]]:
    """Extracts structured metric and quantitative claims from project claim text (Fix 40 & Fix 41 foundation)."""
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Pattern 1: Percentages (e.g., 95% accuracy, 99.9% uptime, 40% optimization)
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*%\s*([a-zA-Z_-]{3,20})(?!\w)", text, re.IGNORECASE):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        val_str, metric = m.group(1), m.group(2).strip()
        claims.append({
            "raw_text": raw,
            "metric": metric.lower(),
            "value": float(val_str) if "." in val_str else int(val_str),
            "unit": "%",
            "context": f"{val_str}% {metric}",
            "source": "resume_project_claim",
            "verification_status": "unverified",
        })

    # Pattern 2: Scale/counts (e.g., 10k users, 5B tokens, 500 tests, 20 deployed projects, 500k transactions)
    for m in re.finditer(
        r"\b(\d+(?:\.\d+)?[kKmMbB]?\+?)\s+(users|customers|queries|requests|req/s|rps|tx/s|transactions|tx|tokens|tests|test cases|deployed projects|projects|microservices|stars|commits)\b",
        text,
        re.IGNORECASE,
    ):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        val_str, unit = m.group(1), m.group(2).strip()
        claims.append({
            "raw_text": raw,
            "metric": unit.lower().replace(" ", "_"),
            "value": val_str,
            "unit": unit.lower(),
            "context": raw,
            "source": "resume_project_claim",
            "verification_status": "unverified",
        })

    # Pattern 3: Latency/performance (e.g., 5ms latency, 100ms response time)
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(ms|s|seconds)\s+(latency|response time|p99|p95)\b", text, re.IGNORECASE):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        val_str, unit, metric = m.group(1), m.group(2).strip(), m.group(3).strip()
        claims.append({
            "raw_text": raw,
            "metric": metric.lower().replace(" ", "_"),
            "value": float(val_str) if "." in val_str else int(val_str),
            "unit": unit.lower(),
            "context": raw,
            "source": "resume_project_claim",
            "verification_status": "unverified",
        })

    # Pattern 4: Optimization reductions (e.g., reduced latency by 40%, improved speed by 3x)
    for m in re.finditer(r"\b(reduced|optimized|improved|increased)\s+([a-zA-Z\s]{3,20})\s+by\s+(\d+(?:\.\d+)?(?:%|x)?)(?!\w)", text, re.IGNORECASE):
        raw = m.group(0).strip()
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        action, target, change = m.group(1), m.group(2).strip(), m.group(3).strip()
        claims.append({
            "raw_text": raw,
            "metric": f"{action.lower()}_{target.lower().replace(' ', '_')}",
            "value": change,
            "unit": "%" if change.endswith("%") else "multiplier",
            "context": raw,
            "source": "resume_project_claim",
            "verification_status": "unverified",
        })

    return claims


def _match_repository(
    project_text: str,
    sources: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Matches a project claim against available repository sources."""
    text_lower = project_text.lower()

    # Only consider sources that are actually code repositories
    repo_sources = [
        s for s in sources
        if s.get("kind") == "github" or "github.com" in str(s.get("url", "")).lower()
    ]
    if not repo_sources:
        return None

    # Priority 1: Explicit repository URL in project text
    for s in repo_sources:
        url = str(s.get("url", "")).strip()
        clean_url = url.removeprefix("https://").removeprefix("http://").rstrip("/").lower()
        if clean_url in text_lower:
            return s

    # Priority 2: Repository slug or name match
    for s in repo_sources:
        url = str(s.get("url", "")).strip()
        parsed = urlparse(url)
        path = parsed.path.strip("/").lower()
        repo_slug = path.split("/")[-1] if "/" in path else path
        if repo_slug and len(repo_slug) >= 3 and repo_slug in text_lower:
            return s
        repo_name_clean = repo_slug.replace("-", " ").replace("_", " ")
        if repo_name_clean and len(repo_name_clean) >= 4 and repo_name_clean in text_lower:
            return s

    # Priority 3: If only one repository source exists, match it
    if len(repo_sources) == 1:
        return repo_sources[0]

    return None


def _match_deployment(
    project_text: str,
    sources: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Matches a project claim against live deployment sources."""
    text_lower = project_text.lower()
    deploy_sources = [
        s for s in sources
        if s.get("kind") == "deployment"
        or (
            "github.com" not in str(s.get("url", "")).lower()
            and "linkedin.com" not in str(s.get("url", "")).lower()
            and "credly.com" not in str(s.get("url", "")).lower()
            and "leetcode.com" not in str(s.get("url", "")).lower()
        )
    ]
    if not deploy_sources:
        return None

    for s in deploy_sources:
        url = str(s.get("url", "")).strip()
        if not url:
            continue
        clean_url = url.removeprefix("https://").removeprefix("http://").rstrip("/").lower()
        if clean_url in text_lower:
            return s

    # If only one deployment source exists, match it
    if len(deploy_sources) == 1:
        return deploy_sources[0]

    return None


def _extract_technologies(
    project_claim: Mapping[str, Any],
    repo_source: Mapping[str, Any] | None,
    evidence_records: Sequence[EvidenceRecord],
) -> list[str]:
    """Combines self-reported and statically detected technologies for the project."""
    technologies: list[str] = []
    seen: set[str] = set()

    def add(t: str):
        clean = t.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            technologies.append(clean)

    # From resume claim
    for t in project_claim.get("technologies", []):
        add(t)

    # From repository review
    if repo_source:
        repo_rev = repo_source.get("repository_review", {})
        for t in repo_rev.get("technologies", []):
            if isinstance(t, dict):
                add(t.get("name", ""))
            elif isinstance(t, str):
                add(t)
        for lang in repo_source.get("languages", []):
            add(lang)

    # From evidence records matching this source
    repo_url = repo_source.get("url") if repo_source else None
    for ev in evidence_records:
        if repo_url and ev.source_locator == repo_url:
            tech = ev.provenance.get("technology")
            if tech:
                add(tech)

    # Keyword search in project text
    text = f"{project_claim.get('title', '')} {project_claim.get('description', '')}".lower()
    all_known = {**DB_KEYWORDS, **BACKEND_FRAMEWORKS, **FRONTEND_FRAMEWORKS, **TEST_FRAMEWORKS, **INFRASTRUCTURE_KEYWORDS}
    for kw, canonical in all_known.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            add(canonical)

    return technologies


def _extract_db_components(
    technologies: Sequence[str],
    artifact_paths: Sequence[str],
) -> list[dict[str, Any]]:
    """Identifies database architectures, schemas, ORMs, and migration files."""
    db_items: list[dict[str, Any]] = []
    seen_techs: set[str] = set()

    for tech in technologies:
        tech_lower = tech.lower()
        if tech_lower in DB_KEYWORDS or any(db_k in tech_lower for db_k in DB_KEYWORDS):
            canonical = DB_KEYWORDS.get(tech_lower, tech)
            if canonical in seen_techs:
                continue
            seen_techs.add(canonical)
            db_type = "relational" if canonical in ("PostgreSQL", "MySQL", "SQLite", "SQLAlchemy", "Alembic") else "nosql_or_cache"
            matched_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("db", "model", "schema", "migration", "prisma", "sql", "alembic"))]
            db_items.append({
                "technology": canonical,
                "type": db_type,
                "matched_artifacts": matched_arts,
            })

    # If no technology hit, but migration/schema files exist
    if not db_items:
        schema_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("schema", "migration", "models.py", "alembic"))]
        if schema_arts:
            db_items.append({
                "technology": "Schema/Migrations",
                "type": "database_definitions",
                "matched_artifacts": schema_arts,
            })

    return db_items


def _extract_backend_components(
    technologies: Sequence[str],
    artifact_paths: Sequence[str],
) -> list[dict[str, Any]]:
    """Identifies backend services, API frameworks, and routing artifacts."""
    backend_items: list[dict[str, Any]] = []
    seen_frameworks: set[str] = set()

    for tech in technologies:
        tech_lower = tech.lower()
        if tech_lower in BACKEND_FRAMEWORKS or any(bw in tech_lower for bw in BACKEND_FRAMEWORKS):
            canonical = BACKEND_FRAMEWORKS.get(tech_lower, tech)
            if canonical in seen_frameworks:
                continue
            seen_frameworks.add(canonical)
            matched_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("api", "server", "routes", "controller", "app.py", "main.py", "service"))]
            backend_items.append({
                "framework": canonical,
                "matched_artifacts": matched_arts,
            })

    if not backend_items:
        server_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("api", "server", "routes", "app.py", "main.py"))]
        if server_arts:
            backend_items.append({
                "framework": "Custom Backend Service",
                "matched_artifacts": server_arts,
            })

    return backend_items


def _extract_frontend_components(
    technologies: Sequence[str],
    artifact_paths: Sequence[str],
) -> list[dict[str, Any]]:
    """Identifies frontend frameworks, UI components, and web templates."""
    frontend_items: list[dict[str, Any]] = []
    seen_frameworks: set[str] = set()

    for tech in technologies:
        tech_lower = tech.lower()
        if tech_lower in FRONTEND_FRAMEWORKS or any(fw in tech_lower for fw in FRONTEND_FRAMEWORKS):
            canonical = FRONTEND_FRAMEWORKS.get(tech_lower, tech)
            if canonical in seen_frameworks:
                continue
            seen_frameworks.add(canonical)
            matched_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("ui", "component", "pages", "frontend", ".jsx", ".tsx", ".vue", ".svelte", ".html"))]
            frontend_items.append({
                "framework": canonical,
                "matched_artifacts": matched_arts,
            })

    if not frontend_items:
        ui_arts = [p for p in artifact_paths if any(p.endswith(ext) for ext in (".jsx", ".tsx", ".vue", ".svelte", ".html", ".css"))]
        if ui_arts:
            frontend_items.append({
                "framework": "Static/Web UI",
                "matched_artifacts": ui_arts,
            })

    return frontend_items


def _extract_tests_info(
    technologies: Sequence[str],
    artifact_paths: Sequence[str],
) -> dict[str, Any]:
    """Inspects automated test frameworks, test files, and test coverage indicators."""
    test_files = [p for p in artifact_paths if any(k in p.lower() for k in ("test", "spec", "pytest", "jest"))]
    frameworks: list[str] = []
    for tech in technologies:
        tech_lower = tech.lower()
        if tech_lower in TEST_FRAMEWORKS or any(tw in tech_lower for tw in TEST_FRAMEWORKS):
            canonical = TEST_FRAMEWORKS.get(tech_lower, tech)
            if canonical not in frameworks:
                frameworks.append(canonical)

    return {
        "frameworks_detected": frameworks,
        "test_files": test_files,
        "test_file_count": len(test_files),
        "has_automated_tests": len(test_files) > 0,
        "explanation": "Static inspection of test directories; test execution is strictly prevented.",
    }


def _extract_infrastructure(
    technologies: Sequence[str],
    artifact_paths: Sequence[str],
) -> list[dict[str, Any]]:
    """Identifies infrastructure, Docker, CI/CD, and deployment configurations."""
    infra_items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for tech in technologies:
        tech_lower = tech.lower()
        if tech_lower in INFRASTRUCTURE_KEYWORDS or any(iw in tech_lower for iw in INFRASTRUCTURE_KEYWORDS):
            canonical = INFRASTRUCTURE_KEYWORDS.get(tech_lower, tech)
            if canonical in seen:
                continue
            seen.add(canonical)
            matched_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("docker", "k8s", "ci", "workflow", "terraform", "helm", "nginx"))]
            infra_items.append({
                "component": canonical,
                "matched_artifacts": matched_arts,
            })

    # File-based inspection
    docker_arts = [p for p in artifact_paths if "docker" in p.lower()]
    if docker_arts and "Docker" not in seen:
        infra_items.append({"component": "Docker", "matched_artifacts": docker_arts})
    cicd_arts = [p for p in artifact_paths if any(k in p.lower() for k in ("workflow", "github", "gitlab-ci", "jenkins"))]
    if cicd_arts and "CI/CD" not in seen:
        infra_items.append({"component": "CI/CD", "matched_artifacts": cicd_arts})

    return infra_items


def _extract_credentials_relationship(
    project_text: str,
    technologies: Sequence[str],
    credentials: Sequence[Any],
) -> list[dict[str, Any]]:
    """Matches relevant certificates, publications, arXiv links, or academic research."""
    relationships: list[dict[str, Any]] = []

    # Credentials matching project technologies
    for cred in credentials:
        cred_dict = cred if isinstance(cred, dict) else (cred.to_dict() if hasattr(cred, "to_dict") else getattr(cred, "__dict__", {}))
        cred_name = cred_dict.get("credential_name") or cred_dict.get("title") or cred_dict.get("claim", "")
        if any(tech.lower() in cred_name.lower() for tech in technologies):
            relationships.append({
                "type": "credential",
                "name": cred_name,
                "relationship": f"Credential domain matches project technology stack: {cred_name}",
            })

    # Publications or research in project text
    m_arxiv = re.search(r"\barxiv\b(?::\s*|\.org/(?:abs|pdf)/)([0-9.]+)", project_text, re.IGNORECASE)
    if m_arxiv:
        relationships.append({
            "type": "publication",
            "reference": f"arXiv:{m_arxiv.group(1)}",
            "relationship": "Research preprint cited in project description.",
        })

    m_pub = re.search(r"\b(published in|conference paper|ieee|acm|neurips|icml|cvpr)\b[^\n.]*", project_text, re.IGNORECASE)
    if m_pub:
        relationships.append({
            "type": "publication",
            "reference": m_pub.group(0).strip(),
            "relationship": "Academic publication or conference proceedings declaration.",
        })

    return relationships


def _extract_contradictions(
    repo_url: str | None,
    deploy_url: str | None,
    contradictions: Sequence[Any],
) -> list[dict[str, Any]]:
    """Finds contradictions, framework absences, or negative evidence relevant to this project."""
    matched_contradictions: list[dict[str, Any]] = []
    for c in contradictions:
        c_dict = c if isinstance(c, dict) else (c.to_dict() if hasattr(c, "to_dict") else getattr(c, "__dict__", {}))
        scan_scope = c_dict.get("scan_scope") or {}
        scope_repo = scan_scope.get("repository_scope") or ""
        scope_deploy = scan_scope.get("deployment_url") or ""

        is_match = False
        if repo_url and scope_repo and (scope_repo.lower() in repo_url.lower() or repo_url.lower() in scope_repo.lower()):
            is_match = True
        if deploy_url and scope_deploy and (scope_deploy.lower() in deploy_url.lower() or deploy_url.lower() in scope_deploy.lower()):
            is_match = True

        if is_match:
            matched_contradictions.append(c_dict)

    return matched_contradictions


def build_project_entities(
    project_claims: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]] = (),
    evidence_records: Sequence[EvidenceRecord] = (),
    claims: Sequence[Any] = (),
    contradictions: Sequence[Any] = (),
    credentials: Sequence[Any] = (),
    candidate_identifier: str | None = None,
) -> list[ProjectEntity]:
    """Rebuilds candidate project declarations into fully traceable, 16-facet ProjectEntity dossiers (Fix 40)."""
    entities: list[ProjectEntity] = []

    # Map claims for claim_id linkage
    claim_id_map: dict[str, str] = {}
    for c in claims:
        c_dict = c if isinstance(c, dict) else (c.to_dict() if hasattr(c, "to_dict") else getattr(c, "__dict__", {}))
        c_id = str(c_dict.get("claim_id", ""))
        c_text = str(c_dict.get("original_text") or c_dict.get("claim", "")).lower()
        if c_id and c_text:
            claim_id_map[c_text] = c_id

    for proj in project_claims:
        title = str(proj.get("title", "")).strip() or "Unnamed Project"
        description = str(proj.get("description", "")).strip()
        combined_text = f"{title} {description}".strip()

        project_id = str(uuid5(NAMESPACE_URL, f"project:{title.lower()}"))

        # Find matching claim_id if available
        matched_claim_id = next(
            (cid for ctext, cid in claim_id_map.items() if title.lower() in ctext or ctext in title.lower()),
            None,
        )

        # 1. Resume Claim
        resume_claim = {
            "title": title,
            "description": description,
            "technologies": list(proj.get("technologies", [])),
            "section": proj.get("section", "projects"),
            "source_location": proj.get("source_location"),
            "claim_id": matched_claim_id,
        }

        # 2. Repository matching
        repo_source = _match_repository(combined_text, sources)
        repository: dict[str, Any] | None = None
        repo_url = None
        artifact_paths: list[str] = []

        if repo_source:
            repo_url = str(repo_source.get("url", ""))
            parsed = urlparse(repo_url)
            path_parts = parsed.path.strip("/").split("/")
            repo_owner = path_parts[0] if len(path_parts) > 1 else ""
            repo_name = path_parts[1] if len(path_parts) > 1 else path_parts[0]
            repository = {
                "url": repo_url,
                "name": repo_name,
                "owner": repo_owner,
                "is_fork": repo_source.get("is_fork", False),
                "default_branch": repo_source.get("default_branch", "main"),
                "status": repo_source.get("status", "observed"),
            }
            # Collect artifact paths from repo source review
            repo_rev = repo_source.get("repository_review", {})
            for tech in repo_rev.get("technologies", []):
                p = tech.get("path") if isinstance(tech, dict) else None
                if p and p not in artifact_paths:
                    artifact_paths.append(p)
            for attr in repo_source.get("artifact_attributions", []):
                p = attr.get("artifact_path")
                if p and p not in artifact_paths:
                    artifact_paths.append(p)
            for obs in repo_source.get("observed_files", []):
                if obs not in artifact_paths:
                    artifact_paths.append(obs)

        # 3. Deployment matching
        deploy_source = _match_deployment(combined_text, sources)
        deployment: dict[str, Any] | None = None
        deploy_url = None
        if deploy_source:
            deploy_url = str(deploy_source.get("url", ""))
            deployment = {
                "url": deploy_url,
                "status": deploy_source.get("status", "observed"),
                "reachable": deploy_source.get("status") in ("observed", "fetched", "reachable"),
                "protocol": "https" if deploy_url.startswith("https") else "http",
                "explanation": "Runtime deployment inspected via non-destructive HTTP GET.",
            }

        # 4. Documentation
        doc_files = [p for p in artifact_paths if any(k in p.lower() for k in ("readme", ".md", "doc", "license"))]
        readme_file = next((p for p in artifact_paths if "readme" in p.lower()), None)
        documentation = {
            "has_readme": readme_file is not None,
            "readme_path": readme_file,
            "doc_files": doc_files,
            "explanation": "Repository documentation and markdown structures observed in file tree.",
        }

        # 5. Technologies
        technologies = _extract_technologies(proj, repo_source, evidence_records)

        # 6. DB
        db = _extract_db_components(technologies, artifact_paths)

        # 7. Backend
        backend = _extract_backend_components(technologies, artifact_paths)

        # 8. Frontend
        frontend = _extract_frontend_components(technologies, artifact_paths)

        # 9. Tests
        tests = _extract_tests_info(technologies, artifact_paths)

        # 10. Infrastructure
        infrastructure = _extract_infrastructure(technologies, artifact_paths)

        # 11. Candidate Attribution
        candidate_attribution: dict[str, Any] = {}
        if repo_source:
            attributions = repo_source.get("artifact_attributions", [])
            scores = [a.get("ownership_score", 0.0) for a in attributions if "ownership_score" in a]
            mean_score = sum(scores) / len(scores) if scores else 0.0
            states = [a.get("state") for a in attributions if a.get("state")]
            top_state = states[0] if states else "REPOSITORY_ASSOCIATION_ONLY"
            candidate_attribution = {
                "attribution_state": top_state,
                "ownership_score": round(mean_score, 3),
                "author_login": candidate_identifier,
                "sample_count": len(attributions),
                "explanation": "Attribution derived from git commit author login history for sampled paths.",
            }
        else:
            candidate_attribution = {
                "attribution_state": "UNATTRIBUTED",
                "ownership_score": 0.0,
                "explanation": "No repository source linked; attribution cannot be established.",
            }

        # 12. Recency
        recency: dict[str, Any] = {}
        if repo_source:
            last_activity = repo_source.get("last_activity") or repo_source.get("fetched_at")
            recency = {
                "last_activity": last_activity,
                "basis": "repository_activity_timestamp",
            }
        else:
            recency = {
                "last_activity": None,
                "basis": "no_source_available",
            }

        # 13. Credentials / Publication Relationship
        credentials_rel = _extract_credentials_relationship(combined_text, technologies, credentials)

        # 14. Quantitative Claims
        quant_claims = extract_quantitative_claims(combined_text)

        # 15. Contradictions
        contradictions_matched = _extract_contradictions(repo_url, deploy_url, contradictions)

        # 16. Limitations
        limitations = list(PROJECT_LIMITATIONS)

        # Trace links (claim -> source -> artifact -> observation)
        trace_links: list[ProjectTraceLink] = []

        # Claim to source hop
        if repo_url:
            trace_links.append(
                ProjectTraceLink(
                    link_type="claim_to_source",
                    claim_id=matched_claim_id,
                    source_url=repo_url,
                    summary=f"Project '{title}' linked to repository source '{repo_url}'",
                )
            )
        if deploy_url:
            trace_links.append(
                ProjectTraceLink(
                    link_type="claim_to_source",
                    claim_id=matched_claim_id,
                    source_url=deploy_url,
                    summary=f"Project '{title}' linked to deployment URL '{deploy_url}'",
                )
            )

        # Source to artifact hops
        for art in artifact_paths[:10]:
            trace_links.append(
                ProjectTraceLink(
                    link_type="source_to_artifact",
                    source_url=repo_url,
                    artifact_path=art,
                    summary=f"Artifact '{art}' observed in source '{repo_url}'",
                )
            )

        # Artifact to observation hops
        for ev in evidence_records:
            if repo_url and ev.source_locator == repo_url:
                ev_art = ev.provenance.get("artifact_path")
                trace_links.append(
                    ProjectTraceLink(
                        link_type="artifact_to_observation",
                        artifact_path=ev_art,
                        evidence_id=str(ev.evidence_id),
                        observation_type=ev.observation_type,
                        summary=f"Evidence observed for capability '{ev.target_capability.value}'",
                    )
                )

        entity = ProjectEntity(
            project_id=project_id,
            name=title,
            resume_claim=resume_claim,
            repository=repository,
            deployment=deployment,
            documentation=documentation,
            technologies=technologies,
            db=db,
            backend=backend,
            frontend=frontend,
            tests=tests,
            infrastructure=infrastructure,
            candidate_attribution=candidate_attribution,
            recency=recency,
            credentials_or_publication_relationship=credentials_rel,
            quantitative_claims=quant_claims,
            contradictions=contradictions_matched,
            limitations=limitations,
            trace=trace_links,
        )
        entities.append(entity)

    return entities
