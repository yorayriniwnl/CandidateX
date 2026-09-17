/**
 * Paper-aligned TypeScript definitions for Candidate Capability Intelligence (CCI).
 */

export type CanonicalRole =
  | 'backend'
  | 'frontend'
  | 'fullstack'
  | 'ml_engineer'
  | 'devops_cloud'
  | 'data_engineer';

export type CapabilityKey =
  | 'backend_engineering'
  | 'frontend_engineering'
  | 'database_engineering'
  | 'devops_cloud'
  | 'machine_learning'
  | 'data_engineering'
  | 'algorithms_problem_solving'
  | 'testing_quality'
  | 'security'
  | 'software_architecture'
  | 'collaboration'
  | 'documentation_communication';

export type RequirementPriority = 'mandatory' | 'preferred' | 'nice_to_have' | 'optional';

export type AnalysisStage =
  | 'PARSING_CV'
  | 'INGESTING_SOURCES'
  | 'ANALYZING_ARTIFACTS'
  | 'BUILDING_EVIDENCE'
  | 'CALIBRATING_RELIABILITY'
  | 'ESTIMATING_OWNERSHIP'
  | 'COMPUTING_UNCERTAINTY'
  | 'SCORING'
  | 'PRIORITIZING_PROBES'
  | 'GENERATING_DOSSIER';

export type AnalysisStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'cancelled';

export type ClaimStatus = 'corroborated' | 'partial' | 'unknown' | 'contradicted';

export interface NormalizedRequirement {
  requirement_id: string;
  source_text: string;
  normalized_name: string;
  priority: RequirementPriority;
  capability_mappings: CapabilityKey[];
  technology_mentions: string[];
}

export interface CandidateManifest {
  candidate_id: string;
  full_name?: string;
  primary_email?: string;
  github_usernames: string[];
  github_repositories: string[];
  deployment_urls: string[];
  portfolio_urls: string[];
  declared_skills: string[];
  extraction_metadata: Record<string, any>;
}

export interface PipelineStageInfo {
  stage: AnalysisStage;
  label: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  started_at?: string;
  completed_at?: string;
}

export interface CapabilityEstimate {
  capability_key: CapabilityKey;
  estimate: number | null;
  is_observed: boolean;
  effective_evidence_count: number;
  raw_evidence_count: number;
  cluster_count?: number;
  standard_error: number;
  dispersion: number;
  ci_lower: number | null;
  ci_upper: number | null;
  coverage_k: number;
}

export interface CapabilityConflict {
  capability_key: CapabilityKey;
  positive_support_sum: number;
  negative_support_sum: number;
  contradiction_diagnostic: number; // D_k in [-1, 1]
  has_meaningful_conflict: boolean;
  triggering_evidence_ids?: string[];
}

export interface ProbePriority {
  capability_key: CapabilityKey;
  rank: number;
  priority_score: number;
  role_weight: number;
  coverage_gap_term: number;
  uncertainty_term: number;
  contradiction_term: number;
}

export interface InterviewQuestion {
  question_id: string;
  target_capability: CapabilityKey;
  question_text: string;
  rationale: string;
  verification_guidance: string;
  grounding_evidence_ids: string[];
  suggested_followups: string[];
}

export interface OwnershipAssessment {
  assessment_id: string;
  repository_url: string;
  candidate_identifier: string;
  ownership_score: number;
  feature_vector: Record<string, number>;
  is_fork: boolean;
  is_vendor_or_generated: boolean;
  attribution_confidence: number;
  limitations: string[];
}

export interface ClaimCorroboration {
  claim_id: string;
  claim_text: string;
  target_capability: CapabilityKey;
  status: ClaimStatus;
  confidence: number;
  grounding_evidence_ids: string[];
  citation_urls: string[];
  explanation: string;
}

export interface Dossier {
  dossier_id: string;
  candidate_id: string;
  analysis_run_id: string;
  role: CanonicalRole;
  rci: number | null;
  coverage: number;
  is_insufficient_evidence: boolean;
  capability_estimates: Record<CapabilityKey, CapabilityEstimate>;
  capability_conflicts: Record<CapabilityKey, CapabilityConflict>;
  role_requirements: NormalizedRequirement[];
  ownership_assessments: OwnershipAssessment[];
  claims_corroboration: ClaimCorroboration[];
  interview_probes: ProbePriority[];
  interview_questions: InterviewQuestion[];
  system_limitations: string[];
  versions: Record<string, string>;
  generated_at: string;
}

export interface CEGNode {
  id: string;
  type: string;
  label: string;
  properties: Record<string, any>;
}

export interface CEGEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
  properties: Record<string, any>;
}

export interface CEGGraph {
  candidate_id: string;
  analysis_run_id: string;
  nodes: CEGNode[];
  edges: CEGEdge[];
  metadata?: Record<string, any>;
}

export interface ProbeEvaluationItem {
  capability_key: CapabilityKey;
  rating: number; // 1 to 5
  notes: string;
  is_gap_resolved: boolean;
}

export type HiringRecommendation = 'strong_hire' | 'lean_hire' | 'lean_no_hire' | 'no_hire';

export interface InterviewFeedbackPayload {
  candidate_id: string;
  interviewer_name: string;
  probe_evaluations: ProbeEvaluationItem[];
  overall_recommendation: HiringRecommendation;
  overall_notes?: string;
}

export interface InterviewFeedbackResponse {
  feedback_id: string;
  candidate_id: string;
  interviewer_name: string;
  evaluations_count: number;
  audit_event_id: string;
  recorded_at: string;
}

export interface AuditEventItem {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  user_id: string | null;
  details: Record<string, any>;
  created_at: string;
}
