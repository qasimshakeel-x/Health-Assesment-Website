import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { simulateFuture } from '../services/api';
import { FaArrowLeft, FaArrowRight, FaPlay, FaCheck, FaSmoking } from 'react-icons/fa6';

function SliderInput({ label, value, onChange, min, max, step = 1, unit = '', suffix = '' }) {
  const percentage = ((value - min) / (max - min)) * 100;
  return (
    <div className="mb-5">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-gray-300">{label}</span>
        <span className="text-sm font-semibold text-primary-300">
          {value}{unit}{suffix}
        </span>
      </div>
      <div className="relative">
        <div className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-primary-500/20 w-full" />
        <div
          className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-primary-500"
          style={{ width: `${percentage}%` }}
        />
        <input
          type="range"
          min={min} max={max} step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="relative z-10 w-full"
        />
      </div>
      <div className="flex justify-between text-xs text-gray-600 mt-1">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

function ComparisonCard({ title, current, improved, unit = '', lowerBetter = true }) {
  const improved_ = improved ?? current;
  const diff = improved_ - current;
  const isBetter = lowerBetter ? diff < 0 : diff > 0;

  return (
    <div className="glass-light p-4">
      <p className="text-xs text-gray-500 mb-2">{title}</p>
      <div className="flex items-center gap-4">
        <div>
          <p className="text-xl font-bold text-white">{typeof current === 'number' ? current.toFixed(1) : current}{unit}</p>
          <p className="text-xs text-gray-500">Current</p>
        </div>
        <div className="text-gray-600"><FaArrowRight size={16} aria-hidden="true" /></div>
        <div>
          <p className={`text-xl font-bold ${isBetter ? 'text-green-400' : diff === 0 ? 'text-gray-400' : 'text-red-400'}`}>
            {typeof improved_ === 'number' ? improved_.toFixed(1) : improved_}{unit}
          </p>
          <p className="text-xs text-gray-500">Projected</p>
        </div>
        {diff !== 0 && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${isBetter ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {diff > 0 ? '+' : ''}{typeof diff === 'number' ? diff.toFixed(1) : diff}{unit}
          </span>
        )}
      </div>
    </div>
  );
}

// WS-5: 16-disease comparison rows (current → projected), backend `current.diseases` se
function DiseaseComparisonRow({ label, current, improved }) {
  const base = current ?? 0;
  const proj = improved ?? base;
  const diff = proj - base;
  const isBetter = diff < 0;
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-b-0">
      <span className="text-sm text-gray-300 truncate pr-3">{label}</span>
      <span className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-gray-500 w-11 text-right">{Math.round(base)}%</span>
        <span className="text-gray-600"><FaArrowRight size={12} aria-hidden="true" /></span>
        <span
          className={`text-xs font-semibold w-11 text-right ${
            diff === 0 ? 'text-gray-400' : isBetter ? 'text-green-400' : 'text-red-400'
          }`}
        >
          {Math.round(proj)}%
        </span>
        <span
          className={`text-[10px] w-12 text-right ${
            diff === 0 ? 'text-gray-600' : isBetter ? 'text-green-500/80' : 'text-red-400/80'
          }`}
        >
          {diff === 0 ? '—' : `${diff > 0 ? '+' : ''}${Math.round(diff)}`}
        </span>
      </span>
    </div>
  );
}

export default function Simulator() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isDemo, setIsDemo] = useState(false);
  const [params, setParams] = useState({
    years: 10,
    sleep_hours_delta: 0,
    exercise_level_delta: 0,
    smoking_quit: false,
    bmi_improvement: 0,
    diet_improvement: 'none',
  });

  const update = (key, val) => setParams((prev) => ({ ...prev, [key]: val }));

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    setIsDemo(false);
    try {
      const res = await simulateFuture(params);
      setResult(res.data);
    } catch (err) {
      // Backend down → demo estimates clearly label karo; fake results real ke roop mein
      // dikhana spec ke against hai (08-FRONTEND-UI-SPEC: no misleading states) (BUG-7)
      const status = err?.response?.status;
      setError(
        status
          ? `Simulation failed (HTTP ${status}). Showing approximate demo estimates.`
          : 'Backend unavailable. Showing approximate demo estimates only.'
      );
      setIsDemo(true);
      setResult({
        // Backend response keys ke saath match: {years, current, improved, comparison}
        current: { biological_age: 45, diabetes_risk: 35, heart_risk: 28, longevity_score: 55, diseases: [] },
        improved: {
          biological_age: Math.max(0, 45 - params.sleep_hours_delta * 0.5 - params.exercise_level_delta * 1.5 - params.bmi_improvement * 0.3),
          diabetes_risk: Math.max(0, 35 - params.sleep_hours_delta * 2 - params.exercise_level_delta * 4 - (params.diet_improvement === 'strict' ? 15 : params.diet_improvement === 'moderate' ? 8 : 0)),
          heart_risk: Math.max(0, 28 - params.sleep_hours_delta * 1.5 - params.exercise_level_delta * 3 - (params.smoking_quit ? 10 : 0)),
          longevity_score: Math.min(100, Math.max(0, 55 + params.sleep_hours_delta * 2 + params.exercise_level_delta * 5 + (params.diet_improvement === 'strict' ? 15 : params.diet_improvement === 'moderate' ? 8 : 0))),
          diseases: [],
        },
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-20 pb-12 px-4 max-w-5xl mx-auto">
      <div className="animate-slide-up">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
        >
          <FaArrowLeft size={18} /> Back to Dashboard
        </button>

        <h1 className="font-display text-3xl font-bold text-white mb-2">Future Health Simulator</h1>
        <p className="text-gray-400 mb-6">
          See how lifestyle changes can impact your health over the next few years
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Controls */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-5">Lifestyle Changes</h2>

            <SliderInput
              label="Time Horizon"
              value={params.years}
              onChange={(v) => update('years', v)}
              min={1} max={30} step={1}
              unit=" years"
            />
            <SliderInput
              label="Sleep Improvement"
              value={params.sleep_hours_delta}
              onChange={(v) => update('sleep_hours_delta', v)}
              min={0} max={5} step={0.5}
              unit="h more"
            />
            <SliderInput
              label="Exercise Level Increase"
              value={params.exercise_level_delta}
              onChange={(v) => update('exercise_level_delta', v)}
              min={0} max={4} step={1}
              suffix=" levels"
            />
            <SliderInput
              label="BMI Improvement"
              value={params.bmi_improvement}
              onChange={(v) => update('bmi_improvement', v)}
              min={0} max={10} step={0.5}
              unit=" points"
            />

            <div className="mb-5">
              <label className="block text-sm text-gray-300 mb-2">Diet Improvement</label>
              <div className="grid grid-cols-3 gap-2">
                {['none', 'moderate', 'strict'].map((d) => (
                  <button
                    key={d}
                    onClick={() => update('diet_improvement', d)}
                    className={`py-2 rounded-xl text-sm font-medium transition-all ${
                      params.diet_improvement === d
                        ? 'bg-primary-500/20 border border-primary-500/40 text-primary-300'
                        : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/30'
                    }`}
                  >
                    {d.charAt(0).toUpperCase() + d.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-6">
              <button
                onClick={() => update('smoking_quit', !params.smoking_quit)}
                className={`w-full py-3 rounded-xl font-medium transition-all ${
                  params.smoking_quit
                    ? 'bg-green-500/20 border border-green-500/40 text-green-300'
                    : 'bg-surface-50 border border-white/10 text-gray-400'
                }`}
              >
                <span className="inline-flex items-center justify-center gap-2">
                  {params.smoking_quit ? <FaCheck size={16} aria-hidden="true" /> : <FaSmoking size={16} aria-hidden="true" />}
                  Quit Smoking
                </span>
              </button>
            </div>

            <button
              onClick={handleSimulate}
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <FaPlay size={18} />
                  Run Simulation
                </>
              )}
            </button>
          </div>

          {/* Results */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-5">Projected Results</h2>

            {error && (
              <div role="alert" className="mb-4 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-sm">
                {error}
                {isDemo && (
                  <span className="block mt-1 text-yellow-400/80 text-xs">
                    Demo estimates only — not calculated from your real health data.
                  </span>
                )}
              </div>
            )}

            {result ? (
              <div className="space-y-4">
                <ComparisonCard
                  title="Biological Age"
                  current={result.current?.biological_age}
                  improved={result.improved?.biological_age}
                  unit=" yrs"
                />
                <ComparisonCard
                  title="Diabetes Risk"
                  current={result.current?.diabetes_risk}
                  improved={result.improved?.diabetes_risk}
                  unit="%"
                />
                <ComparisonCard
                  title="Heart Disease Risk"
                  current={result.current?.heart_risk}
                  improved={result.improved?.heart_risk}
                  unit="%"
                />
                <ComparisonCard
                  title="Longevity Score"
                  current={result.current?.longevity_score}
                  improved={result.improved?.longevity_score}
                  unit="/100"
                  lowerBetter={false}
                />

                {/* WS-5: sab disease ka current → projected comparison */}
                {(result.current?.diseases || []).length > 0 && (
                  <div className="glass-light p-4">
                    <p className="text-sm text-gray-300 font-medium mb-2">
                      All Disease Risks ({result.current.diseases.length})
                    </p>
                    <p className="text-xs text-gray-600 mb-3">
                      {result.years}-year projection with your selected lifestyle changes
                    </p>
                    <div>
                      {result.current.diseases.map((d, i) => (
                        <DiseaseComparisonRow
                          key={d.disease_key || i}
                          label={d.label || d.disease_key}
                          current={d.risk_percent}
                          improved={result.improved?.diseases?.[i]?.risk_percent}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-2xl bg-surface-100 flex items-center justify-center mx-auto mb-4">
                  <FaPlay className="text-gray-600" size={24} />
                </div>
                <p className="text-gray-500">Adjust the sliders and run a simulation to see results</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
