import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { downloadReport, fetchReports } from '../../services/backendService';
import { formatDateTime } from '../../utils/formatDate';

const ReportsPage = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadLoading, setDownloadLoading] = useState({});

  useEffect(() => {
    const loadReports = async () => {
      try {
        setLoading(true);
        const data = await fetchReports();
        setReports(data?.reports || []);
      } catch (err) {
        setReports([]);
      } finally {
        setLoading(false);
      }
    };

    loadReports();
  }, []);

  const handleDownload = async (report) => {
    setDownloadLoading((prev) => ({ ...prev, [report.id]: true }));
    try {
      await downloadReport(report.id, report.report_filename);
    } catch (err) {
      // Download error - could show toast notification
    } finally {
      setDownloadLoading((prev) => ({ ...prev, [report.id]: false }));
    }
  };

  const getStatusColor = (status) => {
    if (status === 'PASS') return 'text-emerald-400';
    if (status === 'FAIL') return 'text-rose-400';
    return 'text-slate-400';
  };

  if (loading) {
    return (
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-slate-300">
        Loading reports...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-lg shadow-slate-950/30">
        <h2 className="text-2xl font-semibold text-white">Reports</h2>
        <p className="mt-3 max-w-2xl text-slate-400">
          Verification reports and audit-ready summaries for completed drawing comparisons.
        </p>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-slate-950/30">
        {reports.length === 0 ? (
          <p className="text-sm text-slate-500">No reports generated yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="pb-3 text-left font-semibold text-slate-400">Report ID</th>
                <th className="pb-3 text-left font-semibold text-slate-400">Upload ID</th>
                <th className="pb-3 text-left font-semibold text-slate-400">Accuracy</th>
                <th className="pb-3 text-left font-semibold text-slate-400">Status</th>
                <th className="pb-3 text-left font-semibold text-slate-400">Created</th>
                <th className="pb-3 text-right font-semibold text-slate-400">Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id} className="border-b border-slate-800/50 last:border-0">
                  <td className="py-3 text-white">#{report.id}</td>
                  <td className="py-3 text-slate-300">{report.upload_id}</td>
                  <td className="py-3 text-white">{report.accuracy}%</td>
                  <td className={`py-3 font-semibold ${getStatusColor(report.status)}`}>
                    {report.status}
                  </td>
                  <td className="py-3 text-slate-300">{formatDateTime(report.created_at)}</td>
                  <td className="py-3 text-right">
                    <button
                      type="button"
                      onClick={() => handleDownload(report)}
                      disabled={downloadLoading[report.id]}
                      className="inline-flex items-center gap-1.5 rounded-2xl bg-violet-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Download className="h-3 w-3" />
                      {downloadLoading[report.id] ? 'Downloading...' : 'Download'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

export default ReportsPage;
