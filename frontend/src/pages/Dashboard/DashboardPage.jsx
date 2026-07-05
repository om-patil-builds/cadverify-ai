import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, FileCheck2, Layers3 } from 'lucide-react';
import Card from '../../components/ui/Card';
import UploadCard from '../../components/ui/UploadCard';
import { checkBackendHealth, fetchUploads } from '../../services/backendService';
import { formatDateTime } from '../../utils/formatDate';

const DashboardPage = () => {
  const [backendStatus, setBackendStatus] = useState('loading');
  const [backendMessage, setBackendMessage] = useState('Checking backend connection...');
  const [uploads, setUploads] = useState([]);
  const [uploadCount, setUploadCount] = useState(0);
  const [comparisonCount, setComparisonCount] = useState(0);

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

    const loadUploads = async () => {
      try {
        const response = await fetchUploads();
        if (isMounted) {
          const total = response?.total ?? response?.count ?? 0;
          setUploadCount(total);
          setComparisonCount(response?.comparison_count ?? 0);
          setUploads(response?.uploads ?? []);
        }
      } catch (error) {
        if (isMounted) {
          setUploads([]);
          setUploadCount(0);
        }
      }
    };

    loadBackendStatus();
    loadUploads();

    return () => {
      isMounted = false;
    };
  }, []);

  const stats = useMemo(
    () => [
      {
        title: 'Backend Status',
        value:
          backendStatus === 'connected'
            ? '🟢 Backend Connected'
            : backendStatus === 'offline'
            ? '🔴 Backend Offline'
            : '⏳ Checking...',
        description: backendMessage,
        icon: Activity,
      },
      {
        title: 'Uploaded Drawings',
        value: uploadCount.toString(),
        description: uploadCount === 0 ? 'No drawings uploaded yet' : 'Database-backed upload count',
        icon: Layers3,
      },
      { title: 'Comparison Reports', value: comparisonCount.toString(), description: comparisonCount === 0 ? 'No comparisons completed yet' : 'Completed drawing comparisons', icon: FileCheck2 },
    ],
    [backendMessage, backendStatus, uploadCount, comparisonCount]
  );

  const navigate = useNavigate();

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
            <h3 className="text-lg font-semibold text-white">Recent Uploads</h3>
            <span className="text-sm text-slate-500">Latest 5 records</span>
          </div>
          <ul className="space-y-3">
            {uploads.length === 0 ? (
              <li className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
                No uploads recorded yet.
              </li>
            ) : (
              uploads.slice(0, 5).map((item) => (
                <li key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-400">
                  <div className="font-medium text-white">{item.pdf_filename}</div>
                  <div className="mt-1 text-xs text-slate-500">{formatDateTime(item.created_at)}</div>
                </li>
              ))
            )}
          </ul>
        </div>

        <div className="space-y-3">
          {uploads.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-6 text-center text-sm text-slate-400">
              No drawings uploaded yet.
            </div>
          ) : (
            uploads.slice(0, 5).map((upload) => (
              <UploadCard
                key={upload.id}
                upload={{ ...upload, created_at: formatDateTime(upload.created_at) }}
                onClick={() => navigate(`/compare/${upload.id}`)}
              />
            ))
          )}
        </div>
      </section>

      <footer className="border-t border-slate-800 pt-6 text-sm text-slate-500">
        CADVerify AI • Enterprise Engineering Review Workspace
      </footer>
    </div>
  );
};

export default DashboardPage;
