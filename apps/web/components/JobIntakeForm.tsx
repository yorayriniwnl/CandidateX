'use client';

import React, { useState } from 'react';
import { Briefcase, CheckCircle2, ChevronRight, FileText, Sparkles } from 'lucide-react';
import { CanonicalRole, CapabilityKey, NormalizedRequirement } from '../types/cci';

const CANONICAL_ROLES: { id: CanonicalRole; title: string; description: string }[] = [
  { id: 'backend', title: 'Backend Engineer', description: 'Distributed services, APIs, databases, concurrency' },
  { id: 'frontend', title: 'Frontend Engineer', description: 'Web UI, state management, browsers, performance' },
  { id: 'fullstack', title: 'Fullstack Engineer', description: 'End-to-end applications, frontend and backend integration' },
  { id: 'ml_engineer', title: 'ML Engineer', description: 'Model training, serving, feature pipelines, algorithms' },
  { id: 'devops_cloud', title: 'DevOps / Cloud Engineer', description: 'Infrastructure-as-code, CI/CD, containers, security' },
  { id: 'data_engineer', title: 'Data Engineer', description: 'ETL pipelines, data warehousing, stream processing' },
];

export const JobIntakeForm: React.FC<{
  onComplete?: (role: CanonicalRole, jdText: string, requirements: NormalizedRequirement[]) => void;
}> = ({ onComplete }) => {
  const [selectedRole, setSelectedRole] = useState<CanonicalRole>('backend');
  const [seniority, setSeniority] = useState('Senior');
  const [jobTitle, setJobTitle] = useState('Senior Backend Engineer');
  const [jdText, setJdText] = useState(
    `We are seeking a Senior Backend Engineer to architect high-throughput microservices.\n\nMandatory Requirements:\n- 5+ years of experience with Python (FastAPI/SQLAlchemy) or Go.\n- Proven expertise in relational schema design and PostgreSQL optimization.\n- Strong unit and integration testing habits (pytest/mocks).\n\nPreferred:\n- Experience with Docker, Kubernetes, and automated CI/CD.\n- Knowledge of Kafka and distributed event streaming.`
  );
  const [isExtracted, setIsExtracted] = useState(false);

  const handleExtract = () => {
    setIsExtracted(true);
  };

  const sampleExtractedReqs: NormalizedRequirement[] = [
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
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
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
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Job Title</label>
          <input
            type="text"
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Seniority Level</label>
          <select
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            value={seniority}
            onChange={(e) => setSeniority(e.target.value)}
          >
            <option>Junior</option>
            <option>Mid-Level</option>
            <option>Senior</option>
            <option>Staff / Lead</option>
            <option>Principal / Architect</option>
          </select>
        </div>
      </div>

      {/* Canonical Role Selection */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-2">Canonical Role (Paper Profile)</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {CANONICAL_ROLES.map((r) => {
            const isSelected = selectedRole === r.id;
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => setSelectedRole(r.id)}
                className={`text-left p-3 rounded-lg border transition-all ${
                  isSelected
                    ? 'bg-indigo-500/10 border-indigo-500/60 ring-1 ring-indigo-500/50'
                    : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'
                }`}
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

      {/* Verbatim JD Input */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center justify-between">
          <span>Verbatim Job Description</span>
          <span className="text-slate-500">Text is analyzed for requirements without hallucinatory expansion</span>
        </label>
        <textarea
          rows={6}
          className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-sm text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
        />
      </div>

      <div className="flex justify-between items-center pt-2">
        <button
          type="button"
          onClick={handleExtract}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 border border-slate-700"
        >
          <Sparkles className="w-4 h-4 text-indigo-400" />
          Extract Requirements Preview
        </button>

        <button
          type="button"
          onClick={() => onComplete && onComplete(selectedRole, jdText, sampleExtractedReqs)}
          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-lg shadow-indigo-600/20"
        >
          Confirm & Calibrate Role Profile
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Extracted Requirements Preview */}
      {isExtracted && (
        <div className="mt-4 p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Extracted Requirements ({sampleExtractedReqs.length})
            </h3>
            <span className="text-xs text-indigo-400 font-mono">Ontology v1.0.0</span>
          </div>

          <div className="space-y-2">
            {sampleExtractedReqs.map((req) => (
              <div
                key={req.requirement_id}
                className="flex items-start justify-between p-2.5 bg-slate-900/70 border border-slate-800/80 rounded-md text-xs"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-slate-200">{req.normalized_name}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold ${
                        req.priority === 'mandatory'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      }`}
                    >
                      {req.priority}
                    </span>
                  </div>
                  <p className="text-slate-400 italic">"{req.source_text}"</p>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
                  {req.capability_mappings.map((cap) => (
                    <span key={cap} className="px-2 py-0.5 bg-slate-800 rounded text-[11px] text-indigo-300 border border-slate-700">
                      {cap.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
