import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getShapExplanations } from '../services/api';
import { FiArrowLeft, FiInfo } from 'react-icons/fi';

function ShapBar({ feature, shapValue, direction }) {
  const width = Math.min(Math.abs(shapValue) * 100, 100);
  const color = direction === 'increases_risk' ? '#F44336' : '#66BB6A';
  const bgColor = direction === 'increases_risk' ? 'rgba(244,67,54,0.1)' : 'rgba(102,187,106,0.1)';

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-300">{feature}</span>
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

  const explanations = data?.explanations || [];
  const increasing = explanations.filter((e) => e.direction === 'increases_risk').slice(0, 8);
  const decreasing = explanations.filter((e) => e.direction === 'decreases_risk').slice(0, 8);

  return (
    <div className="pt-20 pb-12 px-4 max-w-4xl mx-auto">
      <div className="animate-slide-up">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
        >
          <FiArrowLeft size={18} /> Back to Dashboard
        </button>

        <h1 className="font-display text-3xl font-bold text-white mb-2">SHAP Explainability</h1>
        <p className="text-gray-400 mb-6">
          Understanding what drives your health risk predictions
        </p>

        {/* Info Banner */}
        <div className="glass-light p-4 flex items-start gap-3 mb-6">
          <FiInfo className="text-primary-300 shrink-0 mt-0.5" size={18} />
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
                    <strong className="text-white">{item.feature}</strong> is increasing your overall risk.
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    SHAP value: +{item.shap_value.toFixed(4)}
                  </p>
                </div>
              </div>
            ))}
            {decreasing.slice(0, 3).map((item, i) => (
              <div key={`dec-${i}`} className="flex items-start gap-3 glass-light p-3">
                <span className="text-green-400 font-bold text-lg">✓</span>
                <div>
                  <p className="text-sm text-gray-300">
                    <strong className="text-white">{item.feature}</strong> is helping lower your risk.
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
