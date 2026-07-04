import { LayoutDashboard, GitCompareArrows, FileText, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/compare', label: 'Compare Drawings', icon: GitCompareArrows },
  { to: '/reports', label: 'Reports', icon: FileText },
];

const Sidebar = ({ collapsed, onToggle }) => {
  return (
    <aside className={`hidden border-r border-slate-800 bg-slate-950/80 backdrop-blur lg:flex lg:flex-col ${collapsed ? 'w-20' : 'w-72'}`}>
      <div className="flex items-center justify-between border-b border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-cyan-500/15 p-2 text-cyan-400">
            <GitCompareArrows className="h-5 w-5" />
          </div>
          {!collapsed ? <span className="text-sm font-semibold text-white">CADVerify AI</span> : null}
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="mt-6 flex-1 space-y-2 px-3">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                isActive ? 'bg-cyan-500/15 text-cyan-400' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <Icon className="h-5 w-5" />
            {!collapsed ? <span>{label}</span> : null}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
