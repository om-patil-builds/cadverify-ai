import { useCallback, useState } from 'react';
import { uploadDrawingFiles } from '../../services/backendService';

const ComparePage = () => {
  const [pdfFile, setPdfFile] = useState(null);
  const [dxfFile, setDxfFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('info');
  const [isUploading, setIsUploading] = useState(false);

  const onFileSelect = (fileSetter) => (event) => {
    const file = event.target.files?.[0] ?? null;
    fileSetter(file);
  };

  const handleUpload = async () => {
    if (!pdfFile || !dxfFile) {
      setStatusType('error');
      setStatusMessage('Please select both a PDF and a DXF file before uploading.');
      return;
    }

    setIsUploading(true);
    setProgress(0);
    setStatusType('info');
    setStatusMessage('Uploading files...');

    try {
      const response = await uploadDrawingFiles({
        pdfFile,
        dxfFile,
        onUploadProgress: setProgress,
      });

      setStatusType('success');
      setStatusMessage(`Upload succeeded. Upload ID: ${response?.upload_id ?? 'unknown'}`);
      setPdfFile(null);
      setDxfFile(null);
    } catch (error) {
      setStatusType('error');
      setStatusMessage(
        error?.response?.data?.detail || 'Upload failed. Please try again with valid PDF and DXF files.'
      );
    } finally {
      setIsUploading(false);
      setProgress(0);
    }
  };

  const handleDrop = useCallback(
    (event) => {
      event.preventDefault();
      setDragActive(false);

      const files = Array.from(event.dataTransfer.files || []);
      const pdf = files.find((file) => file.name.toLowerCase().endsWith('.pdf')) || null;
      const dxf = files.find((file) => file.name.toLowerCase().endsWith('.dxf')) || null;

      if (pdf) setPdfFile(pdf);
      if (dxf) setDxfFile(dxf);
    },
    [setPdfFile, setDxfFile]
  );

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 shadow-lg shadow-slate-950/30">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Compare Drawings</h2>
          <p className="mt-2 max-w-2xl text-slate-400">
            Upload a PDF and DXF pair to begin the drawing review workflow.
          </p>
        </div>
      </div>

      <div
        className={`mb-6 rounded-3xl border border-dashed px-6 py-10 text-center transition ${
          dragActive ? 'border-cyan-400/80 bg-slate-950' : 'border-slate-800 bg-slate-900/70'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <p className="text-lg font-semibold text-white">Drag & drop your files here</p>
        <p className="mt-2 text-sm text-slate-500">PDF + DXF pairs are required for upload.</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label className="flex cursor-pointer flex-col rounded-3xl border border-slate-800 bg-slate-950/70 px-4 py-6 text-left transition hover:border-cyan-400/80">
            <span className="text-sm font-medium text-slate-400">PDF File</span>
            <span className="mt-4 text-base font-semibold text-white">{pdfFile?.name ?? 'No file selected'}</span>
            <input type="file" accept="application/pdf" className="sr-only" onChange={onFileSelect(setPdfFile)} />
          </label>
          <label className="flex cursor-pointer flex-col rounded-3xl border border-slate-800 bg-slate-950/70 px-4 py-6 text-left transition hover:border-cyan-400/80">
            <span className="text-sm font-medium text-slate-400">DXF File</span>
            <span className="mt-4 text-base font-semibold text-white">{dxfFile?.name ?? 'No file selected'}</span>
            <input type="file" accept=".dxf" className="sr-only" onChange={onFileSelect(setDxfFile)} />
          </label>
        </div>
      </div>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={handleUpload}
          disabled={isUploading}
          className="inline-flex items-center justify-center rounded-3xl bg-cyan-500 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isUploading ? 'Uploading…' : 'Upload Files'}
        </button>
        <div className="text-sm text-slate-400">
          {pdfFile ? `PDF ready: ${pdfFile.name}` : 'Select a PDF file'}
          <span className="mx-3">•</span>
          {dxfFile ? `DXF ready: ${dxfFile.name}` : 'Select a DXF file'}
        </div>
      </div>

      {isUploading && (
        <div className="mb-6 rounded-2xl bg-slate-950/80 p-4 text-sm text-slate-300">
          <div className="mb-3 flex items-center justify-between text-slate-300">
            <span>Upload progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-cyan-400" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {statusMessage && (
        <div
          className={`rounded-2xl border px-4 py-3 text-sm ${
            statusType === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
              : statusType === 'error'
              ? 'border-rose-500/30 bg-rose-500/10 text-rose-200'
              : 'border-slate-800 bg-slate-950/70 text-slate-300'
          }`}
        >
          {statusMessage}
        </div>
      )}
    </div>
  );
};

export default ComparePage;
