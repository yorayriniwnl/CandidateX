'use client';

import React, { useState, useRef } from 'react';
import { AlertCircle, Briefcase, CheckCircle2, ChevronRight, FileCheck, FileText, Sparkles, Upload, X } from 'lucide-react';
import { CanonicalRole, CapabilityKey, NormalizedRequirement } from '../types/cci';

import { parseJobDescription, uploadJobDescription } from '../lib/api';

import { GlassCard } from '@/components/ui/GlassCard';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { motion, AnimatePresence } from 'framer-motion';

const CANONICAL_ROLES: { id: CanonicalRole; title: string; description: string }[] = [
  { id: 'backend', title: 'Backend Engineer', description: 'Distributed services, APIs, databases, concurrency' },
  { id: 'frontend', title: 'Frontend Engineer', description: 'Web UI, state management, browsers, performance' },
  { id: 'fullstack', title: 'Fullstack Engineer', description: 'End-to-end applications, frontend and backend integration' },
  { id: 'ml_engineer', title: 'ML Engineer', description: 'Model training, serving, feature pipelines, algorithms' },
  { id: 'devops_cloud', title: 'DevOps / Cloud Engineer', description: 'Infrastructure-as-code, CI/CD, containers, security' },
  { id: 'data_engineer', title: 'Data Engineer', description: 'ETL pipelines, data warehousing, stream processing' },
];

const ROLE_JD_TEMPLATES: Record<CanonicalRole, { title: string; text: string }> = {
  backend: {
    title: 'Senior Backend Distributed Infrastructure Engineer',
    text: `We are seeking a Senior Backend Engineer to architect high-throughput microservices.\n\nMandatory Requirements:\n- 5+ years of experience with Python (FastAPI/SQLAlchemy) or Go.\n- Proven expertise in relational schema design and PostgreSQL optimization.\n- Strong unit and integration testing habits (pytest/mocks).\n\nPreferred:\n- Experience with Docker, Kubernetes, and automated CI/CD.\n- Knowledge of Kafka and distributed event streaming.`,
  },
  frontend: {
    title: 'Staff Frontend Platform & Web Applications Engineer',
    text: `We are looking for a Staff Frontend Platform Engineer to drive web experience.\n\nMandatory Requirements:\n- 5+ years of extensive experience building production web applications in modern TypeScript and React / Next.js.\n- Deep understanding of browser architecture and Core Web Vitals performance profiling.\n- Rigorous commitment to web accessibility (WCAG 2.1 AA/AAA, WAI-ARIA authoring practices).\n- Proven expertise writing automated frontend tests with Jest/Vitest and Playwright.\n\nPreferred:\n- Micro-frontends, module federation, or Turborepo.\n- Client-side state machines, GraphQL, or WebSockets.`,
  },
  fullstack: {
    title: 'Lead Fullstack Product Engineer',
    text: `We are looking for an experienced Fullstack Engineer to drive core product features.\n\nMandatory Requirements:\n- 5+ years of fullstack web engineering experience delivering production applications.\n- Strong proficiency in modern TypeScript, React, and server-side frameworks (Node.js or Python).\n- Deep hands-on experience with relational databases (PostgreSQL) and caching systems (Redis).\n- Proven track record building and testing end-to-end applications (unit, integration, and E2E tests).\n\nPreferred:\n- Experience with GraphQL, tRPC, or schema-driven API generation.\n- Hands-on deployment experience with Docker and AWS.`,
  },
  ml_engineer: {
    title: 'Senior Machine Learning & Applied AI Systems Engineer',
    text: `We are seeking a Senior Machine Learning Engineer to design and deploy foundation models.\n\nMandatory Requirements:\n- 4+ years of hands-on production experience training and serving machine learning models in Python and PyTorch.\n- Strong practical knowledge of modern transformer architectures, fine-tuning (LoRA, PEFT), and embedding models.\n- Experience deploying real-time model inference at scale (vLLM, Triton, TensorRT, or ONNX Runtime).\n- Demonstrated mastery of model evaluation methodologies, calibration metrics, and regression testing in CI.\n\nPreferred:\n- Distributed training frameworks (DeepSpeed, FSDP, Ray).\n- Hands-on deployment of vector search engines (Qdrant, Milvus, FAISS).`,
  },
  devops_cloud: {
    title: 'Staff Site Reliability & Cloud Infrastructure Engineer',
    text: `We are looking for a Staff Site Reliability Engineer to design, scale, and automate infrastructure.\n\nMandatory Requirements:\n- 5+ years in production Site Reliability Engineering, DevOps, or Cloud Infrastructure roles.\n- Expert-level proficiency with Kubernetes administration, networking, security policies, and debugging.\n- Advanced mastery of Terraform / Infrastructure as Code and cloud architecture (AWS or GCP).\n- Strong experience with production observability stacks (Prometheus, Grafana, OpenTelemetry, Datadog).\n\nPreferred:\n- Modern eBPF networking, service mesh (Cilium, Istio), or zero-trust network policies.\n- Hands-on experience with chaos engineering tools (Chaos Mesh, Gremlin).`,
  },
  data_engineer: {
    title: 'Senior Data Platform Engineer',
    text: `We are looking for a Senior Data Engineer to build enterprise analytical pipelines.\n\nMandatory Requirements:\n- 5+ years building scalable data ingestion and transformation pipelines using Python, SQL, and Spark.\n- Experience with columnar data warehouses (Snowflake, BigQuery, DuckDB) and data modeling.\n- Workflow orchestration with Apache Airflow or Dagster.\n\nPreferred:\n- Streaming architectures with Apache Kafka or Flink.\n- Data quality frameworks (Great Expectations, dbt).`,
  },
};

