import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, Circle, Download, File, FileText, Trash2 } from 'lucide-react';
import {
  deleteUpload,
  downloadUploadDxf,
  downloadUploadPdf,
  fetchUploadById,
} from '../../services/backendService';
import { formatDateTime } from '../../utils/formatDate';

const UploadDetailsPage = () => {
  const { uploadId } = useParams();
  const navigate = useNavigate();
  const [upload, setUpload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const loadUpload = async () => {
      try {
        const data = await fetchUploadById(uploadId);
        setUpload(data);
      } catch (err) {
        setError('Unable to load upload details.');
      } finally {
        setLoading(false);
      }
    };

    loadUpload();
  }, [uploadId]);

  const handleDelete = async () => {
    const confirmed = window.confirm('Delete this upload and all associated files?');
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteUpload(uploadId);
      navigate('/dashboard');
    } catch (err) {
      setError('Failed to delete upload. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!upload) return;
    try {
      await downloadUploadPdf(upload.id, upload.pdf_filename);
    } catch (err) {
      setError('Unable to download PDF file.');
    }
  };

  const handleDownloadDxf = async () => {
    if (!upload) return;
    try {
      await downloadUploadDxf(upload.id, upload.dxf_filename);
    } catch (err) {
      setError('Unable to download DXF file.');
    }
  };

  if (loading) {
    return <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-slate-300">Loading drawing workspace…</div>;
  }

  if (error) {
    return <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-rose-300">{error}</div>;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-lg shadow-slate-950/30">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">Drawing Review Workspace</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">Drawing Review Workspace</h2>
            <p className="mt-3 max-w-2xl text-sm text-slate-400">
              Review, verify and process an uploaded engineering drawing.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="rounded-3xl border border-slate-700 bg-slate-950/70 px-5 py-3 text-sm font-semibold text-slate-200 hover:border-cyan-400/70"
          >
            Back to Dashboard
          </button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Upload Information</h3>
              <div className="mt-4 space-y-3 text-sm text-slate-400">
                <div>
                  <span className="block text-slate-500">Upload ID</span>
                  <p className="text-white">{upload.id}</p>
                </div>
                <div>
                  <span className="block text-slate-500">Upload Date</span>
                  <p className="text-white">{formatDateTime(upload.created_at)}</p>
                </div>
                <div>
                  <span className="block text-slate-500">Status</span>
                  <p className="text-emerald-300">Uploaded</p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Drawing Pair</h3>
              <div className="mt-6 space-y-4 text-sm text-slate-400">
                <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <FileText className="h-5 w-5 text-cyan-400" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-500">PDF</p>
                    <p className="truncate text-white">{upload.pdf_filename}</p>
                  </div>
                  <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-400">PDF</span>
                </div>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <File className="h-5 w-5 text-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-500">DXF</p>
                    <p className="truncate text-white">{upload.dxf_filename}</p>
                  </div>
                  <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-400">DXF</span>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Progress Timeline</h3>
              <div className="mt-6 space-y-4 text-sm text-slate-400">
                <div className="flex items-start gap-3">
                  <CheckCircle className="mt-1 h-5 w-5 text-emerald-400" />
                  <div>
                    <p className="font-semibold text-white">Uploaded</p>
                    <p className="text-slate-500">The drawing pair is stored and ready for review.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className="mt-1 h-5 w-5 text-slate-500" />
                  <div>
                    <p className="font-semibold text-white">DXF Parsing</p>
                    <p className="text-slate-500">Available in next milestone.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className="mt-1 h-5 w-5 text-slate-500" />
                  <div>
                    <p className="font-semibold text-white">Drawing Comparison</p>
                    <p className="text-slate-500">Available in next milestone.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className="mt-1 h-5 w-5 text-slate-500" />
                  <div>
                    <p className="font-semibold text-white">Report Generation</p>
                    <p className="text-slate-500">Available in next milestone.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Actions</h3>
              <div className="mt-6 flex flex-col gap-3">
                <button
                  type="button"
                  disabled
                  className="rounded-3xl bg-cyan-500/20 px-5 py-3 text-sm font-semibold text-cyan-200 opacity-80"
                >
                  Parse DXF (Available in Next Milestone)
                </button>
                <button
                  type="button"
                  disabled
                  className="rounded-3xl bg-slate-900/80 px-5 py-3 text-sm font-semibold text-slate-200 opacity-80"
                >
                  Start Comparison (Available in Next Milestone)
                </button>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Downloads</h3>
              <div className="mt-6 grid gap-3">
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  className="rounded-3xl bg-slate-800 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Download PDF
                </button>
                <button
                  type="button"
                  onClick={handleDownloadDxf}
                  className="rounded-3xl bg-slate-800 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-700"
                >
                  Download DXF
                </button>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Danger Zone</h3>
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="mt-4 w-full rounded-3xl bg-rose-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                {isDeleting ? 'Deleting…' : 'Delete Upload'}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default UploadDetailsPage;
