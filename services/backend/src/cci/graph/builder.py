"""Build the paper's provenance graph from the same snapshot used for scoring."""
from hashlib import sha256
from uuid import uuid4
from cci.artifacts.identity import compute_canonical_artifact_id
from cci.contradictions.qualification import is_qualified_negative
from cci.domain.contracts import Dossier
from cci.domain.enums import ClaimStatus, GraphNodeType as N, GraphEdgeType as E, SourceFamily
from cci.graph.ceg import CandidateEvidenceGraph, CEGNode, CEGEdge


def build_dossier_graph(dossier: Dossier) -> CandidateEvidenceGraph:
    graph = CandidateEvidenceGraph()

    def node(key, kind, label, **properties):
        existing = graph.get_node(key)
        merged = {**(existing.properties if existing and existing.node_type == kind else {}),
                  "label": label, **properties}
        graph.add_node(CEGNode(key, kind, merged))

    def edge(source, target, kind, **properties):
        graph.add_edge(CEGEdge(f"{source}:{kind.value}:{target}", source, target, kind, properties))

    candidate = str(dossier.candidate_id)
    identity = f"identity_{candidate}"
    run = str(dossier.analysis_run_id)

    def repository_source(repository_url):
        source = "source_" + sha256(repository_url.encode()).hexdigest()[:20]
        node(source, N.SOURCE, repository_url, locator=repository_url, source_kind="repository")
        return source

    node(candidate, N.CANDIDATE, "Synthetic candidate" if dossier.evidence_mode == "synthetic" else "Candidate", candidate_id=candidate)
    node(identity, N.IDENTITY, "Scenario identity" if dossier.evidence_mode == "synthetic" else "Supplied identity", candidate_id=candidate, verification="synthetic" if dossier.evidence_mode == "synthetic" else "not externally verified")
    node(run, N.ANALYSIS_RUN, "Analysis snapshot", role=dossier.role.value, evidence_mode=dossier.evidence_mode,
         scenario=dossier.scenario, role_weights={k.value: v for k, v in dossier.role_weights.items()},
         override_history=dossier.override_history, versions=dossier.versions)
    edge(identity, candidate, E.DERIVED_FROM)
    edge(run, candidate, E.DERIVED_FROM)

    for association in dossier.repository_associations:
        source = repository_source(association.repository_url)
        repo_id = "repo_" + sha256(association.repository_url.encode()).hexdigest()[:20]
        node(repo_id, N.REPOSITORY, association.repository_url, repository_url=association.repository_url)
        edge(source, repo_id, E.CONTAINS)
        edge(candidate, repo_id, E.ASSOCIATED_WITH,
             basis=association.basis, identity_verified=association.identity_verified)
        edge(candidate, source, E.ASSOCIATED_WITH,
             basis=association.basis, identity_verified=association.identity_verified)

    for contribution in dossier.repository_contributions:
        source = repository_source(contribution.repository_url)
        repo_id = "repo_" + sha256(contribution.repository_url.encode()).hexdigest()[:20]
        node(repo_id, N.REPOSITORY, contribution.repository_url, repository_url=contribution.repository_url)
        if contribution.candidate_commit_count > 0:
            edge(candidate, repo_id, E.CONTRIBUTES_TO,
                 basis=contribution.method, weight=contribution.candidate_commit_ratio,
                 candidate_commit_count=contribution.candidate_commit_count,
                 sampled_commit_count=contribution.sampled_commit_count,
                 candidate_commit_shas=contribution.candidate_commit_shas,
                 limitation="Repository contribution does not establish artifact authorship.")
            edge(candidate, source, E.CONTRIBUTES_TO,
                 basis=contribution.method, weight=contribution.candidate_commit_ratio,
                 candidate_commit_count=contribution.candidate_commit_count,
                 sampled_commit_count=contribution.sampled_commit_count,
                 candidate_commit_shas=contribution.candidate_commit_shas,
                 limitation="Repository contribution does not establish artifact authorship.")

    for cap, estimate in dossier.capability_estimates.items():
        key = f"cap_{cap.value}"
        node(key, N.CAPABILITY, cap.value, **estimate.model_dump(mode="json"))
        requirement = f"requirement_{cap.value}"
        node(requirement, N.ROLE_REQUIREMENT, f"{dossier.role.value}: {cap.value}",
             weight=dossier.role_weights.get(cap, 0),
             jd_excerpts=[r.source_text for r in dossier.role_requirements if cap in r.capability_mappings])
        edge(requirement, run, E.DERIVED_FROM)
        if estimate.is_observed:
            # A capability observation contributes to a requirement; it does not certify satisfaction.
            edge(key, requirement, E.CONTRIBUTES_TO, status="observed; interviewer verification required")

    for record in dossier.evidence_records:
        ev = str(record.evidence_id)
        source = "source_" + sha256(record.source_locator.encode()).hexdigest()[:20]
        art_path = record.provenance.get("artifact_path", record.source_locator)
        content_hash = (
            record.provenance.get("content_sha256")
            or record.provenance.get("artifact_sha256")
            or record.provenance.get("content_hash")
            or ""
        )
        artifact = compute_canonical_artifact_id(
            repo_url=record.source_locator,
            immutable_revision=record.immutable_revision,
            artifact_path=art_path,
            content_hash=content_hash,
        )
        node(
            source,
            N.SOURCE,
            record.source_family.value,
            locator=record.source_locator,
            synthetic=dossier.evidence_mode == "synthetic",
        )
        node(
            artifact,
            N.ARTIFACT,
            art_path,
            revision=record.immutable_revision,
            artifact_path=art_path,
            content_hash=content_hash,
            raw_support_text=record.provenance.get("raw_support_text", ""),
            extractor_version=record.provenance.get("extractor_version"),
        )
        node(
            ev,
            N.EVIDENCE,
            f"{record.source_family.value}: {record.target_capability.value}",
            **record.model_dump(mode="json"),
            score=record.technical_signal_strength,
        )
        edge(artifact, source, E.CONTRIBUTES_TO)

        if record.source_family == SourceFamily.DEPLOYMENT:
            deploy_id = "deploy_" + sha256(record.source_locator.encode()).hexdigest()[:20]
            node(
                deploy_id,
                N.DEPLOYMENT,
                record.source_locator,
                url=record.source_locator,
                status="observed",
                linked_repository=record.provenance.get("linked_repository"),
                supported_signals=record.provenance.get("supported_signals", []),
            )
            edge(deploy_id, source, E.DISCOVERED_FROM)
            edge(candidate, deploy_id, E.ATTRIBUTED_TO,
                 weight=record.confidence_factors.ownership_score,
                 basis="candidate_declared_deployment")
            edge(artifact, deploy_id, E.OBSERVED_IN)
            linked_repo = record.provenance.get("linked_repository")
            if linked_repo:
                repo_id = "repo_" + sha256(linked_repo.encode()).hexdigest()[:20]
                if repo_id not in graph.nodes:
                    node(repo_id, N.REPOSITORY, linked_repo, repository_url=linked_repo)
                edge(repo_id, deploy_id, E.DEPLOYED_AS, basis="verified_runtime_linkage")

        attribution = record.artifact_attribution
        if attribution and attribution.candidate_commit_count > 0:
            edge(candidate, artifact, E.ATTRIBUTED_TO,
                 basis=attribution.basis, weight=attribution.ownership_score,
                 attribution_state=attribution.state.value,
                 attribution_confidence=attribution.attribution_confidence,
                 candidate_commit_count=attribution.candidate_commit_count,
                 candidate_commit_shas=attribution.candidate_commit_shas,
                 limitation="A GitHub account match is not human identity verification or line-level authorship.")
            edge(candidate, artifact, E.CONTRIBUTES_TO,
                 basis=attribution.basis, weight=attribution.ownership_score,
                 attribution_state=attribution.state.value,
                 attribution_confidence=attribution.attribution_confidence,
                 candidate_commit_count=attribution.candidate_commit_count,
                 candidate_commit_shas=attribution.candidate_commit_shas,
                 limitation="A GitHub account match is not human identity verification or line-level authorship.")
        edge(ev, artifact, E.DERIVED_FROM)
        edge(ev, run, E.CONTRIBUTES_TO)
        cap_node = f"cap_{record.target_capability.value}"
        if cap_node in graph.nodes:
            if record.is_positive_support:
                edge(
                    ev,
                    cap_node,
                    E.SUPPORTS_CAPABILITY,
                    weight=record.confidence,
                )
            elif is_qualified_negative(record):
                edge(
                    ev,
                    cap_node,
                    E.CONTRADICTS,
                    weight=record.confidence,
                )

    for question in dossier.interview_questions:
        key = str(question.question_id)
        node(key, N.DOSSIER_ITEM, question.question_text, rationale=question.rationale)
        edge(key, run, E.DERIVED_FROM)
        for evidence_id in question.grounding_evidence_ids:
            if str(evidence_id) in graph.nodes:
                edge(key, str(evidence_id), E.GENERATED_QUESTION_FROM)
        if not question.grounding_evidence_ids:
            edge(key, f"cap_{question.target_capability.value}", E.GENERATED_QUESTION_FROM, reason="missing evidence")

    for claim_data in dossier.claims_corroboration:
        cid_str = (
            str(claim_data.get("claim_id"))
            if isinstance(claim_data, dict)
            else str(getattr(claim_data, "claim_id", uuid4()))
        )
        key = f"claim_{cid_str}"
        text = (
            claim_data.get("original_text") or claim_data.get("claim_text", "")
            if isinstance(claim_data, dict)
            else getattr(claim_data, "original_text", "") or getattr(claim_data, "claim_text", "")
        )
        claim_type = (
            claim_data.get("claim_type")
            if isinstance(claim_data, dict)
            else getattr(claim_data, "claim_type", "claim")
        )
        status_val = (
            claim_data.get("status")
            if isinstance(claim_data, dict)
            else getattr(claim_data, "status", "SELF_REPORTED")
        )
        if hasattr(status_val, "value"):
            status_val = status_val.value
        props = claim_data if isinstance(claim_data, dict) else (
            claim_data.model_dump(mode="json") if hasattr(claim_data, "model_dump") else claim_data.to_dict()
        )
        node(key, N.CLAIM, text, **props)
        edge(key, run, E.DERIVED_FROM)
        edge(candidate, key, E.DECLARES)

        # Specialized ontology nodes for claim subjects
        claim_type_str = str(claim_type).lower() if claim_type else ""
        norm_subj = props.get("normalized_subject") or text
        if claim_type_str == "skill":
            skill_id = f"skill_{sha256(norm_subj.encode()).hexdigest()[:16]}"
            node(skill_id, N.SKILL, norm_subj, skill_name=norm_subj)
            edge(key, skill_id, E.REFERENCES)
        elif claim_type_str == "project":
            proj_id = f"proj_{sha256(norm_subj.encode()).hexdigest()[:16]}"
            node(proj_id, N.PROJECT, norm_subj, project_name=norm_subj)
            edge(key, proj_id, E.REFERENCES)
        elif claim_type_str in ("education", "degree", "academic"):
            acad_id = f"acad_{cid_str}"
            node(acad_id, N.ACADEMIC_RECORD, norm_subj, **props)
            edge(key, acad_id, E.REFERENCES)
        elif claim_type_str in ("experience", "employment"):
            exp_id = f"exp_{cid_str}"
            node(exp_id, N.EXPERIENCE_RECORD, norm_subj, **props)
            edge(key, exp_id, E.REFERENCES)

        target_cap = (
            claim_data.get("target_capability")
            if isinstance(claim_data, dict)
            else getattr(claim_data, "target_capability", None)
        )
        if target_cap:
            cap_str = target_cap.value if hasattr(target_cap, "value") else str(target_cap)
            cap_node = f"cap_{cap_str}"
            if cap_node in graph.nodes:
                edge(key, cap_node, E.CONTRIBUTES_TO)

        grounding_ids = (
            claim_data.get("grounding_evidence_ids", [])
            if isinstance(claim_data, dict)
            else getattr(claim_data, "grounding_evidence_ids", [])
        )
        for ev_id in grounding_ids:
            ev_str = str(ev_id)
            if ev_str in graph.nodes:
                if str(status_val).lower() == "contradicted" or status_val == ClaimStatus.CONTRADICTED:
                    edge(ev_str, key, E.CONTRADICTS)
                else:
                    edge(ev_str, key, E.CORROBORATES)
    return graph