export const JobIntakeForm: React.FC<{
  onComplete?: (role: CanonicalRole, jdText: string, requirements: NormalizedRequirement[]) => void;
}> = ({ onComplete }) => {
  const [selectedRole, setSelectedRole] = useState<CanonicalRole>('backend');
  const [seniority, setSeniority] = useState('Senior');
  const [jobTitle, setJobTitle] = useState(ROLE_JD_TEMPLATES.backend.title);
  const [jdText, setJdText] = useState(ROLE_JD_TEMPLATES.backend.text);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError('');
    const ext = file.name.toLowerCase();
    if (!ext.endsWith('.pdf') && !ext.endsWith('.docx')) {
      setUploadError('Only PDF and DOCX files are supported.');
      return;
    }
    setIsUploading(true);
    try {
      const res = await uploadJobDescription(file, jobTitle, selectedRole);
      setUploadedFile(file.name);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Failed to upload document.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setUploadError('');
  };

  const [isExtracted, setIsExtracted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const [extractedReqs, setExtractedReqs] = useState<NormalizedRequirement[]>([
    {
      requirement_id: 'req-1',
      source_text: '5+ years of experience with Python (FastAPI/SQLAlchemy) or Go',
      normalized_name: 'Python / Go Microservices',
      priority: 'mandatory',
      capability_mappings: ['backend_engineering'],
      technology_mentions: ['Python', 'FastAPI', 'SQLAlchemy', 'Go'],
    },
    {
      requirement_id: 'req-2',
      source_text: 'Proven expertise in relational schema design and PostgreSQL optimization',
      normalized_name: 'PostgreSQL Relational Schema Design',
      priority: 'mandatory',
      capability_mappings: ['database_engineering'],
      technology_mentions: ['PostgreSQL'],
    },
    {
      requirement_id: 'req-3',
      source_text: 'Strong unit and integration testing habits (pytest/mocks)',
      normalized_name: 'Automated Testing Rigor',
      priority: 'mandatory',
      capability_mappings: ['testing_quality'],
      technology_mentions: ['pytest', 'mocks'],
    },
    {
      requirement_id: 'req-4',
      source_text: 'Experience with Docker, Kubernetes, and automated CI/CD',
      normalized_name: 'Container & Cloud Orchestration',
      priority: 'preferred',
      capability_mappings: ['devops_cloud'],
      technology_mentions: ['Docker', 'Kubernetes', 'CI/CD'],
    },
  ]);

  const handleRoleSelect = (role: CanonicalRole) => {
    setSelectedRole(role);
    if (ROLE_JD_TEMPLATES[role]) {
      setJobTitle(ROLE_JD_TEMPLATES[role].title);
      setJdText(ROLE_JD_TEMPLATES[role].text);
    }
  };

  const handleExtract = async () => {
    setIsLoading(true);
    try {
      const parsed = await parseJobDescription(jdText, selectedRole);
      if (parsed.requirements && parsed.requirements.length > 0) {
        setExtractedReqs(parsed.requirements);
      }
    } catch {
      // Graceful fallback to default requirements if backend is offline
    } finally {
      setIsLoading(false);
      setIsExtracted(true);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <GlassCard variant="strong" glow="indigo" className="p-6 space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Job Specification Intake</h2>
            <p className="text-xs text-slate-400">Define role requirements to calibrate capability weights w_k</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassInput
          label="Job Title"
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          glowColor="indigo"
        />
        <GlassSelect
          label="Seniority Level"
          value={seniority}
          onChange={(e) => setSeniority(e.target.value)}
          options={[
            { value: 'Junior', label: 'Junior' },
            { value: 'Mid-Level', label: 'Mid-Level' },
            { value: 'Senior', label: 'Senior' },
            { value: 'Staff / Lead', label: 'Staff / Lead' },
            { value: 'Principal / Architect', label: 'Principal / Architect' },
          ]}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-300 mb-2">Canonical Role (Paper Profile)</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {CANONICAL_ROLES.map((r) => {
            const isSelected = selectedRole === r.id;
            return (
              <button
                key={r.id}
                type="button"
                aria-pressed={isSelected}
                className={`rounded-xl border p-4 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-300 ${isSelected ? 'bg-indigo-500/10 border-indigo-400/40' : 'bg-white/[0.02] border-white/10 hover:border-indigo-400/30'}`}
                onClick={() => handleRoleSelect(r.id)}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-sm font-medium ${isSelected ? 'text-indigo-300' : 'text-slate-200'}`}>
                    {r.title}
                  </span>
                  {isSelected && <CheckCircle2 className="w-4 h-4 text-indigo-400" />}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{r.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-3">
        <label className="block text-xs font-medium text-slate-300">
          Job Description & Recruitment Rules Document (PDF or DOCX)
        </label>

        {!uploadedFile ? (
          <div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="hidden"
              id="jd-file-upload-input"
            />
            <button
              type="button"
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center justify-center gap-3 p-4 rounded-xl border border-dashed border-indigo-500/30 hover:border-indigo-500/60 bg-indigo-500/5 hover:bg-indigo-500/10 transition-colors text-slate-300 hover:text-white cursor-pointer group"
            >
              <Upload className={`w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform ${isUploading ? 'animate-bounce' : ''}`} />
              <div className="text-left">
                <span className="text-sm font-medium block">
                  {isUploading ? 'Uploading & parsing document…' : 'Upload Job Description or Recruitment Rules (PDF / DOCX)'}
                </span>
                <span className="text-xs text-slate-400">
                  PDF or DOCX document · requirements calibrated automatically.
                </span>
              </div>
            </button>
          </div>
        ) : (
          <GlassCard variant="subtle" className="flex items-center justify-between p-3.5 border border-indigo-500/30 bg-indigo-500/10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-100">{uploadedFile}</span>
                  <GlowBadge variant="brand" size="sm">Document loaded</GlowBadge>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Job description & recruitment rules loaded and ready for evaluation.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleRemoveFile}
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Remove document"
            >
              <X className="w-4 h-4" />
            </button>
          </GlassCard>
        )}

        {uploadError && (
          <p className="text-xs text-rose-400 flex items-center gap-1.5 mt-1">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            {uploadError}
          </p>
        )}
      </div>

      <div>
        <GlassInput
          variant="textarea"
          label={
            uploadedFile
              ? "Additional recruiter notes or custom criteria (optional)"
              : "Verbatim Job Description (Text is analyzed for requirements without hallucinatory expansion)"
          }
          value={uploadedFile ? '' : jdText}
          onChange={(e) => setJdText(e.target.value)}
          placeholder={
            uploadedFile
              ? "Optional recruiter notes or extra instructions…"
              : "Paste the responsibilities, standards, or recruitment rules…"
          }
          rows={uploadedFile ? 4 : 8}
          glowColor="indigo"
        />
        {uploadedFile && (
          <p className="text-xs text-slate-400 mt-1">
            The uploaded job description & recruitment rules are ready for evaluation.
          </p>
        )}
      </div>

      <div className="flex flex-wrap justify-between items-center gap-3 pt-2">
        <GlassButton
          variant="secondary"
          onClick={handleExtract}
          disabled={isLoading}
          icon={<Sparkles className="w-4 h-4 text-indigo-400" />}
          iconPosition="left"
        >
          {isLoading ? 'Extracting via Ontology Engine...' : 'Extract Requirements Preview'}
        </GlassButton>

        <GlassButton
          variant="primary"
          onClick={() => onComplete && onComplete(selectedRole, jdText, extractedReqs)}
          icon={<ChevronRight className="w-4 h-4" />}
          iconPosition="right"
        >
          Confirm role profile
        </GlassButton>
      </div>

      {isExtracted && (
        <div className="mt-4 p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Extracted Requirements ({extractedReqs.length})
            </h3>
            <span className="text-xs text-indigo-400 font-mono">Ontology v1.0.0</span>
          </div>

          <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-2">
            {extractedReqs.map((req) => (
              <motion.div key={req.requirement_id} variants={itemVariants}>
                <GlassCard variant="subtle" className="flex items-start justify-between p-2.5">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-slate-200">{req.normalized_name}</span>
                      <GlowBadge variant={req.priority === 'mandatory' ? 'danger' : 'info'} size="sm">
                        {req.priority}
                      </GlowBadge>
                    </div>
                    <p className="text-slate-400 italic">"{req.source_text}"</p>
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
                    {req.capability_mappings.map((cap) => (
                      <GlowBadge key={cap} variant="neutral" size="sm">
                        {cap.replace('_', ' ')}
                      </GlowBadge>
                    ))}
                  </div>
                </GlassCard>
              </motion.div>
            ))}
          </motion.div>
        </div>
      )}
    </GlassCard>
  );
};
