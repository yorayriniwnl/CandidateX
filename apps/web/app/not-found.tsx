import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-6">
      <div className="glass-card max-w-md w-full p-8 text-center space-y-4">
        <h2 className="text-3xl font-bold text-slate-100 mb-2">404</h2>
        <p className="text-lg font-semibold text-slate-200">Page not found</p>
        <p className="text-sm text-slate-400 mb-6">The page you are looking for does not exist or has been moved.</p>
        <Link 
          href="/" 
          className="inline-block mt-4 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/30 transition-colors"
        >
          Return Home
        </Link>
      </div>
    </div>
  );
}
