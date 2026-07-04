import { useEffect, useMemo, useState } from 'react';
import { Activity, FileCheck2, Layers3 } from 'lucide-react';
import Card from '../../components/ui/Card';
import { checkBackendHealth } from '../../services/backendService';

const recentActivity = [
  'Frontend shell initialized for CADVerify AI.',
  'Routing and layout structure are ready for future workflows.',
  'Dashboard UI prepared for engineering review experiences.',
];

const DashboardPage = () => {
  const [backendStatus, setBackendStatus] = useState('loading');
  const [backendMessage, setBackendMessage] = useState('Checking backend connection...');

  useEffect(() => {
    let isMounted = true;

    const loadBackendStatus = async () => {
      try {
        const response = await checkBackendHealth();
        if (isMounted) {
          setBackendStatus('connected');
          setBackendMessage(response?.status === 'healthy' ? 'Backend Connected' : 'Backend Connected');
        }
      } catch (error) {
        if (isMounted) {
          setBackendStatus('offline');
          setBackendMessage('Backend Offline');
        }
      }
    };

    loadBackendStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  const stats = useMemo(
    () => [
      {
        title: 'Backend Status',
        value: backendStatus === 'connected' ? '🟢 Backend Connected' : backendStatus === 'offline' ? '🔴 Backend Offline' : '⏳ Checking...',
        description: backendMessage,
        icon: Activity,
      },
      { title: 'Uploaded Drawings', value: '0', description: 'No drawings uploaded yet', icon: Layers3 },
      { title: 'Comparison Reports', value: '0', description: 'Reports queue is currently empty', icon: FileCheck2 },
    ],
    [backendMessage, backendStatus]
  );

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-2xl shadow-slate-950/40">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">CADVerify AI</p>
            <h2 className="mt-3 text-3xl font-semibold text-white sm:text-4xl">
              AI-Powered Engineering Drawing Verification Platform
            </h2>
            <p className="mt-4 max-w-2xl text-base text-slate-400">
              A scalable workspace for reviewing engineering drawings, identifying discrepancies, and generating verification insights.
            </p>
          </div>
          <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-300">
            Status: {backendStatus === 'connected' ? 'Connected to backend' : backendStatus === 'offline' ? 'Backend unavailable' : 'Checking backend...'}
          </div>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.title} {...stat} />
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-slate-950/30">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
            <span className="text-sm text-slate-500">Live placeholder</span>
          </div>
          <ul className="space-y-3">
            {recentActivity.map((item) => (
              <li key={item} className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-slate-950/30">
          <h3 className="text-lg font-semibold text-white">Next Steps</h3>
          <ul className="mt-4 space-y-3 text-sm text-slate-400">
            <li>• Connect frontend routes to backend services</li>
            <li>• Add upload and review workflows</li>
            <li>• Prepare report generation experiences</li>
          </ul>
        </div>
      </section>

      <footer className="border-t border-slate-800 pt-6 text-sm text-slate-500">
        CADVerify AI • Enterprise Engineering Review Workspace
      </footer>
    </div>
  );
};

export default DashboardPage;
