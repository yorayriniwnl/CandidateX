"""Role-aware repository prioritization engine (Fix 23).

Replaces newest-repositories-first heuristics with multidimensional priority scoring:
1. Explicitly supplied repository
2. Resume-linked repository
3. Project-title similarity
4. Technology relevance
5. Role relevance
6. Deployment linkage
7. Portfolio linkage
8. Non-fork preference (fork penalty)
9. Engineering depth (size, stars, complexity)
10. Recent meaningful activity

Invariants:
1. Every selected repository records a human-auditable `selection_reason`.
2. Non-selected repositories remain visible as `inventory_only` or `deferred`.
3. No repository silently disappears from analysis inventory or receipts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from cci.domain.enums import CanonicalRole


@dataclass(frozen=True)
class RepositoryPriorityResult:
    """Calculated priority ranking and selection rationale for a candidate repository."""
    url: str
    name: str
    priority_score: float
    is_selected: bool
    inspection_status: str  # "observed", "deferred", or "inventory_only"
    selection_reason: str | None
    deferral_reason: str | None
    feature_scores: dict[str, float] = field(default_factory=dict)
    matched_features: list[str] = field(default_factory=list)


ROLE_TECHNOLOGIES: dict[str, dict[str, set[str]]] = {
    "backend": {
        "languages": {
            "python", "go", "golang", "java", "rust", "c#", "csharp", "c++", "cpp",
            "ruby", "kotlin", "scala", "elixir", "php", "sql",
        },
        "frameworks": {
            "fastapi", "django", "flask", "spring", "springboot", "express", "nestjs",
            "gin", "fiber", "actix", "axum", "rocket", "rails", "aspnet", "laravel",
            "celery", "airflow", "gunicorn", "uvicorn", "koa", "tornado",
        },
        "topics": {
            "api", "backend", "rest", "graphql", "grpc", "microservices", "database",
            "postgres", "postgresql", "mysql", "redis", "mongodb", "kafka", "rabbitmq",
            "distributed", "asyncio", "concurrency", "orm", "sqlalchemy", "prisma",
            "server", "auth", "oauth", "jwt",
        },
    },
    "frontend": {
        "languages": {
            "typescript", "javascript", "html", "css", "scss", "sass",
        },
        "frameworks": {
            "react", "vue", "angular", "svelte", "nextjs", "next.js", "nuxt", "gatsby",
            "tailwind", "bootstrap", "redux", "zustand", "mobx", "vite", "webpack",
        },
        "topics": {
            "frontend", "ui", "ux", "web", "spa", "css", "html", "dom", "components",
            "responsive", "accessibility", "a11y", "state-management", "client",
        },
    },
    "fullstack": {
        "languages": {
            "typescript", "javascript", "python", "go", "java", "rust", "c#", "ruby",
        },
        "frameworks": {
            "nextjs", "next.js", "react", "vue", "svelte", "fastapi", "django", "express",
            "nestjs", "rails", "spring", "nuxt",
        },
        "topics": {
            "fullstack", "web", "api", "frontend", "backend", "full-stack", "spa", "app",
        },
    },
    "data": {
        "languages": {
            "python", "r", "julia", "sql", "scala",
        },
        "frameworks": {
            "pytorch", "tensorflow", "keras", "pandas", "numpy", "scipy", "scikit-learn",
            "sklearn", "spark", "pyspark", "polars", "dbt", "airflow", "huggingface",
            "transformers", "langchain", "llama-index", "xgboost", "lightgbm",
        },
        "topics": {
            "data", "machine-learning", "deep-learning", "ai", "ml", "nlp", "llm", "cv",
            "computer-vision", "data-science", "analytics", "etl", "data-engineering",
            "statistics", "jupyter", "notebook", "pipeline",
        },
    },
    "devops": {
        "languages": {
            "go", "python", "shell", "bash", "hcl", "dockerfile",
        },
        "frameworks": {
            "docker", "kubernetes", "k8s", "terraform", "ansible", "helm", "prometheus",
            "grafana", "argo", "argocd", "istio",
        },
        "topics": {
            "devops", "infra", "infrastructure", "ci-cd", "ci", "cd", "cloud", "aws",
            "gcp", "azure", "observability", "monitoring", "gitops", "iac", "security",
        },
    },
    "mobile": {
        "languages": {
            "swift", "kotlin", "dart", "java", "objective-c",
        },
        "frameworks": {
            "flutter", "react-native", "swiftui", "uikit", "jetpack-compose", "android-sdk",
        },
        "topics": {
            "mobile", "ios", "android", "app", "cross-platform",
        },
    },
    "embedded": {
        "languages": {
            "c", "c++", "rust", "assembly", "zig",
        },
        "frameworks": {
            "freertos", "zephyr", "esp-idf", "arduino", "mbed",
        },
        "topics": {
            "embedded", "firmware", "iot", "microcontroller", "rtos", "hardware", "stm32",
        },
    },
}


def normalize_words(text: str) -> set[str]:
    """Tokenizes text into lowercase alphanumeric words."""
    if not text:
        return set()
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.\s]', ' ', text)
    tokens = {t.lower() for t in re.split(r'[\s_\-\.]+', cleaned) if len(t) >= 2}
    return tokens


def compute_title_similarity(
    repo_name: str,
    repo_desc: str | None,
    project_titles: Sequence[str],
) -> tuple[float, str | None]:
    """Calculates name/description similarity against resume project titles."""
    if not project_titles:
        return 0.0, None

    clean_repo_name = re.sub(r'[^a-z0-9]', '', repo_name.lower())
    repo_tokens = normalize_words(repo_name)
    if repo_desc:
        repo_tokens |= normalize_words(repo_desc)

    best_similarity = 0.0
    best_title: str | None = None

    for title in project_titles:
        clean_title = re.sub(r'[^a-z0-9]', '', title.lower())
        if clean_repo_name and clean_title:
            if clean_repo_name in clean_title or clean_title in clean_repo_name:
                return 1.0, title

        title_tokens = normalize_words(title)
        if not title_tokens:
            continue
        overlap = len(repo_tokens & title_tokens)
        union = len(repo_tokens | title_tokens)
        similarity = overlap / union if union > 0 else 0.0

        if similarity > best_similarity:
            best_similarity = similarity
            best_title = title

    return best_similarity, best_title


def score_repository_candidate(
    repo_data: Mapping[str, Any],
    *,
    target_role: CanonicalRole | str | None = None,
    explicit_urls: set[str] | None = None,
    resume_urls: set[str] | None = None,
    project_titles: Sequence[str] = (),
    candidate_skills: Sequence[str] = (),
    jd_keywords: Sequence[str] = (),
    deployment_urls: Sequence[str] = (),
    portfolio_urls: Sequence[str] = (),
) -> tuple[float, list[str], dict[str, float]]:
    """Evaluates the 10 priority features and computes composite score and reasons."""
    scores: dict[str, float] = {}
    reasons: list[str] = []

    url = repo_data.get("url", "").rstrip("/")
    url_lower = url.lower()
    name = repo_data.get("name", "")
    description = repo_data.get("description") or ""
    language = (repo_data.get("language") or "").lower()
    topics = {t.lower() for t in (repo_data.get("topics") or [])}
    is_fork = bool(repo_data.get("fork"))
    is_archived = bool(repo_data.get("archived"))
    size_kb = repo_data.get("size_kb") or repo_data.get("size") or 0
    stars = repo_data.get("stars") or repo_data.get("stargazers_count") or 0
    pushed_at = repo_data.get("pushed_at")

    # 1. Explicitly supplied repository
    is_explicit = bool(explicit_urls and url_lower in {u.lower().rstrip("/") for u in explicit_urls})
    if is_explicit:
        scores["explicitly_supplied"] = 100.0
        reasons.append("explicitly supplied repository link")

    # 2. Resume-linked repository
    is_resume_linked = bool(
        resume_urls
        and any(
            url_lower == u.lower().rstrip("/")
            or (name.lower() and name.lower() in u.lower())
            for u in resume_urls
        )
    )
    if is_resume_linked and not is_explicit:
        scores["resume_linked"] = 50.0
        reasons.append("linked in resume project citations")

    # 3. Project-title similarity
    title_sim, best_title = compute_title_similarity(name, description, project_titles)
    if title_sim >= 0.25:
        sim_score = round(title_sim * 30.0, 1)
        scores["project_title_similarity"] = sim_score
        reasons.append(f"matches resume project '{best_title}' (similarity {title_sim:.2f})")

    # 4. Technology relevance (claimed skills + JD keywords)
    all_tech_targets = {s.lower() for s in candidate_skills} | {k.lower() for k in jd_keywords}
    repo_words = normalize_words(f"{name} {description} {language} {' '.join(topics)}")
    matched_techs = all_tech_targets & repo_words
    if matched_techs:
        tech_score = min(25.0, len(matched_techs) * 6.0)
        scores["technology_relevance"] = tech_score
        reasons.append(f"matches claimed/required technologies ({', '.join(sorted(matched_techs)[:4])})")

    # 5. Role relevance
    role_key = (target_role.value if isinstance(target_role, CanonicalRole) else str(target_role or "")).lower()
    role_spec = ROLE_TECHNOLOGIES.get(role_key, ROLE_TECHNOLOGIES.get("backend", {}))
    role_langs = role_spec.get("languages", set())
    role_frameworks = role_spec.get("frameworks", set())
    role_topics = role_spec.get("topics", set())

    role_score = 0.0
    matched_role_indicators = []
    if language in role_langs:
        role_score += 15.0
        matched_role_indicators.append(language)
    matched_rf = (role_frameworks | role_topics) & repo_words
    if matched_rf:
        role_score += min(10.0, len(matched_rf) * 4.0)
        matched_role_indicators.extend(sorted(matched_rf)[:3])

    if role_score > 0:
        scores["role_relevance"] = role_score
        reasons.append(f"aligned with {role_key.upper()} role ({', '.join(matched_role_indicators[:4])})")

    # 6. Deployment linkage
    is_deploy_linked = False
    linked_deploy_host = None
    for d_url in deployment_urls:
        parsed_d = urlsplit(d_url)
        host = (parsed_d.netloc or d_url).lower()
        if (
            name.lower() in host
            or (parsed_d.path and name.lower() in parsed_d.path.lower())
            or (description and host in description.lower())
            or any(t in host for t in topics)
        ):
            is_deploy_linked = True
            linked_deploy_host = host
            break
    if is_deploy_linked:
        scores["deployment_linkage"] = 20.0
        reasons.append(f"linked to candidate deployment ({linked_deploy_host})")

    # 7. Portfolio linkage
    is_portfolio_linked = False
    for p_url in portfolio_urls:
        p_host = urlsplit(p_url).netloc.lower()
        if (name.lower() in p_host) or (description and p_host in description.lower()):
            is_portfolio_linked = True
            break
    if is_portfolio_linked:
        scores["portfolio_linkage"] = 15.0
        reasons.append("linked to portfolio")

    # 8. Non-fork vs Fork/Archived
    if not is_fork and not is_archived:
        scores["non_fork"] = 15.0
        reasons.append("original candidate repository (non-fork)")
    else:
        if is_fork:
            scores["fork_penalty"] = -40.0 if not is_explicit else 0.0
        if is_archived:
            scores["archived_penalty"] = -30.0 if not is_explicit else 0.0

    # 9. Engineering depth
    depth_score = 0.0
    if size_kb >= 500:
        depth_score += 15.0
    elif size_kb >= 50:
        depth_score += 10.0
    elif size_kb >= 10:
        depth_score += 5.0

    if stars >= 2:
        depth_score += 5.0
    if len(topics) >= 2:
        depth_score += 5.0

    if depth_score > 0:
        scores["engineering_depth"] = depth_score
        reasons.append(f"engineering depth ({size_kb} KB{f', {stars} stars' if stars else ''})")

    # 10. Recent meaningful activity
    if pushed_at:
        try:
            ts = pushed_at if isinstance(pushed_at, datetime) else datetime.fromisoformat(str(pushed_at).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = max(0, (now - ts).days)
            if days <= 180:
                scores["recent_activity"] = 10.0
                reasons.append(f"active within last {days} days")
            elif days <= 365:
                scores["recent_activity"] = 7.0
                reasons.append(f"active within last {days} days")
            elif days <= 730:
                scores["recent_activity"] = 4.0
            else:
                scores["recent_activity"] = 1.0
        except Exception:
            pass

    total = sum(scores.values())
    return total, reasons, scores


def prioritize_repositories(
    candidate_repos: Sequence[Mapping[str, Any]],
    *,
    max_repositories: int = 6,
    target_role: CanonicalRole | str | None = None,
    explicit_urls: set[str] | None = None,
    resume_urls: set[str] | None = None,
    project_titles: Sequence[str] = (),
    candidate_skills: Sequence[str] = (),
    jd_keywords: Sequence[str] = (),
    deployment_urls: Sequence[str] = (),
    portfolio_urls: Sequence[str] = (),
) -> list[RepositoryPriorityResult]:
    """Prioritizes and partitions repositories into selected and deferred/inventory sets (Fix 23).

    Sorting:
    1. Highest composite priority score first.
    2. Tie-break by recency (pushed_at descending).
    3. Tie-break by name alphabetically ascending.
    """
    scored_items: list[tuple[float, str, str, Mapping[str, Any], list[str], dict[str, float]]] = []

    for item in candidate_repos:
        score, reasons, feature_scores = score_repository_candidate(
            item,
            target_role=target_role,
            explicit_urls=explicit_urls,
            resume_urls=resume_urls,
            project_titles=project_titles,
            candidate_skills=candidate_skills,
            jd_keywords=jd_keywords,
            deployment_urls=deployment_urls,
            portfolio_urls=portfolio_urls,
        )
        pushed_at_str = str(item.get("pushed_at") or "")
        name = str(item.get("name") or "")
        scored_items.append((score, pushed_at_str, name, item, reasons, feature_scores))

    # Sort: score descending, pushed_at descending, name ascending
    scored_items.sort(key=lambda t: (-t[0], t[1] == "", -_timestamp_sort_key(t[1]), t[2].lower()))

    results: list[RepositoryPriorityResult] = []
    selected_count = 0

    for score, _, name, item, reasons, feature_scores in scored_items:
        url = item.get("url", "")
        is_fork = bool(item.get("fork"))
        is_archived = bool(item.get("archived"))

        if selected_count < max_repositories and not (is_fork and not feature_scores.get("explicitly_supplied")):
            selected_count += 1
            is_selected = True
            inspection_status = "observed"
            sel_reason = "; ".join(reasons) if reasons else "Selected non-fork repository within scan budget"
            def_reason = None
        else:
            is_selected = False
            sel_reason = None
            if is_fork:
                inspection_status = "inventory_only"
                def_reason = "Forked third-party repository retained in inventory only"
            elif is_archived:
                inspection_status = "inventory_only"
                def_reason = "Archived repository retained in inventory only"
            else:
                inspection_status = "deferred"
                def_reason = f"Deferred due to scan budget limit; lower role/technology relevance than selected repositories (score: {score:.1f})"

        results.append(
            RepositoryPriorityResult(
                url=url,
                name=name,
                priority_score=score,
                is_selected=is_selected,
                inspection_status=inspection_status,
                selection_reason=sel_reason,
                deferral_reason=def_reason,
                feature_scores=feature_scores,
                matched_features=reasons,
            )
        )

    return results


def _timestamp_sort_key(pushed_at: str) -> float:
    if not pushed_at:
        return 0.0
    try:
        dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0
