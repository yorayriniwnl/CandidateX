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
