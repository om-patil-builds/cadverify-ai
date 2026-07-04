import { useMemo, useState } from 'react';
import { FileUp, FileCheck2, UploadCloud } from 'lucide-react';
import { uploadDrawingFiles } from '../../services/backendService';

const ComparePage = () => {
  const [pdfFile, setPdfFile] = useState(null);
  const [dxfFile, setDxfFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('info');

  const hasBothFiles = Boolean(pdfFile && dxfFile);

  const handleFileSelection = (event, type) => {
    const selected = event.target.files?.[0] || null;
    if (type === 'pdf') setPdfFile(selected);
    else setDxfFile(selected);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragActive(false);
    const droppedFile = event.dataTransfer.files?.[0] || null;
    if (!droppedFile) return;

    const ext = droppedFile.name.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') setPdfFile(droppedFile);
    else if (ext === 'dxf') setDxfFile(droppedFile);
  };

  const handleUpload = async () => {
    if (!hasBothFiles) {
      setMessageType('error');
      setMessage('Please select both a PDF and a DXF file.');
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(0);
      setMessageType('info');
      setMessage('Uploading files...');

      const response = await uploadDrawingFiles({
        pdfFile,
        dxfFile,
        onUploadProgress: (percent) => setUploadProgress(percent),
      });

      setMessageType('success');
      setMessage(`Upload complete. ID: ${response?.upload_id ?? response?.data?.upload_id ?? 'unknown'}`);
      setPdfFile(null);
      setDxfFile(null);
      setUploadProgress(0);
    } catch (error) {
      setMessageType('error');
      setMessage(error?.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const statusLabel = useMemo(() => {
    if (messageType === 'success') return 'text-emerald-400';
    if (messageType === 'error') return 'text-rose-400';
    return 'text-cyan-400';
  }, [messageType]);

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-lg shadow-slate-950/30">
        <h2 className="text-2xl font-semibold text-white">Compare Drawings</h2>
        <p className="mt-3 max-w-2xl text-slate-400">Upload a scanned PDF drawing and its DXF counterpart to prepare them for future comparison workflows.</p>
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-lg shadow-slate-950/30">
        <div
          className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${dragActive ? 'border-cyan-400 bg-cyan-500/10' : 'border-slate-700 bg-slate-950/40'}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <UploadCloud className="mx-auto h-10 w-10 text-cyan-400" />
          <p className="mt-4 text-lg font-semibold text-white">Drop your files here</p>
          <p className="mt-2 text-sm text-slate-400">Upload one PDF and one DXF file to continue.</p>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <label className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <FileUp className="h-4 w-4 text-cyan-400" />
              Select PDF
            </div>
            <input type="file" accept=".pdf" className="mt-4 block w-full text-sm text-slate-400" onChange={(e) => handleFileSelection(e, 'pdf')} />
            {pdfFile ? <p className="mt-3 text-sm text-slate-400">Selected: {pdfFile.name}</p> : <p className="mt-3 text-sm text-slate-500">No PDF selected</p>}
          </label>

          <label className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <FileUp className="h-4 w-4 text-cyan-400" />
              Select DXF
            </div>
            <input type="file" accept=".dxf" className="mt-4 block w-full text-sm text-slate-400" onChange={(e) => handleFileSelection(e, 'dxf')} />
            {dxfFile ? <p className="mt-3 text-sm text-slate-400">Selected: {dxfFile.name}</p> : <p className="mt-3 text-sm text-slate-500">No DXF selected</p>}
          </label>
        </div>

        <div className="mt-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <button
            type="button"
            onClick={handleUpload}
            disabled={!hasBothFiles || isUploading}
            className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {isUploading ? 'Uploading...' : 'Upload Files'}
          </button>

          <div className="text-sm text-slate-400">{isUploading ? `Progress: ${uploadProgress}%` : 'Upload button is enabled once both files are selected.'}</div>
        </div>

        {isUploading ? (
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-cyan-500 transition-all" style={{ width: `${uploadProgress}%` }} />
          </div>
        ) : null}

        {message ? (
          <div className={`mt-5 rounded-xl border px-4 py-3 text-sm ${messageType === 'success' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : messageType === 'error' ? 'border-rose-500/20 bg-rose-500/10 text-rose-400' : 'border-cyan-500/20 bg-cyan-500/10 text-cyan-400'}`}>
            <div className="flex items-center gap-2">
              <FileCheck2 className="h-4 w-4" />
              <span className={statusLabel}>{message}</span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default ComparePage;
