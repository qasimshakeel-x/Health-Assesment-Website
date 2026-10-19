import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { submitPrediction, getDiseases, getScreeningQuestions } from '../services/api';
import { FaCircleExclamation, FaCircleInfo, FaCheck, FaMicroscope, FaSmoking, FaBanSmoking } from 'react-icons/fa6';
import AssessmentAssistant from '../components/AssessmentAssistant';

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

function ScreeningQuestion({ catKey, q, value, onChange }) {
  if (q.type === 'number') {
    return (
      <div>
        <label className="block text-sm text-gray-300 mb-1" htmlFor={`${catKey}-${q.id}`}>
          {q.prompt}
        </label>
        <input
          id={`${catKey}-${q.id}`}
          type="number"
          min={q.min} max={q.max} step={q.step || 1}
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
          className="input-field"
          aria-label={q.prompt}
          required={q.required}
        />
      </div>
    );
  }
  // scale / yes_no / choice → option pills (PHQ-9 rows ke jaisa hi look)
  const options = q.options || [];
  return (
    <div className="glass-light p-4">
      <p className="text-sm text-gray-300 mb-3" id={`${catKey}-${q.id}-label`}>{q.prompt}</p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-labelledby={`${catKey}-${q.id}-label`}>
        {options.map((opt) => (
          <label
            key={String(opt.value)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 ${
              value === opt.value
                ? 'bg-primary-500/20 border border-primary-500/40 text-primary-300'
                : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/30'
            }`}
          >
            <input
              type="radio"
              name={`${catKey}-${q.id}`}
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              className="sr-only"
              aria-label={opt.label}
            />
            {opt.label}
          </label>
        ))}
      </div>
    </div>
  );
}

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
    // WS-4: Phase 2-5 form inputs (06-DISEASE-MODULES) — BP→stroke/metabolic,
    // waist→IDF metabolic, diet→anemia/colorectal/liver. Optional hain → backend accept karega.
    bp_systolic: '',
    bp_diastolic: '',
    waist_circumference: '',
    diet_quality: '',
  });

  // WS-4 dynamic screening sections — koi question hardcode nahi (08-FRONTEND §3):
  // /diseases se requires_screening wale keys → /screenings/{key}/questions se render.
  const [screeningCatalogs, setScreeningCatalogs] = useState({});
  const [screeningAnswers, setScreeningAnswers] = useState({});

  useEffect(() => {
    let cancelled = false;
    async function loadScreeningCatalogs() {
      try {
        const disRes = await getDiseases();
        const needed = (disRes.data.diseases || []).filter(
          (d) => d.requires_screening && d.active !== false
        );
        const entries = await Promise.all(
          needed.map(async (d) => {
            try {
              const res = await getScreeningQuestions(d.screening_key);
              return [d.screening_key, res.data];
            } catch {
              return null; // screener fail hone pe form baaki se chalta rahe
            }
          })
        );
        if (cancelled) return;
        const cats = {};
        for (const entry of entries) if (entry) cats[entry[0]] = entry[1];
        setScreeningCatalogs(cats);
      } catch {
        // /diseases unavailable → base form hi render (backend down state)
      }
    }
    loadScreeningCatalogs();
    return () => {
      cancelled = true;
    };
  }, []);

  // Catalog load hone pe har screener ke liye answer slots init karo
  useEffect(() => {
    const init = {};
    for (const [key, cat] of Object.entries(screeningCatalogs)) {
      const vals = {};
      for (const q of cat.questions || []) {
        if (q.profile_field) continue; // profile field upar alag se render hota hai
        if (q.response_index != null) {
          if (!Array.isArray(vals[q.response_key])) vals[q.response_key] = [];
          vals[q.response_key][q.response_index] = null;
        } else {
          vals[q.response_key] = q.type === 'number' ? '' : null;
        }
      }
      init[key] = vals;
    }
    setScreeningAnswers(init);
  }, [screeningCatalogs]);

  // Gates: pcos sirf Female (requires_gender=0), colorectal/severe-screener sirf age>=min_age
  const visibleScreenings = Object.values(screeningCatalogs).filter((cat) => {
    const age = parseInt(form.age || '0', 10);
    if (cat.requires_gender != null && String(form.gender) !== String(cat.requires_gender)) return false;
    if (cat.min_age != null && age < cat.min_age) return false;
    return true;
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

  const setScreeningValue = (key, responseKey, index, value) => {
    setScreeningAnswers((prev) => {
      const next = { ...(prev[key] || {}) };
      if (index != null) {
        const arr = Array.isArray(next[responseKey]) ? [...next[responseKey]] : [];
        arr[index] = value;
        next[responseKey] = arr;
      } else {
        next[responseKey] = value;
      }
      return { ...prev, [key]: next };
    });
  };

  const getScreeningValue = (key, q) => {
    const vals = screeningAnswers[key] || {};
    return q.response_index != null
      ? (Array.isArray(vals[q.response_key]) ? vals[q.response_key][q.response_index] : null)
      : vals[q.response_key];
  };

  // Required screening questions check — backend engines missing answers pe skip kar dete
  // hain, par user ko pata chalna chahiye ke kaunsa screener adhoora hai.
  const validateScreenings = () => {
    for (const cat of visibleScreenings) {
      for (const q of cat.questions || []) {
        if (q.profile_field || !q.required) continue;
        const v = getScreeningValue(cat.screening_key, q);
        if (v === null || v === undefined || v === '') {
          return `${cat.label}: "${q.prompt}" is required`;
        }
      }
    }
    return '';
  };

  // screening_answers → POST /predict ka `screening_responses` object
  // (response_key + response_index se assemble; gad7 → answers[], burnout → exhaustion[])
  const buildScreeningResponses = () => {
    const out = {};
    for (const cat of visibleScreenings) {
      const payload = {};
      for (const q of cat.questions || []) {
        if (q.profile_field) continue; // diet_quality profile column se jata hai, yahan nahi
        const v = getScreeningValue(cat.screening_key, q);
        if (v === null || v === undefined || v === '') continue;
        if (q.response_index != null) {
          if (!Array.isArray(payload[q.response_key])) payload[q.response_key] = [];
          payload[q.response_key][q.response_index] = v;
        } else {
          payload[q.response_key] = q.type === 'number' ? Number(v) : v;
        }
      }
      if (Object.keys(payload).length) out[cat.screening_key] = payload;
    }
    return out;
  };

  const toOptionalNumber = (v) => (v === '' || v == null ? null : parseFloat(v));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const screeningError = validateScreenings();
    if (screeningError) {
      setError(screeningError);
      return;
    }
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
        // WS-4 naye fields + dynamic screening answers
        bp_systolic: toOptionalNumber(form.bp_systolic),
        bp_diastolic: toOptionalNumber(form.bp_diastolic),
        waist_circumference: toOptionalNumber(form.waist_circumference),
        diet_quality: form.diet_quality || null,
        screening_responses: buildScreeningResponses(),
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

  // PHQ-9 questions ka shared JSX — screeners ke saath columns-flow wale card
  // mein aur fallback (koi screener visible na ho) dono mein isi se render.
  const phq9Questions = (
    <div className="space-y-3">
      {PHQ9_QUESTIONS.map((q, i) => (
        <div key={i} className="glass-light p-4">
          <p className="text-sm text-gray-300 mb-3">
            <span className="text-primary-300 font-medium">Q{i + 1}.</span> {q}
          </p>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={`PHQ-9 question ${i + 1}`}>
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
                  aria-label={label}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="pt-20 pb-12 px-4 max-w-6xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8 animate-slide-up">
        <h1 className="font-display text-3xl font-bold text-white mb-2">Health Assessment</h1>
        <p className="text-gray-400">Fill in your details for a comprehensive ML health analysis</p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Cards grid: chhote sections 2-up, bade (screenings wala block) full-width.
            PHQ-9 ab usi ke andar columns-flow card hai (neeche Section 5+6).
            Submit bar grid ke BAHAR (neeche) hai — aur `animate-slide-up` ka
            transform grid pe lagta hai, is liye submit bar ko us transform wale
            ancestor se bahar rakha hai. */}
        <div className="assessment-grid grid grid-cols-1 lg:grid-cols-2 gap-6 animate-slide-up">
          {/* ── Section: Basic Info ── */}
          <div className="glass p-6 assessment-card">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold" aria-hidden="true">1</span>
              Basic Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="hf-name" className="block text-sm text-gray-300 mb-1">Full Name</label>
                <input id="hf-name" type="text" value={form.name} onChange={(e) => updateField('name', e.target.value)} className="input-field" aria-label="Full name" aria-describedby={error ? 'health-error' : undefined} required />
              </div>
              <div>
                <label htmlFor="hf-age" className="block text-sm text-gray-300 mb-1">Age (18–120)</label>
                <input id="hf-age" type="number" value={form.age} onChange={(e) => updateField('age', e.target.value)} className="input-field" aria-label="Age" min="18" max="120" required />
              </div>
              <div>
                <label htmlFor="hf-gender" className="block text-sm text-gray-300 mb-1">Gender</label>
                <select id="hf-gender" value={form.gender} onChange={(e) => updateField('gender', e.target.value)} className="input-field" aria-label="Gender" required>
                  <option value="">Select</option>
                  <option value="0">Female</option>
                  <option value="1">Male</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="hf-height" className="block text-sm text-gray-300 mb-1">Height (cm)</label>
                  <input id="hf-height" type="number" value={form.height} onChange={(e) => updateField('height', e.target.value)} className="input-field" aria-label="Height in centimeters" min="50" max="250" step="0.1" required />
                </div>
                <div>
                  <label htmlFor="hf-weight" className="block text-sm text-gray-300 mb-1">Weight (kg)</label>
                  <input id="hf-weight" type="number" value={form.weight} onChange={(e) => updateField('weight', e.target.value)} className="input-field" aria-label="Weight in kilograms" min="20" max="300" step="0.1" required />
                </div>
              </div>
              <div className="sm:col-span-2">
                <div className="glass-light p-3 flex items-center gap-3">
                  <FaCircleInfo className="text-primary-300 shrink-0" size={18} />
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
          <div className="glass p-6 assessment-card">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">2</span>
              Lifestyle
            </h2>
            <div className="space-y-5">
              {/* Sleep */}
              <div>
                <label htmlFor="hf-sleep" className="block text-sm text-gray-300 mb-2">
                  Sleep Hours: <strong className="text-primary-300">{form.sleep_hours}h</strong>
                </label>
                <input
                  id="hf-sleep"
                  type="range" min="3" max="12" step="0.5"
                  value={form.sleep_hours}
                  onChange={(e) => updateField('sleep_hours', parseFloat(e.target.value))}
                  className="w-full"
                  aria-label="Sleep hours per night"
                  aria-valuetext={`${form.sleep_hours} hours`}
                />
                <div className="flex justify-between text-xs text-gray-600 mt-1"><span>3h</span><span>12h</span></div>
              </div>

              {/* Exercise */}
              <div>
                <label htmlFor="hf-exercise" className="block text-sm text-gray-300 mb-2">
                  Exercise Level: <strong className="text-primary-300">{exercises[form.exercise_level]}</strong>
                </label>
                <input
                  id="hf-exercise"
                  type="range" min="0" max="4" step="1"
                  value={form.exercise_level}
                  onChange={(e) => updateField('exercise_level', parseInt(e.target.value))}
                  className="w-full"
                  aria-label="Exercise level"
                  aria-valuetext={exercises[form.exercise_level]}
                />
                <div className="flex justify-between text-xs text-gray-600 mt-1">
                  {exercises.map((e) => <span key={e}>{e}</span>)}
                </div>
              </div>

              {/* Smoking + Alcohol */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-300 mb-2" id="hf-smoking-label">Smoking</label>
                  <button
                    type="button"
                    onClick={() => updateField('smoking', !form.smoking)}
                    aria-pressed={form.smoking}
                    aria-labelledby="hf-smoking-label"
                    className={`w-full py-3 rounded-xl font-medium transition-all duration-200 ${
                      form.smoking
                        ? 'bg-red-500/20 border border-red-500/40 text-red-300'
                        : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/40'
                    }`}
                  >
                    <span className="inline-flex items-center justify-center gap-2">
                      {form.smoking ? <FaSmoking size={16} aria-hidden="true" /> : <FaBanSmoking size={16} aria-hidden="true" />}
                      {form.smoking ? 'Smoker' : 'Non-Smoker'}
                    </span>
                  </button>
                </div>
                <div>
                  <label htmlFor="hf-alcohol" className="block text-sm text-gray-300 mb-2">
                    Alcohol: <strong className="text-primary-300">{form.alcohol}/wk</strong>
                  </label>
                  <input
                    id="hf-alcohol"
                    type="range" min="0" max="7" step="1"
                    value={form.alcohol}
                    onChange={(e) => updateField('alcohol', parseInt(e.target.value))}
                    className="w-full"
                    aria-label="Alcohol drinks per week"
                    aria-valuetext={`${form.alcohol} drinks per week`}
                  />
                  <div className="flex justify-between text-xs text-gray-600 mt-1"><span>0</span><span>7</span></div>
                </div>
              </div>
            </div>
          </div>

          {/* ── Section: Family History ── */}
          <div className="glass p-6 assessment-card">
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
                  aria-pressed={!!form.family_history[i]}
                  aria-label={`Family history of ${label}`}
                  className={`p-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                    form.family_history[i]
                      ? 'bg-red-500/20 border border-red-500/40 text-red-300'
                      : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/40'
                  }`}
                >
                  <span className="inline-flex items-center gap-1.5">
                    {form.family_history[i] && <FaCheck className="shrink-0" size={13} aria-hidden="true" />}
                    {label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* ── Section: Body Measurements & Vitals (WS-4) ── */}
          <div className="glass p-6 assessment-card">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">4</span>
              Body Measurements &amp; Vitals
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1" htmlFor="bp_systolic">
                  Blood Pressure — Systolic (mmHg)
                </label>
                <input
                  id="bp_systolic" type="number" min="50" max="250"
                  value={form.bp_systolic}
                  onChange={(e) => updateField('bp_systolic', e.target.value)}
                  className="input-field" placeholder="e.g. 120"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1" htmlFor="bp_diastolic">
                  Blood Pressure — Diastolic (mmHg)
                </label>
                <input
                  id="bp_diastolic" type="number" min="30" max="150"
                  value={form.bp_diastolic}
                  onChange={(e) => updateField('bp_diastolic', e.target.value)}
                  className="input-field" placeholder="e.g. 80"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1" htmlFor="waist_circumference">
                  Waist Circumference (cm)
                </label>
                <input
                  id="waist_circumference" type="number" min="40" max="250" step="0.5"
                  value={form.waist_circumference}
                  onChange={(e) => updateField('waist_circumference', e.target.value)}
                  className="input-field" placeholder="e.g. 90"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-2">Diet Quality</label>
                <div className="grid grid-cols-3 gap-2">
                  {['poor', 'average', 'good'].map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => updateField('diet_quality', d)}
                      aria-pressed={form.diet_quality === d}
                      aria-label={`Diet quality ${d}`}
                      className={`py-2 rounded-xl text-sm font-medium capitalize transition-all ${
                        form.diet_quality === d
                          ? 'bg-primary-500/20 border border-primary-500/40 text-primary-300'
                          : 'bg-surface-50 border border-white/10 text-gray-400 hover:border-primary-500/30'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-3">
              Optional — BP feeds Stroke &amp; Metabolic Syndrome, waist feeds Metabolic Syndrome,
              diet quality feeds Anemia / Colorectal / Liver.
            </p>
          </div>

          {/* ── Section 5+6: Mental Health (PHQ-9) + dynamic screeners (WS-4) ──
              PHQ-9 ab akela full-width section nahi — wo screeners ke saath
              masonry columns mein ek card flow karta hai, is liye poora page
              nahi khaata aur uske bagal doosre cards khali jagah fill karte hain.
              Fallback: gates (gender/age) ki wajah se koi screener visible na
              ho toh PHQ-9 wahi purane full-width card mein render hota hai.
              Hardcode nahi: screeners /diseases → /screenings/{key}/questions
              se render hote hain (08 §3). */}
          {visibleScreenings.length > 0 ? (
            <div className="glass p-6 lg:col-span-2">
              <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">5</span>
                Mental Health &amp; Health Screenings
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Personalized questions based on your profile — answered only here, shown only to you.
              </p>
              {/* Screeners ki height bohot alag hoti hai → CSS columns (masonry-style):
                  chhote cards lambon ke bagal khali jagah fill kar lete hain, aur
                  cards `break-inside-avoid` se column ke beech mein toot-te nahi.
                  Aur sirf 1 card hone pe 2-col nahi. */}
              <div className={`assessment-grid columns-1 gap-6 ${visibleScreenings.length > 1 ? 'lg:columns-2' : ''}`}>
                {/* PHQ-9 — pehla screening card (depression) */}
                <div className="glass-light p-4 assessment-card mb-6 break-inside-avoid">
                  <h3 className="text-base font-semibold text-white mb-1">Mental Health Screening (PHQ-9)</h3>
                  <p className="text-xs text-gray-500 mb-3">
                    Over the last 2 weeks, how often have you been bothered by:
                  </p>
                  {phq9Questions}
                </div>
                {visibleScreenings.map((cat) => (
                  <div key={cat.screening_key} className="glass-light p-4 assessment-card mb-6 break-inside-avoid">
                    <h3 className="text-sm font-semibold text-primary-300 mb-1">{cat.label}</h3>
                    {cat.instructions && (
                      <p className="text-xs text-gray-500 mb-3">{cat.instructions}</p>
                    )}
                    <div className="space-y-3">
                      {(cat.questions || [])
                        .filter((q) => !q.profile_field)
                        .map((q) => (
                          <ScreeningQuestion
                            key={q.id}
                            catKey={cat.screening_key}
                            q={q}
                            value={getScreeningValue(cat.screening_key, q)}
                            onChange={(v) =>
                              setScreeningValue(cat.screening_key, q.response_key, q.response_index, v)
                            }
                          />
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Fallback: koi dynamic screener visible nahi (e.g. gates) → PHQ-9
               apne purane full-width card mein. */
            <div className="glass p-6 assessment-card lg:col-span-2">
              <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-primary-500/20 text-primary-300 flex items-center justify-center text-sm font-bold">5</span>
                Mental Health Screening (PHQ-9)
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Over the last 2 weeks, how often have you been bothered by:
              </p>
              {phq9Questions}
            </div>
          )}

          {/* Privacy Notice */}
          <div className="glass-light p-4 flex items-start gap-3 lg:col-span-2">
            <FaCircleInfo className="text-primary-300 shrink-0 mt-0.5" size={18} />
            <p className="text-xs text-gray-400">
              <strong className="text-gray-300">Privacy Notice:</strong> Your health data is processed locally through our ML pipeline and stored securely.
              It is never shared with third parties. This tool provides ML-based risk estimates and does <strong className="text-gray-300">not</strong> constitute medical diagnosis.
            </p>
          </div>
        </div>

        {/* ── Submit bar (form ke bilkul END mein, normal flow) ──
            Pehle ye `position: sticky` thi (screen pe chipki rehti thi). Ab ye grid
            ke neeche aam block ki tarah scroll ke saath aata hai. Error bhi yahin
            dikhate hain taake action ke saath feedback saath rahe. */}
        <div className="mt-6">
          <div className="glass p-3 shadow-2xl">
            {error && (
              <div id="health-error" role="alert" className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-3 text-red-400 text-sm">
                <FaCircleExclamation size={16} className="shrink-0" />
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              aria-describedby={error ? 'health-error' : undefined}
              className="btn-primary w-full text-lg py-4 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Running Health Analysis...
                </>
              ) : (
                <span className="inline-flex items-center justify-center gap-2">
                  <FaMicroscope size={18} aria-hidden="true" />
                  Run Health Analysis
                </span>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Floating Form Helper — fixed FAB, scroll ke saath ek hi jagah.
          Backend proxy (/intake/chat) se LLM; API key sirf server .env mein */}
      <AssessmentAssistant
        form={form}
        updateField={updateField}
        visibleScreenings={visibleScreenings}
        screeningAnswers={screeningAnswers}
        setScreeningValue={setScreeningValue}
        phq9Questions={PHQ9_QUESTIONS}
      />
    </div>
  );
}
