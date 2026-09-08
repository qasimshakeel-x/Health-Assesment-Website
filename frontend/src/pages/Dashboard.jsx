import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getLatestPrediction, generateReport, getReportStatus, downloadReport } from '../services/api';
import { FiDownload, FiMessageCircle, FiAlertTriangle, FiArrowRight } from 'react-icons/fi';

function RiskGauge({ label, value, color }) {
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
          <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
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
          <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
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

  return (
    <div className="glass p-6">
      <h3 className="text-sm text-gray-400 mb-2">Depression Screening</h3>
      <p className="text-xl font-bold mb-1" style={{ color }}>{level}</p>
      <p className="text-sm text-gray-500">Confidence: {Math.round((confidence || 0) * 100)}%</p>
      {isSevere && (
        <div className="mt-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <p className="text-xs text-red-400 font-medium">
            ⚠️ Please consider reaching out to a mental health professional.
          </p>
          <p className="text-xs text-red-400/70 mt-1">📞 Crisis helpline: Call or text 988 (US)</p>
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
  const [loading, setLoading] = useState(true);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  useEffect(() => {
    async function fetch() {
      try {
        if (!user) return;
        const res = await getLatestPrediction(user.id);
        setData(res.data);
      } catch {
        navigate('/');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [user, navigate]);

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

  const hasHighRisk =
    data.diabetes_risk > 60 || data.heart_risk > 60 ||
    data.hypertension_risk > 60 || data.obesity_risk > 60;

  return (
    <div className="pt-20 pb-12 px-4 max-w-6xl mx-auto">
      <div className="animate-slide-up">
        <h1 className="font-display text-3xl font-bold text-white mb-2">Health Dashboard</h1>
        <p className="text-gray-400 mb-6">Your AI-powered health analysis results</p>

        {/* High Risk Warning */}
        {hasHighRisk && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 mb-6 flex items-start gap-3">
            <FiAlertTriangle className="text-yellow-500 shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-yellow-400 font-medium">Elevated Risk Detected</p>
              <p className="text-sm text-yellow-400/70 mt-1">
                This is an AI prediction, not a medical diagnosis. Consult a qualified doctor for proper evaluation.
              </p>
            </div>
          </div>
        )}

        {/* Risk Gauges */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <RiskGauge label="Diabetes" value={data.diabetes_risk} />
          <RiskGauge label="Heart Disease" value={data.heart_risk} />
          <RiskGauge label="Hypertension" value={data.hypertension_risk} />
          <RiskGauge label="Obesity" value={data.obesity_risk} />
        </div>

        {/* Bio Age + Longevity + Depression */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <BioAgeCard biologicalAge={data.biological_age} chronologicalAge={data.age || 30} />
          <LongevityScore score={data.longevity_score} />
          <DepressionCard level={data.depression_level} confidence={data.depression_confidence} />
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button
            onClick={handleDownloadPdf}
            disabled={generatingPdf}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group disabled:opacity-50"
          >
            {generatingPdf ? (
              <div className="w-5 h-5 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
            ) : (
              <FiDownload className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            )}
            <span className="text-white font-medium">{generatingPdf ? 'Generating...' : 'Download PDF Report'}</span>
          </button>

          <button
            onClick={() => navigate('/chat')}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group"
          >
            <FiMessageCircle className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            <span className="text-white font-medium">Diet Advisor Chat</span>
          </button>

          <button
            onClick={() => navigate(`/shap/${data.id}`)}
            className="glass p-4 flex items-center justify-center gap-3 hover:bg-surface-100 transition-all group"
          >
            <FiArrowRight className="text-primary-300 group-hover:scale-110 transition-transform" size={20} />
            <span className="text-white font-medium">View SHAP Explanations</span>
          </button>
        </div>
      </div>
    </div>
  );
}
