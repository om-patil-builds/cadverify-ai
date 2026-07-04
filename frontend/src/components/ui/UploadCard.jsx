import { formatDateTime } from '../../utils/formatDate';

const UploadCard = ({ upload, onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-left transition hover:border-cyan-400/80 hover:bg-slate-900"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Upload ID</p>
          <p className="text-base font-semibold text-white">{upload.id}</p>
        </div>
        <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
          View
        </span>
      </div>
      <div className="mt-4 space-y-2 text-sm text-slate-400">
        <div>
          <span className="block text-slate-500">PDF</span>
          <p className="text-white truncate">{upload.pdf_filename}</p>
        </div>
        <div>
          <span className="block text-slate-500">DXF</span>
          <p className="text-white truncate">{upload.dxf_filename}</p>
        </div>
        <div className="text-xs text-slate-500">Uploaded at {upload.created_at ? upload.created_at : ''}</div>
      </div>
    </button>
  );
};

export default UploadCard;
