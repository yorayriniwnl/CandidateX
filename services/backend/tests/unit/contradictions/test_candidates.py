"""Contradictions require a pinned, complete, unambiguous observation."""

import pytest

from cci.contradictions.candidates import (
    DeploymentProjectIdentity,
    evaluate_deployment_project_mismatch,
    evaluate_repository_candidates,
)
from cci.contradictions.expectations import parse_observable_claim
from cci.live.scan_inventory import InventoryCounter


REPOSITORY = "https://github.com/acme/api"
SHA = "a" * 40
COBERTURA_70 = b'<coverage line-rate="0.70" branch-rate="0.80"/>'


def claim(text):
    matches = parse_observable_claim(text, repository_scope="acme/api")
    assert len(matches) == 1
    return matches[0]


def inventory(files, *, skipped=(), inventory_complete=True):
    counter = InventoryCounter()
    for path in files:
        categories = counter.add(path)
        if path in skipped:
            counter.skip(categories, "file_cap")
        else:
            counter.inspect(categories)
    counter.inventory_complete = inventory_complete
    return counter.receipt()


def evaluate_one(expectation, artifacts, *, skipped=(), inventory_complete=True):
    return evaluate_repository_candidates(
        [expectation], REPOSITORY, SHA, artifacts,
        inventory(artifacts.keys() | set(skipped), skipped=skipped,
                  inventory_complete=inventory_complete),
    )


def test_coverage_report_below_explicit_claim_emits_qualified_negative():
    expectation = claim("at least 95% line coverage")
    result = evaluate_one(expectation, {"coverage.xml": COBERTURA_70})
    assert len(result) == 1
    evidence = result[0]
    assert evidence.is_positive_support is False
    assert evidence.technical_signal_strength == 70.0
    assert (evidence.signal_rule_id, evidence.signal_rule_version) == (
        "candidatex.contradiction.coverage_below_claim", "1.0.0")
    details = evidence.negative_evidence_details
    assert details.claim_reference == expectation.claim_reference
    assert details.scan_scope.repository_scope == "acme/api"
    assert details.scan_scope.pinned_revision == SHA
    assert details.scan_scope.artifact_paths == ["coverage.xml"]
    assert (details.required_scan_completeness, details.observed_scan_completeness) == (1.0, 1.0)
    assert "70" in details.actual_observation


def test_ambiguous_or_incomplete_report_emits_no_negative():
    expectation = claim("at least 95% line coverage")
    reports = {"lcov.info": b"SF:a.py\nLF:1\nLH:0\nend_of_record\n",
               "coverage/lcov.info": b"SF:a.py\nLF:1\nLH:0\nend_of_record\n"}
    assert evaluate_one(expectation, reports) == []
    assert evaluate_one(expectation, {"coverage.xml": COBERTURA_70},
                        skipped={"coverage/lcov.info"}) == []


def test_repository_scope_and_revision_are_required():
    expectation = claim("at least 95% line coverage")
    receipt = inventory(["coverage.xml"])
    assert evaluate_repository_candidates([expectation], "https://github.com/acme/other", SHA,
                                          {"coverage.xml": COBERTURA_70}, receipt) == []
    assert evaluate_repository_candidates([expectation], REPOSITORY, "", {
        "coverage.xml": COBERTURA_70}, receipt) == []


def test_unsafe_repository_artifact_path_cannot_support_absence():
    assert evaluate_one(claim("Built with FastAPI"), {"../app.py": b"pass\n"}) == []


def test_matching_coverage_and_missing_metric_emit_no_candidate():
    expectation = claim("at least 95% line coverage")
    assert evaluate_one(expectation, {"coverage.xml": b'<coverage line-rate="0.95"/>'}) == []
    assert evaluate_one(expectation, {"coverage.xml": b'<coverage branch-rate="0.70"/>'}) == []
    assert evaluate_one(expectation, {}) == []


def test_strict_coverage_comparator_violates_at_equality():
    assert len(evaluate_one(claim("> 70% line coverage"),
                            {"coverage.xml": COBERTURA_70})) == 1
    assert evaluate_one(claim("at least 70% line coverage"),
                        {"coverage.xml": COBERTURA_70}) == []


