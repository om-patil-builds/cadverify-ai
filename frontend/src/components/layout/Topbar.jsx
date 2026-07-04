import { Bell, Search, Settings } from 'lucide-react';

const Topbar = () => {
  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950/70 px-6 py-4 backdrop-blur">
      <div>
        <p className="text-sm text-slate-400">Operations Center</p>
        <h1 className="text-xl font-semibold text-white">Engineering Verification Workspace</h1>
      </div>

      <div className="flex items-center gap-3">
        <label className="hidden items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-400 md:flex">
          <Search className="h-4 w-4" />
          <input
            type="text"
            placeholder="Search"
            className="bg-transparent outline-none placeholder:text-slate-500"
          />
        </label>
        <button type="button" className="rounded-xl border border-slate-800 bg-slate-900/70 p-2 text-slate-400 transition hover:text-white">
          <Bell className="h-4 w-4" />
        </button>
        <button type="button" className="rounded-xl border border-slate-800 bg-slate-900/70 p-2 text-slate-400 transition hover:text-white">
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
};

export default Topbar;
