import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getLatestPrediction, getPredictionHistory, generateReport, getReportStatus, downloadReport } from '../services/api';
import { FaDownload, FaCommentDots, FaTriangleExclamation, FaArrowRight, FaChevronDown, FaClock, FaPhone } from 'react-icons/fa6';

// WS-5: 16 disease cards grouped into the 5 dashboard categories (06-DISEASE-MODULES §table)
const CATEGORY_ORDER = ['cardiovascular', 'metabolic', 'mental_wellness', 'lifestyle_linked', 'cancer_screening'];
const CATEGORY_LABELS = {
  cardiovascular: 'Cardiovascular',
  metabolic: 'Metabolic',
  mental_wellness: 'Mental Wellness',
  lifestyle_linked: 'Lifestyle-Linked',
  cancer_screening: 'Cancer Screening',
};
// 06 Phase 5: cancer screening cards pe stricter disclaimer hamesha visible (hover pe nahi)
const CANCER_DISCLAIMER = 'Population-level risk estimate, not a diagnostic tool.';

function RiskGauge({ label, value, note }) {
  const riskLevel = value < 25 ? 'Low' : value < 50 ? 'Moderate' : value < 75 ? 'High' : 'Very High';
  const riskColor = value < 25 ? '#66BB6A' : value < 50 ? '#FFC107' : value < 75 ? '#FF9800' : '#F44336';
  const bgGrad = value < 25
    ? 'from-green-500/20 to-green-600/5'
    : value < 50
    ? 'from-yellow-500/20 to-yellow-600/5'
    : value < 75
    ? 'from-orange-500/20 to-orange-600/5'
    : 'from-red-500/20 to-red-600/5';

  return (
    <div className={`glass p-5 bg-gradient-to-br ${bgGrad}`}>
      <p className="text-sm text-gray-400 mb-2">{label}</p>
      <div className="relative w-28 h-28 mx-auto mb-3">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" className="gauge-track" strokeWidth="8" />
          <circle
            cx="50" cy="50" r="42" fill="none"
            stroke={riskColor}
            strokeWidth="8"
            strokeDasharray={`${(value / 100) * 264} 264`}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-white">{Math.round(value)}%</span>
        </div>
      </div>
      <p className="text-center text-sm font-medium" style={{ color: riskColor }}>{riskLevel} Risk</p>
      {note && (
        <p className="text-[11px] leading-snug text-yellow-400/80 mt-2 text-center border-t border-yellow-500/20 pt-2">
          {note}
        </p>
      )}
    </div>
  );
}

