export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <div className="max-w-2xl border border-slate-800 bg-slate-900/60 p-8 rounded-xl shadow-2xl backdrop-blur">
        <div className="inline-block px-3 py-1 mb-4 text-xs font-semibold uppercase tracking-wider text-cyan-400 bg-cyan-950/80 border border-cyan-800 rounded-full">
          CCI Platform Core
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
          Candidate Capability Intelligence
        </h1>
        <p className="text-sm text-slate-400 mb-6">
          Employer and interviewer technical decision support system. Foundation scaffold active.
        </p>
        <div className="text-xs font-mono text-slate-500 bg-slate-950 p-3 rounded border border-slate-800/80">
          Status: Wave 0 Frozen Contracts Operational
        </div>
      </div>
    </main>
  );
}
