import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { generateReport, getReportStatus, listReports, downloadReport } from '../services/api';
import { FaDownload, FaFileLines, FaArrowsRotate } from 'react-icons/fa6';

function downloadBlob(blob, name) {
  const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  window.URL.revokeObjectURL(url);
}

export default function Reports() {
  const { user } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState('');

  const load = async () => {
    if (!user) return;
    try {
      const res = await listReports(user.id);
      setReports(res.data?.reports || []);
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleGenerate = async () => {
    if (!user) return;
    setGenerating(true);
    setMessage('');
    try {
      const res = await generateReport(user.id);
      const reportId = res.data.report_id;
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await getReportStatus(reportId);
          if (statusRes.data.status === 'success') {
            clearInterval(interval);
            setGenerating(false);
            setMessage('Report ready!');
            await load();
          } else if (attempts > 30 || statusRes.data.status === 'failed') {
            clearInterval(interval);
            setGenerating(false);
            setMessage(statusRes.data.status === 'failed' ? 'Report generation failed.' : 'Timed out.');
          }
        } catch {
          clearInterval(interval);
          setGenerating(false);
        }
      }, 1000);
    } catch (err) {
      setGenerating(false);
      setMessage(err.response?.data?.detail || 'Could not start report generation.');
    }
  };

  const handleDownload = async (reportId) => {
    try {
      const res = await downloadReport(reportId);
      downloadBlob(res.data, `health_report_${reportId}.pdf`);
    } catch {
      setMessage('Download failed — report may not be ready.');
    }
  };

  return (
    <div className="pt-20 pb-12 px-4 max-w-4xl mx-auto">
      <div className="animate-slide-up">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
          <div>
            <h1 className="font-display text-3xl font-bold text-white mb-2">Reports</h1>
            <p className="text-gray-400">Generate and download your personalized PDF health reports</p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {generating ? (
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            ) : (
              <FaArrowsRotate size={16} />
            )}
            {generating ? 'Generating...' : 'Generate New Report'}
          </button>
        </div>

        {message && (
          <div className="glass-light p-3 mb-4 text-sm text-primary-300" role="status">{message}</div>
        )}

        {loading ? (
          <div className="glass p-8 flex justify-center">
            <div className="w-10 h-10 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
          </div>
        ) : reports.length === 0 ? (
          <div className="glass p-8 text-center text-gray-400">
            <FaFileLines size={28} className="mx-auto mb-3 text-gray-600" />
            No reports yet. Generate one to download your PDF health report.
          </div>
        ) : (
          <div className="glass overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-white/5">
                  <th className="px-4 py-3 font-medium">Report</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Size</th>
                  <th className="px-4 py-3 font-medium">Generated</th>
                  <th className="px-4 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} className="border-b border-white/5 last:border-0">
                    <td className="px-4 py-3 text-white">#{r.id}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        r.status === 'success'
                          ? 'bg-green-500/10 text-green-400'
                          : r.status === 'failed'
                          ? 'bg-red-500/10 text-red-400'
                          : 'bg-yellow-500/10 text-yellow-400'
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {r.file_size_kb ? `${r.file_size_kb} KB` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {r.generated_at ? new Date(r.generated_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDownload(r.id)}
                        disabled={!r.downloadable}
                        className="inline-flex items-center gap-1 text-primary-300 hover:text-primary-200 disabled:text-gray-600 disabled:cursor-not-allowed"
                      >
                        <FaDownload size={15} /> Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