// Collapsible category section — 16 cards ko 5 groups mein toorna (08-FRONTEND §Dashboard).
// Elevated (Moderate+ = risk >= 25) wale categories default mein khule, baaki band.
function RiskCategorySection({ categoryKey, diseases }) {
  const maxRisk = diseases.reduce((m, d) => Math.max(m, d.risk_percent || 0), 0);
  const [open, setOpen] = useState(maxRisk >= 25);
  const isCancer = categoryKey === 'cancer_screening';

  return (
    <div className="glass overflow-hidden mb-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
      >
        <span className="flex items-center gap-3">
          <span className="text-white font-semibold">{CATEGORY_LABELS[categoryKey] || categoryKey}</span>
          <span className="text-xs text-gray-500">
            {diseases.length} {diseases.length === 1 ? 'check' : 'checks'}
            {maxRisk > 0 && ` · peak ${Math.round(maxRisk)}%`}
          </span>
        </span>
        <span className="flex items-center gap-3">
          {maxRisk >= 60 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400">Elevated</span>
          )}
          <FaChevronDown
            size={18}
            className={`text-gray-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          />
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {diseases.map((d) => (
            <RiskGauge
              key={d.disease_key}
              label={d.label || d.disease_key}
              value={d.risk_percent || 0}
              note={isCancer ? CANCER_DISCLAIMER : (d.disclaimer || null)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function BioAgeCard({ biologicalAge, chronologicalAge }) {
  const diff = biologicalAge - chronologicalAge;
  const isWorse = diff > 0;

  return (
    <div className="glass p-6">
      <h3 className="text-sm text-gray-400 mb-4">Biological Age</h3>
      <div className="flex items-center justify-center gap-6">
        <div className="text-center">
          <p className="text-3xl font-bold text-white">{Math.round(biologicalAge)}</p>
          <p className="text-xs text-gray-500 mt-1">Bio Age</p>
        </div>
        <div className={`text-center px-4 py-2 rounded-xl ${isWorse ? 'bg-red-500/10' : 'bg-green-500/10'}`}>
          <p className={`text-lg font-bold ${isWorse ? 'text-red-400' : 'text-green-400'}`}>
            {isWorse ? '+' : ''}{Math.round(diff)}
          </p>
          <p className="text-xs text-gray-500">years</p>
        </div>
        <div className="text-center">
          <p className="text-3xl font-bold text-gray-500">{chronologicalAge}</p>
          <p className="text-xs text-gray-500 mt-1">Actual Age</p>
        </div>
      </div>
    </div>
  );
}

function LongevityScore({ score }) {
  const category = score < 40 ? 'Poor' : score < 60 ? 'Moderate' : score < 80 ? 'Good' : 'Excellent';
  const catColor = score < 40 ? '#F44336' : score < 60 ? '#FFC107' : score < 80 ? '#66BB6A' : '#2E7D32';
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="glass p-6">
      <h3 className="text-sm text-gray-400 mb-4">Longevity Score</h3>
      <div className="relative w-32 h-32 mx-auto mb-3">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="45" fill="none" className="gauge-track" strokeWidth="6" />
          <circle
            cx="50" cy="50" r="45" fill="none"
            stroke={catColor}
            strokeWidth="6"
            strokeDasharray={`${circumference}`}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-white">{Math.round(score)}</span>
          <span className="text-xs text-gray-500">/100</span>
        </div>
      </div>
      <p className="text-center text-sm font-medium" style={{ color: catColor }}>{category}</p>
    </div>
  );
}

function DepressionCard({ level, confidence }) {
  const levelColors = {
    'No Depression': '#66BB6A',
    'Mild': '#81C784',
    'Moderate': '#FFC107',
    'Moderately Severe': '#FF9800',
    'Severe': '#F44336',
  };
  const color = levelColors[level] || '#9e9e9e';
  const isSevere = level === 'Severe' || level === 'Moderately Severe';
  // Backend confidence tiny percent (0-100) mein bhejta hai (depression.py `*100`) —
  // pehle yahan dobara ×100 ho jata tha (7720% bug). >1 ho to already percent hai.
  const confPct = confidence == null ? 0 : confidence > 1 ? confidence : confidence * 100;

  return (
    <div className="glass p-6">
      <h3 className="text-sm text-gray-400 mb-2">Depression Screening</h3>
      <p className="text-xl font-bold mb-1" style={{ color }}>{level}</p>
      <p className="text-sm text-gray-500">Confidence: {Math.round(confPct)}%</p>
      {isSevere && (
        <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <p className="text-xs text-red-400 font-medium flex items-center gap-1.5">
            <FaTriangleExclamation className="shrink-0" size={13} aria-hidden="true" />
            Please consider reaching out to a mental health professional.
          </p>
          <p className="text-xs text-red-400/70 mt-1 flex items-center gap-1.5">
            <FaPhone className="shrink-0" size={12} aria-hidden="true" />
            Crisis helpline: Call or text 988 (US)
          </p>
        </div>
      )}
      <p className="text-xs text-gray-600 mt-3 italic">
        This tool does not diagnose depression. It estimates risk only.
      </p>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [latestData, setLatestData] = useState(null);
  const [latestId, setLatestId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    async function fetch() {
      try {
        if (!user) return;
        const res = await getLatestPrediction(user.id);
        setData(res.data);
        setLatestData(res.data);
        setLatestId(res.data.id);
      } catch {
        navigate('/');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [user, navigate]);

  // Previous-Health: purani assessments ki list (Round 2). Ek item select karne pe wahi
  // prediction dashboard mein load ho jaati hai (SHAP link bhi usi id ka).
  const toggleHistory = async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (next && history.length === 0 && user) {
      setHistoryLoading(true);
      try {
        const res = await getPredictionHistory(user.id);
        setHistory(res.data?.predictions || []);
      } catch {
        setHistory([]);
      } finally {
        setHistoryLoading(false);
      }
    }
  };

  const peakRisk = (item) => {
    const rows = item.disease_risk_results || [];
    return rows.reduce((m, r) => Math.max(m, r.risk_percent || 0), 0);
  };

  const handleDownloadPdf = async () => {
    if (!user) return;
    setGeneratingPdf(true);
    try {
      const res = await generateReport(user.id);
      const reportId = res.data.report_id;
      // Poll for status
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await getReportStatus(reportId);
          if (statusRes.data.status === 'success') {
            clearInterval(interval);
            const pdfRes = await downloadReport(reportId);
            const url = window.URL.createObjectURL(new Blob([pdfRes.data], { type: 'application/pdf' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = `health_report_${reportId}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            setGeneratingPdf(false);
          } else if (attempts > 20 || statusRes.data.status === 'failed') {
            clearInterval(interval);
            setGeneratingPdf(false);
          }
        } catch {
          clearInterval(interval);
          setGeneratingPdf(false);
        }
      }, 1000);
    } catch {
      setGeneratingPdf(false);
    }
  };

  if (loading) {
    return (
      <div className="pt-24 flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-12 h-12 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading your results...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="pt-24 text-center min-h-screen">
        <p className="text-gray-400">No predictions found. Complete an assessment first.</p>
        <button onClick={() => navigate('/')} className="btn-primary mt-4">Start Assessment</button>
      </div>
    );
  }

  // WS-5: cards `disease_risk_results` array se (05-API-SPEC §9) — 16 diseases tak scale.
  // Purane predictions (array empty) pe flat columns se fallback taake UI toot na jaye.
  const riskRows =
    data.disease_risk_results && data.disease_risk_results.length
      ? data.disease_risk_results
      : [
          { disease_key: 'diabetes', label: 'Diabetes', category: 'metabolic', risk_percent: data.diabetes_risk || 0 },
          { disease_key: 'heart', label: 'Heart Disease', category: 'cardiovascular', risk_percent: data.heart_risk || 0 },
          { disease_key: 'hypertension', label: 'Hypertension', category: 'cardiovascular', risk_percent: data.hypertension_risk || 0 },
          { disease_key: 'obesity', label: 'Obesity', category: 'metabolic', risk_percent: data.obesity_risk || 0 },
        ];

  const byCategory = {};
  for (const row of riskRows) {
    const cat = CATEGORY_LABELS[row.category] ? row.category : 'metabolic';
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(row);
  }
  const orderedCategories = [
    ...CATEGORY_ORDER.filter((c) => byCategory[c]),
    ...Object.keys(byCategory).filter((c) => !CATEGORY_ORDER.includes(c)),
  ];

  const hasHighRisk = riskRows.some((r) => (r.risk_percent || 0) > 60);

  return (
    <div className="pt-20 pb-12 px-4 max-w-6xl mx-auto">
      <div className="animate-slide-up">
        <h1 className="font-display text-3xl font-bold text-white mb-2">Health Dashboard</h1>
        <p className="text-gray-400 mb-6">Your ML-powered health analysis results</p>

        {/* High Risk Warning */}
        {hasHighRisk && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 mb-6 flex items-start gap-3">
            <FaTriangleExclamation className="text-yellow-500 shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-yellow-400 font-medium">Elevated Risk Detected</p>
              <p className="text-sm text-yellow-400/70 mt-1">
                This is an ML prediction, not a medical diagnosis. Consult a qualified doctor for proper evaluation.
              </p>
            </div>
          </div>
        )}

        {/* 16 Disease Risk Cards — 5 category sections (WS-5) */}
        <div className="mb-6">
          {orderedCategories.map((cat) => (
            <RiskCategorySection
              key={cat}
              categoryKey={cat}
              diseases={byCategory[cat]}
            />
          ))}
        </div>

        {/* Bio Age + Longevity + Depression */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <BioAgeCard biologicalAge={data.biological_age} chronologicalAge={data.age || 30} />
          <LongevityScore score={data.longevity_score} />
          <DepressionCard level={data.depression_level} confidence={data.depression_confidence} />
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <button
            onClick={handleDownloadPdf}
            disabled={generatingPdf}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group disabled:opacity-50"
          >
            {generatingPdf ? (
              <div className="w-5 h-5 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
            ) : (
              <FaDownload className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            )}
            <span className="text-white font-medium">{generatingPdf ? 'Generating...' : 'Download PDF Report'}</span>
          </button>

          <button
            onClick={() => navigate('/chat')}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group"
          >
            <FaCommentDots className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            <span className="text-white font-medium">Diet Advisor Chat</span>
          </button>

          <button
            onClick={() => navigate(`/shap/${data.id}`)}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group"
          >
            <FaArrowRight className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            <span className="text-white font-medium">View SHAP Explanations</span>
          </button>

          <button
            onClick={toggleHistory}
            aria-expanded={showHistory}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group"
          >
            <FaClock className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            <span className="text-white font-medium">Previous Assessments</span>
          </button>
        </div>

        {/* Previous-Health history panel */}
        {showHistory && (
          <div className="glass mt-6 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Previous Assessments</h3>
              {data.id !== latestId && (
                <button
                  onClick={() => setData(latestData)}
                  className="text-xs text-primary-300 hover:text-primary-200"
                >
                  Back to latest
                </button>
              )}
            </div>
            {historyLoading ? (
              <div className="flex justify-center py-6">
                <div className="w-8 h-8 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
              </div>
            ) : history.length === 0 ? (
              <p className="text-gray-400 text-sm">No previous assessments found.</p>
            ) : (
              <div className="space-y-2">
                {history.map((h) => {
                  const isCurrent = h.id === data.id;
                  return (
                    <div
                      key={h.id}
                      className={`flex items-center justify-between gap-3 rounded-lg p-3 border ${
                        isCurrent ? 'border-primary-500/40 bg-primary-500/10' : 'border-white/5 hover:bg-white/5'
                      }`}
                    >
                      <button
                        onClick={() => setData(h)}
                        className="text-left flex-1"
                      >
                        <span className="text-sm text-white">
                          {h.created_at ? new Date(h.created_at).toLocaleString() : `Assessment #${h.id}`}
                          {h.id === latestId && <span className="ml-2 text-xs text-primary-300">Latest</span>}
                        </span>
                        <span className="block text-xs text-gray-500 mt-0.5">
                          Peak risk {Math.round(peakRisk(h))}%
                          {h.longevity_score != null && ` · Longevity ${Math.round(h.longevity_score)}/100`}
                        </span>
                      </button>
                      <button
                        onClick={() => navigate(`/shap/${h.id}`)}
                        className="text-xs text-primary-300 hover:text-primary-200 whitespace-nowrap inline-flex items-center gap-1"
                      >
                        SHAP
                        <FaArrowRight size={11} aria-hidden="true" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Server-side disclaimer (05-API-SPEC §8) — API se aata hai, frontend pe rely nahi */}
        {data.disclaimer && (
          <p className="text-xs text-gray-600 mt-6 text-center">{data.disclaimer}</p>
        )}
      </div>
    </div>
  );
}
