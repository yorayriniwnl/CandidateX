"""Stable identities and semantic versions for analyzer signal rules."""

SIGNAL_RULE_VERSIONS: dict[str, str] = {
    rule_id: "1.0.0"
    for rule_id in (
        "candidatex.code.python.dependency_import",
        "candidatex.code.python.async_function",
        "candidatex.code.python.api_route",
        "candidatex.code.python.dependency_injection",
        "candidatex.code.python.auth_guard",
        "candidatex.code.python.pydantic_schema",
        "candidatex.code.python.ml_class",
        "candidatex.code.python.architecture_class",
        "candidatex.code.python.try_except",
        "candidatex.code.typescript.api_route",
        "candidatex.code.typescript.async_handler",
        "candidatex.code.typescript.zod_schema",
        "candidatex.code.typescript.try_catch",
        "candidatex.code.go.http_route",
        "candidatex.code.go.goroutine_channel",
        "candidatex.code.go.error_guard",
        "candidatex.code.java.spring_endpoint",
        "candidatex.code.java.spring_component",
        "candidatex.code.cpp.concurrency_construct",
        "candidatex.code.cpp.class_declaration",
        "candidatex.dependencies.manifest_declaration",
        "candidatex.database.sql_table",
        "candidatex.database.sql_index",
        "candidatex.database.sql_foreign_key",
        "candidatex.database.sql_advanced_feature",
        "candidatex.database.alembic_migration",
        "candidatex.database.prisma_schema",
        "candidatex.deployment.live_service",
        "candidatex.deployment.security_headers",
        "candidatex.deployment.responsive_dom",
        "candidatex.deployment.tls_certificate",
        "candidatex.docs.readme_setup",
        "candidatex.docs.readme_architecture_diagram",
        "candidatex.docs.adr_structure",
        "candidatex.docs.openapi_spec",
        "candidatex.docs.repository_layer_boundaries",
        "candidatex.infra.dockerfile",
        "candidatex.infra.docker_compose",
        "candidatex.infra.ci_workflow",
        "candidatex.infra.kubernetes_manifest",
        "candidatex.infra.terraform_hcl",
        "candidatex.testing.python_suite",
        "candidatex.testing.python_fixtures",
        "candidatex.testing.python_parameterized",
        "candidatex.testing.python_mocks",
        "candidatex.testing.python_property_based",
        "candidatex.testing.python_regex_fallback",
        "candidatex.testing.javascript_suite",
        "candidatex.testing.javascript_lifecycle",
        "candidatex.testing.javascript_mocks",
        "candidatex.testing.javascript_supertest",
        "candidatex.testing.go_suite",
    )
}


def signal_rule_fields(rule_id: str) -> dict[str, str]:
    """Return the current rule identity fields for an analyzer emission."""
    try:
        version = SIGNAL_RULE_VERSIONS[rule_id]
    except KeyError as exc:
        raise ValueError(f"Unknown signal rule: {rule_id}") from exc
    return {"signal_rule_id": rule_id, "signal_rule_version": version}
