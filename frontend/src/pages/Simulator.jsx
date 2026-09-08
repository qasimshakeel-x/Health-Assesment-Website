import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { simulateFuture } from '../services/api';
import { FiArrowLeft, FiPlay } from 'react-icons/fi';

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
        <div className="text-gray-600">→</div>
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

export default function Simulator() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
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
    try {
      const res = await simulateFuture(params);
      setResult(res.data);
    } catch {
      // Use mock results if backend unavailable
      setResult({
        current_scenario: { biological_age: 45, diabetes_risk: 35, heart_risk: 28, longevity_score: 55 },
        improved_scenario: {
          biological_age: 45 - params.sleep_hours_delta * 0.5 - params.exercise_level_delta * 1.5 - params.bmi_improvement * 0.3,
          diabetes_risk: Math.max(5, 35 - params.sleep_hours_delta * 2 - params.exercise_level_delta * 4 - (params.diet_improvement === 'strict' ? 15 : params.diet_improvement === 'moderate' ? 8 : 0)),
          heart_risk: Math.max(5, 28 - params.sleep_hours_delta * 1.5 - params.exercise_level_delta * 3 - (params.smoking_quit ? 10 : 0)),
          longevity_score: Math.min(95, 55 + params.sleep_hours_delta * 2 + params.exercise_level_delta * 5 + (params.diet_improvement === 'strict' ? 15 : params.diet_improvement === 'moderate' ? 8 : 0)),
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
          <FiArrowLeft size={18} /> Back to Dashboard
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
                {params.smoking_quit ? '✓ Quit Smoking' : '🚭 Quit Smoking'}
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
                  <FiPlay size={18} />
                  Run Simulation
                </>
              )}
            </button>
          </div>

          {/* Results */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-5">Projected Results</h2>

            {result ? (
              <div className="space-y-4">
                <ComparisonCard
                  title="Biological Age"
                  current={result.current_scenario?.biological_age}
                  improved={result.improved_scenario?.biological_age}
                  unit=" yrs"
                />
                <ComparisonCard
                  title="Diabetes Risk"
                  current={result.current_scenario?.diabetes_risk}
                  improved={result.improved_scenario?.diabetes_risk}
                  unit="%"
                />
                <ComparisonCard
                  title="Heart Disease Risk"
                  current={result.current_scenario?.heart_risk}
                  improved={result.improved_scenario?.heart_risk}
                  unit="%"
                />
                <ComparisonCard
                  title="Longevity Score"
                  current={result.current_scenario?.longevity_score}
                  improved={result.improved_scenario?.longevity_score}
                  unit="/100"
                  lowerBetter={false}
                />
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-2xl bg-surface-100 flex items-center justify-center mx-auto mb-4">
                  <FiPlay className="text-gray-600" size={24} />
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
