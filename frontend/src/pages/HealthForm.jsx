import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { submitPrediction } from '../services/api';
import { FiAlertCircle, FiInfo } from 'react-icons/fi';

const PHQ9_QUESTIONS = [
  'Little interest or pleasure in doing things',
  'Feeling down, depressed, or hopeless',
  'Trouble falling or staying asleep, or sleeping too much',
  'Feeling tired or having little energy',
  'Poor appetite or overeating',
  'Feeling bad about yourself',
  'Trouble concentrating on things',
  'Moving or speaking slowly, or being fidgety',
  'Thoughts that you would be better off dead',
];

const PHQ9_LABELS = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'];

const FAMILY_HISTORY_LABELS = ['Diabetes', 'Heart Disease', 'Hypertension', 'Cancer'];

export default function HealthForm() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    name: user?.name || '',
    age: user?.age ? String(user.age) : '',
    gender: user?.gender != null ? String(user.gender) : '',
    height: '',
    weight: '',
    sleep_hours: 7,
    exercise_level: 2,
    smoking: false,
    alcohol: 0,
    family_history: [0, 0, 0, 0],
    phq9: [0, 0, 0, 0, 0, 0, 0, 0, 0],
  });

  const bmi =
    form.height && form.weight
      ? (form.weight / (form.height / 100) ** 2).toFixed(1)
      : '—';

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const toggleFamilyHistory = (index) => {
    const updated = [...form.family_history];
    updated[index] = updated[index] ? 0 : 1;
    updateField('family_history', updated);
  };

  const updatePHQ9 = (index, value) => {
    const updated = [...form.phq9];
    updated[index] = parseInt(value);
    updateField('phq9', updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = {
        name: form.name,
        age: parseInt(form.age),
        gender: parseInt(form.gender),
        height: parseFloat(form.height),
        weight: parseFloat(form.weight),
        sleep_hours: form.sleep_hours,
        exercise_level: form.exercise_level,
        smoking: form.smoking,
        alcohol: form.alcohol,
        family_history: form.family_history,
        phq9: form.phq9,
      };
      const res = await submitPrediction(payload);
      localStorage.setItem('latestPrediction', JSON.stringify(res.data));
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit. Please check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  const exercises = ['None', 'Light', 'Moderate', 'Active', 'Very Active'];

  return (
    <div className="pt-20 pb-12 px-4 max-w-3xl mx-auto">
      <div className="animate-slide-up">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">Health Assessment</h1>
          <p className="text-gray-400">Fill in your details for a comprehensive AI health analysis</p>
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-6 text-red-400 text-sm">
            <FiAlertCircle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ── Section: Basic Info ── */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">1</span>
              Basic Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">Full Name</label>
                <input type="text" value={form.name} onChange={(e) => updateField('name', e.target.value)} className="input-field" required />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Age (18–120)</label>
                <input type="number" value={form.age} onChange={(e) => updateField('age', e.target.value)} className="input-field" min="18" max="120" required />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Gender</label>
                <select value={form.gender} onChange={(e) => updateField('gender', e.target.value)} className="input-field" required>
                  <option value="">Select</option>
                  <option value="0">Female</option>
                  <option value="1">Male</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-300 mb-1">Height (cm)</label>
                  <input type="number" value={form.height} onChange={(e) => updateField('height', e.target.value)} className="input-field" min="50" max="250" step="0.1" required />
                </div>
                <div>
                  <label className="block text-sm text-gray-300 mb-1">Weight (kg)</label>
                  <input type="number" value={form.weight} onChange={(e) => updateField('weight', e.target.value)} className="input-field" min="20" max="300" step="0.1" required />
                </div>
              </div>
              <div className="sm:col-span-2">
                <div className="glass-light p-3 flex items-center gap-3">
                  <FiInfo className="text-primary-300 shrink-0" size={18} />
                  <span className="text-sm text-gray-300">
                    Calculated BMI: <strong className="text-white">{bmi}</strong>
                    {bmi !== '—' && (
                      <span className="ml-2 text-gray-500">
                        ({parseFloat(bmi) < 18.5 ? 'Underweight' : parseFloat(bmi) < 25 ? 'Normal' : parseFloat(bmi) < 30 ? 'Overweight' : 'Obese'})
                      </span>
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ── Section: Lifestyle ── */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">2</span>
              Lifestyle
            </h2>
            <div className="space-y-5">
              {/* Sleep */}
              <div>
                <label className="block text-sm text-gray-300 mb-2">
                  Sleep Hours: <strong className="text-primary-300">{form.sleep_hours}h</strong>
                </label>
                <input
                  type="range" min="3" max="12" step="0.5"
                  value={form.sleep_hours}
                  onChange={(e) => updateField('sleep_hours', parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-600 mt-1"><span>3h</span><span>12h</span></div>
              </div>

              {/* Exercise */}
              <div>
                <label className="block text-sm text-gray-300 mb-2">
                  Exercise Level: <strong className="text-primary-300">{exercises[form.exercise_level]}</strong>
                </label>
                <input
                  type="range" min="0" max="4" step="1"
                  value={form.exercise_level}
                  onChange={(e) => updateField('exercise_level', parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                  {exercises.map((e) => <span key={e}>{e}</span>)}
                </div>
              </div>

              {/* Smoking + Alcohol */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-300 mb-2">Smoking</label>
                  <button
                    type="button"
                    onClick={() => updateField('smoking', !form.smoking)}
                    className={`w-full py-3 rounded-xl font-medium transition-all duration-200 ${
                      form.smoking
                        ? 'bg-red-500/20 border border-red-500/40 text-red-300'
                        : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/40'
                    }`}
                  >
                    {form.smoking ? '🚬 Smoker' : '🚫 Non-Smoker'}
                  </button>
                </div>
                <div>
                  <label className="block text-sm text-gray-300 mb-2">
                    Alcohol: <strong className="text-primary-300">{form.alcohol}/wk</strong>
                  </label>
                  <input
                    type="range" min="0" max="7" step="1"
                    value={form.alcohol}
                    onChange={(e) => updateField('alcohol', parseInt(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1"><span>0</span><span>7</span></div>
                </div>
              </div>
            </div>
          </div>

          {/* ── Section: Family History ── */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">3</span>
              Family History
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {FAMILY_HISTORY_LABELS.map((label, i) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => toggleFamilyHistory(i)}
                  className={`p-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                    form.family_history[i]
                      ? 'bg-red-500/20 border border-red-500/40 text-red-300'
                      : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/40'
                  }`}
                >
                  {form.family_history[i] ? '✓ ' : ''}{label}
                </button>
              ))}
            </div>
          </div>

          {/* ── Section: PHQ-9 ── */}
          <div className="glass p-6">
            <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">4</span>
              Mental Health Screening (PHQ-9)
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              Over the last 2 weeks, how often have you been bothered by:
            </p>
            <div className="space-y-4">
              {PHQ9_QUESTIONS.map((q, i) => (
                <div key={i} className="glass-light p-4">
                  <p className="text-sm text-gray-300 mb-3">
                    <span className="text-primary-300 font-medium">Q{i + 1}.</span> {q}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {PHQ9_LABELS.map((label, val) => (
                      <label
                        key={val}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 ${
                          form.phq9[i] === val
                            ? 'bg-primary-500/20 border border-primary-500/40 text-primary-300'
                            : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/30'
                        }`}
                      >
                        <input
                          type="radio"
                          name={`phq9-${i}`}
                          value={val}
                          checked={form.phq9[i] === val}
                          onChange={() => updatePHQ9(i, val)}
                          className="sr-only"
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Privacy Notice */}
          <div className="glass-light p-4 flex items-start gap-3">
            <FiInfo className="text-primary-300 shrink-0 mt-0.5" size={18} />
            <p className="text-xs text-gray-400">
              <strong className="text-gray-300">Privacy Notice:</strong> Your health data is processed locally through our ML pipeline and stored securely.
              It is never shared with third parties. This tool provides AI-based risk estimates and does <strong className="text-gray-300">not</strong> constitute medical diagnosis.
            </p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full text-lg py-4 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running Health Analysis...
              </>
            ) : (
              '🔬 Run Health Analysis'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