@pytest.mark.parametrize("content", [
    b'<coverage line-rate="NaN"/>',
    b'<coverage line-rate="1.2"/>',
    b'<!DOCTYPE coverage [<!ENTITY x SYSTEM "file:///etc/passwd">]><coverage line-rate="0.7"/>',
    b'<coverage',
])
def test_malformed_or_unsafe_coverage_is_unknown(content):
    assert evaluate_one(claim("at least 95% line coverage"), {"coverage.xml": content}) == []


def test_valid_report_with_malformed_sibling_is_unknown():
    assert evaluate_one(claim("at least 95% line coverage"), {
        "coverage.xml": COBERTURA_70, "lcov.info": b"garbage",
    }) == []


def test_lcov_separates_line_and_branch_coverage_and_accepts_string_branch_ids():
    report = (b"SF:src/app.py\nDA:1,1\nLF:10\nLH:7\n"
              b"BRDA:1,1,branch-1,1\nBRF:10\nBRH:9\nend_of_record\n")
    result = evaluate_one(claim("at least 95% line coverage"), {"coverage/lcov.info": report})
    assert len(result) == 1
    assert "70" in result[0].negative_evidence_details.actual_observation
    assert evaluate_one(claim("at least 80% branch coverage"),
                        {"coverage/lcov.info": report}) == []


def test_empty_lcov_denominator_and_generic_coverage_claim_are_unknown():
    report = b"SF:a.py\nLF:0\nLH:0\nend_of_record\n"
    assert evaluate_one(claim("at least 95% line coverage"), {"lcov.info": report}) == []
    assert evaluate_one(claim("at least 95% coverage"), {"coverage.xml": COBERTURA_70}) == []


def test_generic_coverage_claim_uses_report_with_one_valid_metric():
    result = evaluate_one(claim("at least 95% coverage"), {
        "coverage.xml": b'<coverage line-rate="0.70"/>',
    })
    assert len(result) == 1
    assert "line_coverage" in result[0].negative_evidence_details.actual_observation


def test_framework_absence_requires_full_nonempty_registered_scope():
    expectation = claim("Built with FastAPI")
    result = evaluate_one(expectation, {"src/app.py": b"print('hello')\n"})
    assert len(result) == 1
    evidence = result[0]
    assert evidence.technical_signal_strength == 55.0
    assert evidence.signal_rule_id == "candidatex.contradiction.framework_usage_absent"
    assert evidence.negative_evidence_details.scan_scope.scope_kind == "repository"
    assert "1 eligible" in evidence.negative_evidence_details.actual_observation
    assert ".py" in evidence.negative_evidence_details.actual_observation
    assert "requirements.txt" in evidence.negative_evidence_details.actual_observation
    assert "skipped=0" in evidence.negative_evidence_details.actual_observation
    assert evaluate_one(expectation, {}) == []
    assert evaluate_one(expectation, {"src/app.py": b"pass\n"},
                        skipped={"other.py"}) == []


def test_framework_import_suppresses_absence_but_manifest_only_does_not():
    expectation = claim("Built with FastAPI")
    assert evaluate_one(expectation, {"src/app.py": b"from fastapi import FastAPI\n"}) == []
    result = evaluate_one(expectation, {
        "src/app.py": b"print('hello')\n",
        "requirements.txt": b"fastapi==0.115\n",
    })
    assert len(result) == 1
    assert "manifest" in result[0].negative_evidence_details.actual_observation
    assert "fastapi" in result[0].negative_evidence_details.actual_observation


@pytest.mark.parametrize("technology,path,source", [
    ("django", "app.py", b"import django.http\n"),
    ("flask", "app.py", b"from flask import Flask\n"),
    ("express", "app.js", b"const express = require('express');\n"),
    ("nestjs", "app.ts", b"import { Module } from '@nestjs/common';\n"),
    ("angular", "app.ts", b"import { Component } from '@angular/core';\n"),
    ("gin", "app.go", b'package main\nimport (\n "fmt"\n "github.com/gin-gonic/gin"\n)\n'),
    ("spring-boot", "App.java", b"import org.springframework.boot.SpringApplication;\n"),
])
def test_registered_import_suppresses_framework_absence(technology, path, source):
    assert evaluate_one(claim(f"Built with {technology}"), {path: source}) == []


