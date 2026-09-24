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
  evidence_mode?: string;
  role_weights?: Record<CapabilityKey, number>;
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
  evidence_records?: any[];
  academic_records?: AcademicRecord[];
  project_entities?: ProjectEntity[];
  credentials?: CredentialEntity[];
  publications?: PublicationEntity[];
  coding_profiles?: CodingProfileEntity[];
  quantified_claims?: QuantifiedClaim[];
  timeline?: CandidateTimeline;
  source_inventory?: SourceInventoryItem[];
  system_limitations: string[];
  versions: Record<string, string>;
  generated_at: string;
}

export interface AcademicRecord {
  institution: string;
  degree?: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  status: string;
  verification_status: string;
  coursework?: string[];
  notes?: string;
}

export interface ProjectEntity {
  project_id: string;
  name: string;
  resume_claim?: string;
  repository?: string;
  deployment?: string;
  documentation?: string;
  technologies?: string[];
  db?: string;
  backend?: string;
  frontend?: string;
  tests?: string;
  infrastructure?: string;
  candidate_attribution?: string;
  recency?: string;
  credentials_or_publication_relationship?: string;
  quantitative_claims?: string[];
  contradictions?: string[];
  limitations?: string[];
  trace_links?: TraceLink[];
}

export interface CredentialEntity {
  credential_id: string;
  title: string;
  issuer: string;
  issue_date?: string;
  expiration_date?: string;
  credential_url?: string;
  verification_status: 'verified' | 'unverified' | 'expired' | 'issuer_confirmed';
  notes?: string;
}

export interface PublicationEntity {
  publication_id: string;
  title: string;
  authors: string[];
  venue?: string;
  year?: number;
  doi?: string;
  url?: string;
  provenance_family?: string;
}

export interface CodingProfileEntity {
  platform: string;
  profile_url: string;
  username: string;
  solved_count?: number;
  ranking_percentile?: number;
  algorithmic_capability_observed: boolean;
}

export interface QuantifiedClaim {
  metric: string;
  value: number | string;
  unit: string;
  context: string;
  source: string;
  verification_status: 'supported_by_artifacts' | 'portfolio_mention_only' | 'unverified_mention';
  supporting_artifacts: string[];
  limitations?: string[];
}

export interface TimelineEvent {
  event_id: string;
  date_or_year: string;
  category: 'education' | 'experience' | 'repository' | 'deployment' | 'credential' | 'publication';
  description: string;
  source_reference?: string;
}

export interface TimelineInconsistency {
  inconsistency_type: string;
  description: string;
  events_involved: string[];
}

export interface CandidateTimeline {
  events: TimelineEvent[];
  inconsistencies: TimelineInconsistency[];
}

export interface TraceLink {
  claim_id: string;
  evidence_id: string;
  source_url: string;
  artifact_path: string;
  immutable_revision: string;
  content_fingerprint?: string;
  line_or_symbol?: string;
}

export interface EvidenceRecordItem {
  evidence_id: string;
  fingerprint: string;
  source_family: string;
  source_locator: string;
  immutable_revision: string;
  target_capability: CapabilityKey;
  technical_signal_strength?: number;
  confidence: number;
  observation_type: string;
  provenance?: Record<string, any>;
}

export interface SourceInventoryItem {
  source_id: string;
  url: string;
  kind: string;
  status: 'supplied' | 'discovered' | 'queued' | 'fetched' | 'failed' | 'blocked' | 'deferred' | 'not_scanned' | 'observed';
  discovered_by?: string;
  discovery_depth?: number;
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

export interface TheoremMetadata {
  id: number;
  name: string;
  category: string;
  latex_formula: string;
  description: string;
  bound_statement: string;
  physical_intuition: string;
  key_properties: string[];
}

export interface AblationRow {
  model_name: string;
  display_name: string;
  mae: number;
  rmse: number;
  spearman_rho: number;
  kendall_tau: number;
  statistical_significance: string;
  is_baseline?: boolean;
}

export interface RoleBreakdownRow {
  role: string;
  display_name: string;
  full_cci_mae: number;
  no_decay_mae: number | null;
  no_ownership_mae: number | null;
  uniform_weights_mae: number | null;
}

export interface AblationStudyResponse {
  total_candidates: number;
  total_seeds: number;
  roles_count: number;
  models: AblationRow[];
  role_breakdown: RoleBreakdownRow[];
  latex_table: string;
  markdown_table: string;
  notes: string;
}

export interface CalculationRequest {
  theorem_id: number;
  parameters: Record<string, any>;
}

export interface CalculationResponse {
  theorem_id: number;
  theorem_name: string;
  formula: string;
  result: number;
  intermediate_steps: Record<string, any>;
  bounds_satisfied: boolean;
  explanation: string;
}

