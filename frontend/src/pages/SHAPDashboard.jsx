import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getShapExplanations, getDiseases } from '../services/api';
import { FaArrowLeft, FaCircleInfo, FaCheck } from 'react-icons/fa6';

// Plain-language translation (08-FRONTEND-UI-SPEC §3 SHAP screen): raw feature names user ko
// nahi dikhane — "family_diabetes" → "Family history of diabetes"
const FEATURE_LABELS = {
  age: 'Age',
  gender: 'Gender',
  bmi: 'BMI (body mass index)',
  sleep_hours: 'Sleep hours per night',
  exercise_level: 'Exercise level',
  smoking: 'Smoking',
  alcohol: 'Alcohol (drinks/week)',
  family_diabetes: 'Family history of diabetes',
  family_heart: 'Family history of heart disease',
  family_hypertension: 'Family history of hypertension',
  family_cancer: 'Family history of cancer',
};
const featureLabel = (name) => FEATURE_LABELS[name] || name;

function ShapBar({ feature, shapValue, direction }) {
  const width = Math.min(Math.abs(shapValue) * 100, 100);
  const color = direction === 'increases_risk' ? '#F44336' : '#66BB6A';
  const bgColor = direction === 'increases_risk' ? 'rgba(244,67,54,0.1)' : 'rgba(102,187,106,0.1)';

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-300">{featureLabel(feature)}</span>
        <span className="text-xs font-mono" style={{ color }}>
          {shapValue > 0 ? '+' : ''}{shapValue.toFixed(4)}
        </span>
      </div>
      <div className="relative h-6 rounded-lg overflow-hidden" style={{ background: bgColor }}>
        <div
          className="absolute top-0 h-full rounded-lg transition-all duration-700"
          style={{
            width: `${width}%`,
            backgroundColor: color,
            opacity: 0.7,
            left: direction === 'decreases_risk' ? `${100 - width}%` : '0',
          }}
        />
      </div>
    </div>
  );
}

export default function SHAPDashboard() {
  const { predictionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [diseaseLabels, setDiseaseLabels] = useState({});
  const [selected, setSelected] = useState(''); // '' = All

  useEffect(() => {
    getDiseases()
      .then((res) => {
        const map = {};
        (res.data?.diseases || []).forEach((d) => { map[d.disease_key] = d.label; });
        setDiseaseLabels(map);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    async function fetch() {
      try {
        const res = await getShapExplanations(predictionId);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load SHAP explanations');
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [predictionId]);

  if (loading) {
    return (
      <div className="pt-24 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="pt-24 text-center min-h-screen px-4">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate('/dashboard')} className="btn-primary mt-4">Back to Dashboard</button>
      </div>
    );
  }

  const allExplanations = data?.explanations || [];
  const diseases = [...new Set(allExplanations.map((e) => e.disease).filter(Boolean))];
  const explanations = selected ? allExplanations.filter((e) => e.disease === selected) : allExplanations;
  const increasing = explanations.filter((e) => e.direction === 'increases_risk').slice(0, 8);
  const decreasing = explanations.filter((e) => e.direction === 'decreases_risk').slice(0, 8);
  const diseaseLabel = (key) => diseaseLabels[key] || (key ? key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'All Diseases');

  return (
    <div className="pt-20 pb-12 px-4 max-w-4xl mx-auto">
      <div className="animate-slide-up">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
        >
          <FaArrowLeft size={18} /> Back to Dashboard
        </button>

        <h1 className="font-display text-3xl font-bold text-white mb-2">SHAP Explainability</h1>
        <p className="text-gray-400 mb-6">
          Understanding what drives your health risk predictions
        </p>

        {/* Info Banner */}
        <div className="glass-light p-4 flex items-start gap-3 mb-6">
          <FaCircleInfo className="text-primary-300 shrink-0 mt-0.5" size={18} />
          <div className="text-sm text-gray-400">
            <p>
              <strong className="text-gray-300">SHAP (SHapley Additive exPlanations)</strong> shows
              how each factor contributes to your risk prediction. Features with{' '}
              <span className="text-red-400">red bars increase risk</span>, while{' '}
              <span className="text-green-400">green bars decrease risk</span>.
            </p>
          </div>
        </div>

        {explanations.length === 0 ? (
          <div className="glass p-8 text-center">
            <p className="text-gray-400">No SHAP explanations available for this prediction.</p>
          </div>
        ) : (
          <>
            {diseases.length > 1 && (
              <div className="mb-6">
                <label className="block text-sm text-gray-400 mb-2" htmlFor="shap-disease">
                  Show explanations for
                </label>
                <select
                  id="shap-disease"
                  className="w-full md:w-72 glass px-4 py-2 rounded-lg text-gray-200 bg-gray-900/60 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  <option value="">All diseases</option>
                  {diseases.map((d) => (
                    <option key={d} value={d}>{diseaseLabel(d)}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-xl font-semibold text-white">{diseaseLabel(selected)}</h2>
              <span className="text-xs text-gray-500">{explanations.length} factors</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Risk Increasing Factors */}
            {increasing.length > 0 && (
              <div className="glass p-6">
                <h3 className="text-lg font-semibold text-red-400 mb-4 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500" />
                  Factors Increasing Risk
                </h3>
                {increasing.map((item, i) => (
                  <ShapBar
                    key={i}
                    feature={item.feature}
                    shapValue={item.shap_value}
                    direction="increases_risk"
                  />
                ))}
              </div>
            )}

            {/* Risk Decreasing Factors */}
            {decreasing.length > 0 && (
              <div className="glass p-6">
                <h3 className="text-lg font-semibold text-green-400 mb-4 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-green-500" />
                  Factors Decreasing Risk
                </h3>
                {decreasing.map((item, i) => (
                  <ShapBar
                    key={i}
                    feature={item.feature}
                    shapValue={item.shap_value}
                    direction="decreases_risk"
                  />
                ))}
              </div>
            )}
            </div>
          </>
        )}

        {/* Top 5 Plain Language Summary */}
        <div className="glass p-6 mt-6">
          <h3 className="text-lg font-semibold text-white mb-4">Key Insights</h3>
          <div className="space-y-3">
            {increasing.slice(0, 5).map((item, i) => (
              <div key={i} className="flex items-start gap-3 glass-light p-3">
                <span className="text-red-400 font-bold text-lg">{i + 1}</span>
                <div>
                  <p className="text-sm text-gray-300">
                    <strong className="text-white">{featureLabel(item.feature)}</strong> is increasing your overall risk.
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    SHAP value: +{item.shap_value.toFixed(4)}
                  </p>
                </div>
              </div>
            ))}
            {decreasing.slice(0, 3).map((item, i) => (
              <div key={`dec-${i}`} className="flex items-start gap-3 glass-light p-3">
                <span className="text-green-400 text-lg shrink-0"><FaCheck size={18} aria-hidden="true" /></span>
                <div>
                  <p className="text-sm text-gray-300">
                    <strong className="text-white">{featureLabel(item.feature)}</strong> is helping lower your risk.
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    SHAP value: {item.shap_value.toFixed(4)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