@pytest.mark.parametrize("technology,manifest,dependency", [
    ("express", "package.json", b'{"dependencies":{"express":"^4"}}'),
    ("gin", "go.mod", b'module example.com/api\nrequire github.com/gin-gonic/gin v1.10.0\n'),
    ("spring-boot", "pom.xml", b'<project><dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency></dependencies></project>'),
])
def test_exact_manifest_dependency_is_context_not_source_use(technology, manifest, dependency):
    result = evaluate_one(claim(f"Built with {technology}"), {manifest: dependency})
    assert len(result) == 1
    assert "manifest dependency present=true" in result[0].negative_evidence_details.actual_observation


def test_other_inspected_manifest_is_in_complete_framework_scope():
    result = evaluate_one(claim("Built with Express"), {
        "app.js": b"console.log('plain');\n",
        "package.json": b'{"dependencies":{}}',
        "package-lock.json": b'{"lockfileVersion":3}',
    })
    assert len(result) == 1
    assert "3 eligible" in result[0].negative_evidence_details.actual_observation


def test_file_in_source_and_manifest_categories_is_counted_in_both():
    result = evaluate_one(claim("Built with FastAPI"), {"setup.py": b"from setuptools import setup\n"})
    assert len(result) == 1
    assert "2 eligible" in result[0].negative_evidence_details.actual_observation


def test_unrelated_manifest_alone_does_not_create_framework_scope():
    assert evaluate_one(claim("Built with Express"), {
        "package-lock.json": b'{"lockfileVersion":3}',
    }) == []


@pytest.mark.parametrize("technology,manifest,content", [
    ("express", "package.json", b"{broken"),
    ("fastapi", "pyproject.toml", b"[project\n"),
    ("spring-boot", "pom.xml", b"<project"),
])
def test_malformed_registered_manifest_suppresses_absence(technology, manifest, content):
    assert evaluate_one(claim(f"Built with {technology}"), {manifest: content}) == []


def test_unsupported_framework_and_incomplete_inventory_are_unknown():
    expectation = claim("Built with FastAPI")
    assert evaluate_one(expectation, {"app.py": b"pass"}, inventory_complete=False) == []
    from dataclasses import replace

    assert evaluate_one(replace(expectation, technology="unknown"), {"app.py": b"pass"}) == []


def test_comment_and_prose_mentions_do_not_count_as_framework_imports():
    expectation = claim("Built with FastAPI")
    result = evaluate_one(expectation, {"app.py": b"# import fastapi\nprint('fastapi')\n"})
    assert len(result) == 1
    js_result = evaluate_one(claim("Built with Express"), {
        "app.js": b"// import express from 'express'\nconsole.log('express');\n"})
    assert len(js_result) == 1


def test_react_jsx_without_explicit_import_is_ambiguous():
    expectation = claim("Built with React")
    assert evaluate_one(expectation, {"src/App.tsx": b"export const App = () => <div>Hello</div>;"}) == []
    assert evaluate_one(expectation, {"src/App.tsx": b"import React from 'react';\n"}) == []


@pytest.mark.parametrize("technology,path,content", [
    ("vue", "src/App.vue", b"<template><div/></template>"),
    ("svelte", "src/App.svelte", b"<h1>Hello</h1>"),
    ("next", "src/app/page.tsx", b"export default function Page() { return null }"),
    ("next", "next.config.js", b"module.exports = {}"),
])
def test_component_and_next_conventions_suppress_absence(technology, path, content):
    assert evaluate_one(claim(f"Built with {technology}"), {path: content}) == []


def test_performance_report_violation_and_time_unit_conversion():
    expectation = claim("latency under 50 ms technology=fastapi statistic=p95 workload=read environment=prod")
    report = (b'{"schema_version":"1.0.0","observations":[{"metric":"latency",'
              b'"value":0.05,"unit":"s",'
              b'"statistic":"p95","workload":"read","environment":"prod"}]}')
    result = evaluate_one(expectation, {"benchmarks/run.json": report})
    assert len(result) == 1
    assert result[0].technical_signal_strength == 70.0
    assert result[0].signal_rule_id == "candidatex.contradiction.performance_claim_mismatch"
    assert "50" in result[0].negative_evidence_details.actual_observation


