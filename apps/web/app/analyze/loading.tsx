export default function Loading() {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="glass-card animate-pulse rounded-2xl border border-slate-700/50 bg-slate-800/20 p-6 md:p-8 space-y-6">
        <div className="h-8 bg-slate-700/40 rounded w-1/4"></div>
        <div className="space-y-4">
          <div className="h-4 bg-slate-700/30 rounded w-3/4"></div>
          <div className="h-4 bg-slate-700/30 rounded w-full"></div>
          <div className="h-4 bg-slate-700/30 rounded w-5/6"></div>
        </div>
      </div>
    </div>
  );
}
