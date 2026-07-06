import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, Circle, Download, File, FileText, Trash2 } from 'lucide-react';
import {
  compareUpload,
  deleteUpload,
  downloadUploadDxf,
  downloadUploadPdf,
  fetchComparisonResult,
  fetchUploadById,
  fetchParsedDxfEntities,
  fetchParsedPdf,
  parseUploadDxf,
  parseUploadPdf,
} from '../../services/backendService';
import { formatDateTime } from '../../utils/formatDate';

const UploadDetailsPage = () => {
  const { uploadId } = useParams();
  const navigate = useNavigate();
  const [upload, setUpload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError] = useState('');
  const [parseResult, setParseResult] = useState(null);
  const [pdfParseLoading, setPdfParseLoading] = useState(false);
  const [pdfParseError, setPdfParseError] = useState('');
  const [pdfParseResult, setPdfParseResult] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');
  const [compareResult, setCompareResult] = useState(null);

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

    const loadParsedEntities = async () => {
      try {
        const parsed = await fetchParsedDxfEntities(uploadId);
        setParseResult({ summary: parsed.summary, entities: parsed.entities.map((entity) => entity.data) });
      } catch (err) {
        if (err?.response?.status !== 404) {
          setParseError('Unable to load previous parse results.');
        }
      }
    };

    const loadParsedPdf = async () => {
      try {
        const parsed = await fetchParsedPdf(uploadId);
        setPdfParseResult(parsed);
      } catch (err) {
        if (err?.response?.status !== 404) {
          setPdfParseError('Unable to load previous PDF parse results.');
        }
      }
    };

    const loadComparisonResult = async () => {
      try {
        const result = await fetchComparisonResult(uploadId);
        setCompareResult(result);
      } catch (err) {
        if (err?.response?.status !== 404) {
          setCompareError('Unable to load previous comparison results.');
        }
      }
    };

    loadUpload();
    loadParsedEntities();
    loadParsedPdf();
    loadComparisonResult();
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

  const handleParseDxf = async () => {
    if (!upload) return;

    setParseLoading(true);
    setParseError('');
    setParseResult(null);

    try {
      const response = await parseUploadDxf(upload.id);
      setParseResult(response.parsed);
    } catch (err) {
      setParseError(err?.response?.data?.detail || 'DXF parsing failed. Please try again.');
    } finally {
      setParseLoading(false);
    }
  };

  const handleParsePdf = async () => {
    if (!upload) return;

    setPdfParseLoading(true);
    setPdfParseError('');
    setPdfParseResult(null);

    try {
      const response = await parseUploadPdf(upload.id);
      setPdfParseResult(response.parsed);
    } catch (err) {
      setPdfParseError(err?.response?.data?.detail || 'PDF parsing failed. Please try again.');
    } finally {
      setPdfParseLoading(false);
    }
  };

  const handleStartComparison = async () => {
    if (!upload) return;

    setCompareLoading(true);
    setCompareError('');
    setCompareResult(null);

    try {
      const result = await compareUpload(upload.id);
      setCompareResult(result);
    } catch (err) {
      setCompareError(err?.response?.data?.detail || 'Comparison failed. Make sure both DXF and PDF are parsed first.');
    } finally {
      setCompareLoading(false);
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

        <div className="grid gap-6 lg:grid-cols-[1.75fr_1fr]">
          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Upload Information</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <span className="block text-sm text-slate-500">Upload ID</span>
                  <p className="mt-1 text-white">{upload.id}</p>
                </div>
                <div>
                  <span className="block text-sm text-slate-500">Upload Date</span>
                  <p className="mt-1 text-white">{formatDateTime(upload.created_at)}</p>
                </div>
                <div className="sm:col-span-2">
                  <span className="block text-sm text-slate-500">Status</span>
                  <p className="mt-1 text-emerald-300">Uploaded</p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Drawing Pair</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <div className="flex items-center gap-2 text-slate-500">
                    <FileText className="h-4 w-4 text-cyan-400" />
                    <span className="text-xs uppercase tracking-[0.2em]">PDF</span>
                  </div>
                  <p className="mt-2 truncate text-sm text-white" title={upload.pdf_filename}>{upload.pdf_filename}</p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <div className="flex items-center gap-2 text-slate-500">
                    <File className="h-4 w-4 text-emerald-400" />
                    <span className="text-xs uppercase tracking-[0.2em]">DXF</span>
                  </div>
                  <p className="mt-2 truncate text-sm text-white" title={upload.dxf_filename}>{upload.dxf_filename}</p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Progress Timeline</h3>
              <div className="mt-6 space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle className="mt-1 h-5 w-5 text-emerald-400" />
                  <div>
                    <p className="font-semibold text-white">Uploaded</p>
                    <p className="text-sm text-slate-500">The drawing pair is stored and ready for review.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className={`mt-1 h-5 w-5 ${parseResult ? 'text-emerald-400' : parseLoading ? 'text-yellow-400' : 'text-slate-500'}`} />
                  <div>
                    <p className="font-semibold text-white">DXF Parsing</p>
                    <p className="text-sm text-slate-500">
                      {parseLoading ? 'Parsing in progress' : parseResult ? 'Parsed successfully' : 'Ready to parse'}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className={`mt-1 h-5 w-5 ${pdfParseResult ? 'text-emerald-400' : pdfParseLoading ? 'text-yellow-400' : 'text-slate-500'}`} />
                  <div>
                    <p className="font-semibold text-white">PDF Parsing</p>
                    <p className="text-sm text-slate-500">
                      {pdfParseLoading ? 'Parsing in progress' : pdfParseResult ? 'Parsed successfully' : 'Ready to parse'}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className={`mt-1 h-5 w-5 ${compareResult ? 'text-emerald-400' : compareLoading ? 'text-yellow-400' : 'text-slate-500'}`} />
                  <div>
                    <p className="font-semibold text-white">Drawing Comparison</p>
                    <p className="text-sm text-slate-500">
                      {compareLoading
                        ? 'Comparison in progress'
                        : compareResult
                          ? `Completed — ${compareResult.accuracy}% accuracy`
                          : 'Ready to compare'}
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <Circle className="mt-1 h-5 w-5 text-slate-500" />
                  <div>
                    <p className="font-semibold text-white">Report Generation</p>
                    <p className="text-sm text-slate-500">Available in next milestone.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Comparison Results</h3>
              <div className="mt-6 space-y-4">
                <div>
                  <span className="block text-sm text-slate-500">Status</span>
                  <p className="text-white">
                    {compareLoading
                      ? 'Comparison in progress...'
                      : compareResult
                        ? 'Comparison completed'
                        : 'Not yet compared'}
                  </p>
                </div>
                {compareError ? (
                  <div className="rounded-2xl border border-rose-500 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {compareError}
                  </div>
                ) : null}
                 {compareResult ? (
                   <div className="space-y-6">
                     <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                       <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-center">
                         <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Accuracy</p>
                         <p className="mt-1 text-2xl font-bold text-emerald-400">{compareResult.accuracy}%</p>
                       </div>
                       <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-center">
                         <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Matched</p>
                         <p className="mt-1 text-2xl font-bold text-emerald-400">{compareResult.matched_count}</p>
                       </div>
                       <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-center">
                         <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Missing</p>
                         <p className="mt-1 text-2xl font-bold text-rose-400">{compareResult.missing_count}</p>
                       </div>
                       <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-center">
                         <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Extra</p>
                         <p className="mt-1 text-2xl font-bold text-amber-400">{compareResult.extra_count}</p>
                       </div>
                     </div>
                     {compareResult.geometry ? (
                       <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                         <div className="flex items-center justify-between">
                           <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">Geometry Comparison</h4>
                           <span className="text-sm text-emerald-300">{compareResult.geometry.accuracy}% accuracy</span>
                         </div>
                         <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                           {Object.entries(compareResult.geometry.entity_types || {}).map(([type, data]) => (
                             <div key={type} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                               <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{type}</p>
                               <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                                 <div>
                                   <span className="block text-slate-500">Matched</span>
                                   <p className="text-lg font-semibold text-emerald-400">{data.matched_count}</p>
                                 </div>
                                 <div>
                                   <span className="block text-slate-500">Missing</span>
                                   <p className="text-lg font-semibold text-rose-400">{data.missing_count}</p>
                                 </div>
                                 <div>
                                   <span className="block text-slate-500">Extra</span>
                                   <p className="text-lg font-semibold text-amber-400">{data.extra_count}</p>
                                 </div>
                                 <div>
                                   <span className="block text-slate-500">Changed</span>
                                   <p className="text-lg font-semibold text-violet-400">{data.changed_count}</p>
                                 </div>
                               </div>
                             </div>
                           ))}
                         </div>
                       </div>
                     ) : null}
                   </div>
                 ) : (
                  <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/60 p-8 text-center text-sm text-slate-500">
                    Run a comparison to see accuracy metrics and entity counts.
                  </div>
                )}
                {compareResult ? (
                  <div>
                    <span className="block text-sm text-slate-500">Status</span>
                    <p className="font-semibold text-emerald-300">{compareResult.status}</p>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">Actions</h3>
              <div className="mt-6 flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleParseDxf}
                  disabled={parseLoading}
                  className="rounded-3xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-white hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {parseLoading ? 'Parsing DXF…' : 'Parse DXF'}
                </button>
                <button
                  type="button"
                  onClick={handleParsePdf}
                  disabled={pdfParseLoading}
                  className="rounded-3xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-white hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {pdfParseLoading ? 'Parsing PDF…' : 'Parse PDF'}
                </button>
                <button
                  type="button"
                  onClick={handleStartComparison}
                  disabled={compareLoading || (!parseResult && !pdfParseResult)}
                  className="rounded-3xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {compareLoading ? 'Comparing…' : 'Start Comparison'}
                </button>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">DXF Parsing Status</h3>
              <div className="mt-6 space-y-4 text-sm text-slate-400">
                <div>
                  <span className="block text-sm text-slate-500">Status</span>
                  <p className="text-white">
                    {parseLoading
                      ? 'Parsing in progress...'
                      : parseResult
                        ? 'Parsed successfully'
                        : 'Not yet parsed'}
                  </p>
                </div>
                {parseError ? (
                  <div className="rounded-2xl border border-rose-500 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {parseError}
                  </div>
                ) : null}
                {parseResult ? (
                  <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                    <div>
                      <span className="block text-sm text-slate-500">Total Entities</span>
                      <p className="text-white">
                {compareResult?.categories ? (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-6">
                    <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">Category Breakdown</h4>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      {Object.entries(compareResult.categories).map(([cat, data]) => {
                        const displayName = cat.replace('_', ' ').toUpperCase();
                        return (
                          <div key={cat} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{displayName}</p>
                            <p className="mt-1 text-xl font-bold text-cyan-300">{data.accuracy}% Accuracy</p>
                            <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
                              <div>
                                <span className="block text-slate-500">Match</span>
                                <p className="font-semibold text-emerald-400">{data.matched_count}</p>
                              </div>
                              <div>
                                <span className="block text-slate-500">Miss</span>
                                <p className="font-semibold text-rose-400">{data.missing_count}</p>
                              </div>
                              <div>
                                <span className="block text-slate-500">Extra</span>
                                <p className="font-semibold text-amber-400">{data.extra_count}</p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}

                {compareResult?.risk_locations && compareResult.risk_locations.length > 0 ? (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                    <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-400">Detected Risk Locations (Discrepancies)</h4>
                    <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                      {compareResult.risk_locations.map((risk, index) => {
                        const severityColors = {
                          high: 'border-rose-500/20 bg-rose-500/10 text-rose-400',
                          medium: 'border-amber-500/20 bg-amber-500/10 text-amber-400',
                          low: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400',
                        };
                        const catColors = {
                          geometry: 'bg-yellow-500/20 text-yellow-300',
                          dimensions: 'bg-orange-500/20 text-orange-300',
                          annotations: 'bg-blue-500/20 text-blue-300',
                          title_block: 'bg-red-500/20 text-red-300',
                        };
                        return (
                          <div key={index} className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-slate-950/40 border-slate-800`}>
                            <div className="space-y-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${catColors[risk.category] || 'bg-slate-800 text-slate-300'}`}>
                                  {risk.category?.replace('_', ' ')}
                                </span>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${severityColors[risk.severity] || 'bg-slate-800'}`}>
                                  {risk.severity} Severity
                                </span>
                                <span className="text-[10px] text-slate-500">
                                  {risk.confidence}% Confidence
                                </span>
                              </div>
                              <p className="text-sm text-slate-200 mt-1">{risk.description}</p>
                              {risk.bbox ? (
                                <p className="text-[11px] text-slate-500 mt-1">
                                  Location: Page {risk.page || 1}, Box: [{risk.bbox.map(v => Math.round(v)).join(', ')}]
                                </p>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : compareResult ? (
                  <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/60 p-6 text-center text-sm text-emerald-400">
                    No mismatches or risk locations detected! Drawings match within threshold.
                  </div>
                ) : null}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-white">PDF Parsing Status</h3>
              <div className="mt-6 space-y-4 text-sm text-slate-400">
                <div>
                  <span className="block text-sm text-slate-500">Status</span>
                  <p className="text-white">
                    {pdfParseLoading
                      ? 'Parsing in progress...'
                      : pdfParseResult
                        ? 'Parsed successfully'
                        : 'Not yet parsed'}
                  </p>
                </div>
                {pdfParseError ? (
                  <div className="rounded-2xl border border-rose-500 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {pdfParseError}
                  </div>
                ) : null}
                {pdfParseResult ? (
                  <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                    <div>
                      <span className="block text-sm text-slate-500">Number of Pages</span>
                      <p className="text-white">{pdfParseResult.page_count}</p>
                    </div>
                    <div>
                      <span className="block text-sm text-slate-500">Text Block Count</span>
                      <p className="text-white">{pdfParseResult.text_block_count}</p>
                    </div>
                    <div>
                      <span className="block text-sm text-slate-500">Total Text Count</span>
                      <p className="text-white">{pdfParseResult.total_text_count}</p>
                    </div>
                    <div>
                      <span className="block text-sm text-slate-500">Metadata Available</span>
                      <p className="text-white">
                        {pdfParseResult.metadata && Object.values(pdfParseResult.metadata).some(Boolean)
                          ? 'Yes'
                          : 'No'}
                      </p>
                    </div>
                    {pdfParseResult.ocr ? (
                      <>
                        <div>
                          <span className="block text-sm text-slate-500">OCR Completion</span>
                          <p className="text-white">
                            {pdfParseResult.ocr.status === 'completed'
                              ? 'Completed'
                              : pdfParseResult.ocr.status === 'unavailable'
                                ? 'Unavailable'
                                : pdfParseResult.ocr.status === 'failed'
                                  ? 'Failed'
                                  : 'Not run'}
                          </p>
                          {pdfParseResult.ocr.status !== 'completed' && pdfParseResult.ocr.error ? (
                            <p className="mt-1 text-xs text-rose-400">{pdfParseResult.ocr.error}</p>
                          ) : null}
                        </div>
                        <div>
                          <span className="block text-sm text-slate-500">Pages Processed</span>
                          <p className="text-white">{pdfParseResult.ocr.pages?.length || 0}</p>
                        </div>
                        <div>
                          <span className="block text-sm text-slate-500">Total OCR Text Blocks</span>
                          <p className="text-white">{pdfParseResult.ocr.text_block_count || 0}</p>
                        </div>
                      </>
                    ) : null}
                  </div>
                ) : null}
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

            <div className="rounded-3xl border border-rose-500/20 bg-slate-950/70 p-6">
              <h3 className="text-lg font-semibold text-rose-300">Danger Zone</h3>
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