def test_performance_matching_value_and_context_mismatch_are_unknown():
    expectation = claim("latency at most 50 ms technology=fastapi statistic=p95")
    good = (b'{"schema_version":"1.0.0","observations":[{"metric":"latency",'
            b'"value":50,"unit":"ms",'
            b'"statistic":"p95","workload":"read","environment":"prod"}]}')
    assert evaluate_one(expectation, {"benchmarks/run.json": good}) == []
    wrong_context = good.replace(b'"p95"', b'"average"')
    assert evaluate_one(expectation, {"benchmarks/run.json": wrong_context}) == []
    wrong_unit = good.replace(b'"ms"', b'"req/s"').replace(b'"value":50', b'"value":60')
    assert evaluate_one(expectation, {"benchmarks/run.json": wrong_unit}) == []


def test_performance_strict_boundary_duplicate_and_ambiguous_observations():
    expectation = claim("latency under 50 ms technology=fastapi")
    observation = (b'{"metric":"latency","value":50,"unit":"ms",'
                   b'"statistic":"p95",'
                   b'"workload":"read","environment":"prod"}')
    report = b'{"schema_version":"1.0.0","observations":[' + observation + b']}'
    assert len(evaluate_one(expectation, {"benchmark/run.json": report})) == 1
    duplicate = b'{"schema_version":"1.0.0","observations":[' + observation + b',' + observation + b']}'
    assert evaluate_one(expectation, {"benchmark/run.json": duplicate}) == []
    distinct = observation.replace(b'"p95"', b'"p99"')
    ambiguous = b'{"schema_version":"1.0.0","observations":[' + observation + b',' + distinct + b']}'
    assert evaluate_one(expectation, {"benchmark/run.json": ambiguous}) == []
    assert evaluate_one(expectation, {"benchmark/run.json": report},
                        skipped={"benchmarks/unreadable.json"}) == []
    assert evaluate_one(expectation, {"benchmark/run.json": report,
                                      "benchmarks/malformed.json": b"{bad"}) == []


@pytest.mark.parametrize("report", [
    b'{"schema_version":"1.0.0","schema_version":"1.0.0","observations":[]}',
    b'{"schema_version":"1.0.0","observations":[{"metric":"latency","value":NaN}]}',
    b'{"schema_version":"1.0.0","observations":[]}',
])
def test_invalid_or_empty_benchmark_report_is_unknown(report):
    assert evaluate_one(claim("latency under 50 ms technology=fastapi"),
                        {"benchmarks/run.json": report}) == []


def test_deployment_identity_requires_fresh_verified_structured_result():
    expectation = parse_observable_claim(
        "project=api-v2 https://api.example.com", deployment_url="https://api.example.com")[0]
    unavailable = DeploymentProjectIdentity(status="INACCESSIBLE", deployment_url=expectation.deployment_url)
    assert evaluate_deployment_project_mismatch(expectation, unavailable) is None
    stale = DeploymentProjectIdentity(status="VERIFIED", deployment_url=expectation.deployment_url,
                                      project_identity="other", verifier_identity="platform-api",
                                      verification_revision="check-1", fresh=False, authoritative=True)
    assert evaluate_deployment_project_mismatch(expectation, stale) is None
    verified = DeploymentProjectIdentity(status="VERIFIED", deployment_url=expectation.deployment_url,
                                         project_identity="other", verifier_identity="platform-api",
                                         verification_revision="check-2", fresh=True, authoritative=True)
    result = evaluate_deployment_project_mismatch(expectation, verified)
    assert result is not None
    assert result.technical_signal_strength == 85.0
    assert result.negative_evidence_details.scan_scope.scope_kind == "deployment"
    assert evaluate_deployment_project_mismatch(expectation, DeploymentProjectIdentity(
        status="VERIFIED", deployment_url=expectation.deployment_url,
        project_identity="api-v2", verifier_identity="platform-api",
        verification_revision="check-3", fresh=True, authoritative=True)) is None
    assert evaluate_deployment_project_mismatch(expectation, DeploymentProjectIdentity(
        status="VERIFIED", deployment_url=expectation.deployment_url,
        project_identity="other", verifier_identity="public-link-inspector",
        verification_revision="check-4", fresh=True, authoritative=False)) is None
