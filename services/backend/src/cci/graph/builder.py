"""Build the paper's provenance graph from the same snapshot used for scoring."""
from hashlib import sha256
from cci.domain.contracts import Dossier
from cci.domain.enums import GraphNodeType as N, GraphEdgeType as E
from cci.graph.ceg import CandidateEvidenceGraph, CEGNode, CEGEdge


def build_dossier_graph(dossier: Dossier) -> CandidateEvidenceGraph:
    graph = CandidateEvidenceGraph()

    def node(key, kind, label, **properties):
        graph.add_node(CEGNode(key, kind, {"label": label, **properties}))

    def edge(source, target, kind, **properties):
        graph.add_edge(CEGEdge(f"{source}:{kind.value}:{target}", source, target, kind, properties))

    candidate = str(dossier.candidate_id)
    identity = f"identity_{candidate}"
    run = str(dossier.analysis_run_id)
    node(candidate, N.CANDIDATE, "Synthetic candidate" if dossier.evidence_mode == "synthetic" else "Candidate", candidate_id=candidate)
    node(identity, N.IDENTITY, "Scenario identity" if dossier.evidence_mode == "synthetic" else "Supplied identity", candidate_id=candidate, verification="synthetic" if dossier.evidence_mode == "synthetic" else "not externally verified")
    node(run, N.ANALYSIS_RUN, "Analysis snapshot", role=dossier.role.value, evidence_mode=dossier.evidence_mode,
         scenario=dossier.scenario, role_weights={k.value: v for k, v in dossier.role_weights.items()},
         override_history=dossier.override_history, versions=dossier.versions)
    edge(identity, candidate, E.DERIVED_FROM)
    edge(run, candidate, E.DERIVED_FROM)
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
        artifact = "artifact_" + record.fingerprint
        node(source, N.SOURCE, record.source_family.value, locator=record.source_locator, synthetic=dossier.evidence_mode == "synthetic")
        node(artifact, N.ARTIFACT, record.provenance.get("artifact_path", record.source_locator),
             revision=record.immutable_revision, fingerprint=record.fingerprint,
             raw_support_text=record.provenance.get("raw_support_text", ""), extractor_version=record.provenance.get("extractor_version"))
        node(ev, N.EVIDENCE, f"{record.source_family.value}: {record.target_capability.value}",
             **record.model_dump(mode="json"), score=record.support_score)
        edge(artifact, source, E.CONTRIBUTES_TO)
        edge(artifact, identity, E.AUTHORED_BY, weight=record.confidence_factors.ownership_score,
             attribution="simulated" if dossier.evidence_mode == "synthetic" else "supplied estimate")
        edge(ev, artifact, E.DERIVED_FROM)
        edge(ev, run, E.CONTRIBUTES_TO)
        edge(ev, f"cap_{record.target_capability.value}", E.SUPPORTS_CAPABILITY if record.is_positive_support else E.CONTRADICTS, weight=record.confidence)
    for question in dossier.interview_questions:
        key = str(question.question_id)
        node(key, N.DOSSIER_ITEM, question.question_text, rationale=question.rationale)
        edge(key, run, E.DERIVED_FROM)
        for evidence_id in question.grounding_evidence_ids:
            if str(evidence_id) in graph.nodes:
                edge(key, str(evidence_id), E.GENERATED_QUESTION_FROM)
        if not question.grounding_evidence_ids:
            edge(key, f"cap_{question.target_capability.value}", E.GENERATED_QUESTION_FROM, reason="missing evidence")
    return graph
