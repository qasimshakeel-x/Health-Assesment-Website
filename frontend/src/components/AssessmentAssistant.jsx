import React, { useEffect, useRef, useState } from 'react';
import {
  FaClipboardList,
  FaCommentDots,
  FaGlobe,
  FaPaperPlane,
  FaWandMagicSparkles,
  FaXmark,
} from 'react-icons/fa6';
import { sendIntakeMessage } from '../services/api';

/* ============================================================
   "AI Chat-bot Assistant" — floating chat widget (assessment page).
   DietChat se jaan-boojh kar ALAG design (floating window, gradient
   header, avatar + left-accent bot cards, gol input).

   DO MODES (header ke neeche tabs):
     1. Know About Website — website/intro ke sawaalon ke jawab
     2. Form Filling Help  — AI ek-ek karke sawal poochta hai aur
        inputs form mein khud save karta hai (auto-fill).

   Asli logic: widget sirf {messages, context} backend ko bhejta hai
   (`POST /api/v1/intake/chat`) — API key sirf backend .env mein rehti
   hai, browser ko kabhi nahi milti. LLM `form_updates` return karta
   hai jo form fields pe lag jate hain (age, screening answers, PHQ-9,
   buttons — smoking/family-history/diet bhi). SUBMIT kabhi auto nahi —
   user khud review karke karta hai.
   ============================================================ */

// Form state ke wo fields jo number hain (validation/clamp ke liye)
const NUM_RANGES = {
  age: [18, 120],
  height: [50, 250],
  weight: [20, 300],
  sleep_hours: [3, 12],
  bp_systolic: [50, 250],
  bp_diastolic: [30, 150],
  waist_circumference: [40, 250],
};
// Integer fields jo state mein NUMBER hain (string nahi)
const INT_NUMBER_FIELDS = { exercise_level: [0, 4], alcohol: [0, 7] };

const clamp = (n, min, max) => Math.min(Math.max(n, min), max);

const MODES = [
  {
    id: 'about',
    label: 'Know About Website',
    icon: FaGlobe,
    welcome:
      'Assalam-o-Alaikum! Yahan aap is website ke baare mein jaan sakte hain — yeh karti kya hai, kaunsi diseases screen hoti hain, reports kaise milti hain. Koi bhi sawaal poochein.',
    placeholder: 'Website ke baare mein poochein...',
    chips: [
      'Yeh website kya karti hai?',
      'Kaunsi diseases screen hoti hain?',
      'Kya mera data safe hai?',
    ],
  },
  {
    id: 'form',
    label: 'Form Filling Help',
    icon: FaClipboardList,
    welcome:
      'Assalam-o-Alaikum! Main aap ka form bharne mein madad karoon ga. Ek-ek karke sawaal poochonga aur aap ke jawab form mein khud save hote jayenge. Shuru karein?',
    placeholder: 'Apni details likhein...',
    chips: [
      'Meri age 42 hai, male hoon',
      'Height 170cm, weight 85kg',
      'Shuru se sawal karo',
    ],
  },
];

/** LLM ke form_updates object ko actual form state par lagata hai (clamped + validated). */
function applyFormUpdates(updates, { updateField, form, setScreeningValue }) {
  if (!updates || typeof updates !== 'object') return;
  for (const [key, raw] of Object.entries(updates)) {
    try {
      if (key === 'family_history') {
        if (Array.isArray(raw) && raw.length === 4) {
          updateField('family_history', raw.map((v) => (v ? 1 : 0)));
        } else if (raw && typeof raw === 'object') {
          // {index: 0, value: 1} ya {0: 1} — partial update current values pe
          const next = [...(form.family_history || [0, 0, 0, 0])];
          if (Array.isArray(raw)) {
            raw.forEach((u, i) => {
              if (u && u.index != null) next[Number(u.index)] = u.value ? 1 : 0;
            });
          } else {
            for (const [i, v] of Object.entries(raw)) next[Number(i)] = v ? 1 : 0;
          }
          updateField('family_history', next);
        }
      } else if (key === 'phq9') {
        if (Array.isArray(raw) && raw.length === 9) {
          updateField('phq9', raw.map((v) => clamp(parseInt(v, 10) || 0, 0, 3)));
        }
      } else if (key === 'screening_updates') {
        if (Array.isArray(raw)) {
          for (const u of raw) {
            if (u && u.key && u.response_key) {
              setScreeningValue(u.key, u.response_key, u.index ?? null, u.value);
            }
          }
        }
      } else if (key === 'name') {
        if (typeof raw === 'string' && raw.trim()) updateField('name', raw.trim().slice(0, 80));
      } else if (key === 'gender') {
        const g = String(raw).toLowerCase().trim();
        if (['0', 'female', 'f'].includes(g)) updateField('gender', '0');
        else if (['1', 'male', 'm'].includes(g)) updateField('gender', '1');
      } else if (key === 'smoking') {
        if (typeof raw === 'boolean') updateField('smoking', raw);
        else {
          const s = String(raw).toLowerCase().trim();
          if (['yes', 'true', '1', 'smoker'].includes(s)) updateField('smoking', true);
          else if (['no', 'false', '0', 'non-smoker', 'nonsmoker'].includes(s)) updateField('smoking', false);
        }
      } else if (key === 'diet_quality') {
        const d = String(raw).toLowerCase().trim();
        if (['poor', 'average', 'good'].includes(d)) updateField('diet_quality', d);
      } else if (NUM_RANGES[key]) {
        const n = parseFloat(raw);
        if (Number.isFinite(n)) {
          const [min, max] = NUM_RANGES[key];
          updateField(key, String(clamp(n, min, max))); // age/height/weight/bp/waist string hain state mein
        }
      } else if (INT_NUMBER_FIELDS[key]) {
        const n = parseInt(raw, 10);
        if (Number.isFinite(n)) {
          const [min, max] = INT_NUMBER_FIELDS[key];
          updateField(key, clamp(n, min, max)); // sleep/exercise/alcohol number hain state mein
        }
      }
    } catch {
      // ek bad update poore batch ko na roke — baqi apply hote rahen
    }
  }
}

function BotAvatar() {
  return (
    <span
      className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center"
      aria-hidden="true"
    >
      <FaWandMagicSparkles size={12} />
    </span>
  );
}

export default function AssessmentAssistant({
  form,
  updateField,
  visibleScreenings = [],
  screeningAnswers = {},
  setScreeningValue,
  phq9Questions = [],
}) {
  const [open, setOpen] = useState(false);
  const [modeId, setModeId] = useState('about');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', content: MODES[0].welcome },
  ]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef(null);
  const inputRef = useRef(null);

  const activeMode = MODES.find((m) => m.id === modeId) || MODES[0];

  // Chat khulte hi — scroll bar chat ke START (upar) par
  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      if (messagesRef.current) messagesRef.current.scrollTop = 0;
    }
  }, [open]);

  // Naya message aaye (user ka ya bot ka) — auto us Q&A par scroll neeche
  useEffect(() => {
    if (open && messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  // Mode switch — conversation reset (naya welcome, purani baatein na milen)
  const switchMode = (id) => {
    if (id === modeId || loading) return;
    setModeId(id);
    const next = MODES.find((m) => m.id === id) || MODES[0];
    setMessages([{ role: 'assistant', content: next.welcome }]);
    setInput('');
  };

  // Backend ko bhejne ke liye compact context: mode + current form values + visible screeners
  const buildContext = () => ({
    mode: modeId,
    form: {
      name: form.name || null,
      age: form.age || null,
      gender: form.gender === '' ? null : form.gender === '0' ? 'female' : 'male',
      height_cm: form.height || null,
      weight_kg: form.weight || null,
      sleep_hours: form.sleep_hours,
      exercise_level: form.exercise_level,
      smoking: form.smoking,
      alcohol_per_week: form.alcohol,
      family_history: {
        diabetes: form.family_history?.[0] ? 'yes' : 'no',
        heart_disease: form.family_history?.[1] ? 'yes' : 'no',
        hypertension: form.family_history?.[2] ? 'yes' : 'no',
        cancer: form.family_history?.[3] ? 'yes' : 'no',
      },
      bp_systolic: form.bp_systolic || null,
      bp_diastolic: form.bp_diastolic || null,
      waist_circumference: form.waist_circumference || null,
      diet_quality: form.diet_quality || null,
      phq9_answers: form.phq9,
    },
    screening_answers: screeningAnswers,
    phq9_questions: phq9Questions,
    screeners: visibleScreenings.map((cat) => ({
      key: cat.screening_key,
      label: cat.label,
      questions: (cat.questions || [])
        .filter((q) => !q.profile_field)
        .map((q) => ({
          prompt: q.prompt,
          type: q.type,
          response_key: q.response_key,
          index: q.response_index ?? null,
          options: (q.options || []).map((o) => `${o.value}=${o.label}`),
        })),
    })),
  });

  const handleSend = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    const nextMessages = [...messages, { role: 'user', content: text }];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);
    try {
      const res = await sendIntakeMessage(
        nextMessages.slice(-14), // server LLM ko last 10 bhejta hai; form state context se har baar update rehti hai
        buildContext()
      );
      const reply = res.data?.reply || 'Maazrat, main abhi jawab nahi de saka — dobara koshish karein.';
      // About mode mein form_updates nahi aane chahiye (safety: waise bhi server mana karta hai)
      if (modeId === 'form') {
        applyFormUpdates(res.data?.form_updates, { updateField, form, setScreeningValue });
      }
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : 'Maazrat, abhi AI assistant available nahi hai — thori der baad dobara koshish karein.';
      setMessages((prev) => [...prev, { role: 'assistant', content: msg }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* ── FAB: fixed → scroll ke saath hamesha ek hi jagah ── */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close AI chatbot assistant' : 'Open AI chatbot assistant'}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="fixed z-50 bottom-6 right-4 sm:right-6 w-14 h-14 rounded-full bg-primary-500 hover:bg-primary-600 text-white shadow-lg shadow-primary-500/25 flex items-center justify-center transition-transform duration-200 hover:scale-110"
      >
        {!open && (
          <span className="absolute inset-0 rounded-full animate-ping bg-primary-400/25" aria-hidden="true" />
        )}
        {open ? <FaXmark size={20} /> : <FaCommentDots size={22} />}
      </button>

      {/* ── Widget window ── */}
      <div
        role="dialog"
        aria-label="AI chatbot assistant"
        className={`fixed z-50 bottom-24 right-4 sm:right-6 w-[calc(100vw-2rem)] sm:w-[360px] max-h-[70vh] glass flex flex-col overflow-hidden transition-all duration-200 origin-bottom-right ${
          open ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-90 translate-y-2 pointer-events-none'
        }`}
      >
        {/* Header — gradient accent + bot avatar + close */}
        <div className="flex items-center gap-3 px-4 py-3 bg-primary-500/10 border-b border-white/10 shrink-0">
          <span className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center shadow-md" aria-hidden="true">
            <FaWandMagicSparkles size={16} />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-white leading-tight">AI Chat-bot Assistant</h3>
            <p className="text-[11px] text-gray-400 leading-tight truncate">
              Website poochein ya baaton se form bhwayein
            </p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close AI chatbot assistant"
            className="ml-auto p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <FaXmark size={16} />
          </button>
        </div>

        {/* Mode tabs */}
        <div className="flex gap-2 px-4 pt-3 pb-1 shrink-0" role="tablist" aria-label="Assistant modes">
          {MODES.map((m) => {
            const Icon = m.icon;
            const active = m.id === modeId;
            return (
              <button
                key={m.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => switchMode(m.id)}
                className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-medium transition-colors border ${
                  active
                    ? 'bg-primary-500/20 border-primary-500/40 text-primary-300'
                    : 'bg-white/[0.03] border-white/10 text-gray-400 hover:text-white hover:border-white/20'
                }`}
              >
                <Icon size={12} aria-hidden="true" />
                <span className="truncate">{m.label}</span>
              </button>
            );
          })}
        </div>

        {/* Messages */}
        <div ref={messagesRef} className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0" role="log" aria-live="polite" aria-label="AI chatbot messages">
          {messages.map((msg, i) =>
            msg.role === 'assistant' ? (
              <div key={i} className="flex gap-2 items-start">
                <BotAvatar />
                <div className="glass-light border-l-2 border-primary-500/50 rounded-xl rounded-tl-sm px-3 py-2 text-sm text-gray-300 max-w-[85%] whitespace-pre-wrap">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-end">
                <div className="bg-primary-500 text-white rounded-xl rounded-tr-sm px-3 py-2 text-sm max-w-[85%] whitespace-pre-wrap">
                  {msg.content}
                </div>
              </div>
            )
          )}

          {loading && (
            <div className="flex gap-2 items-center" aria-label="Assistant is typing">
              <BotAvatar />
              <span className="glass-light rounded-xl rounded-tl-sm px-3 py-2.5 inline-flex gap-1" aria-hidden="true">
                <span className="w-1.5 h-1.5 rounded-full bg-primary-300 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary-300 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-primary-300 animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          )}
        </div>

        {/* Suggestion chips — sirf chat start se pehle (pehle user message ke baad khatam) */}
        {messages.length <= 1 && (
          <div className="px-4 pb-2 flex flex-wrap gap-2 shrink-0">
            {activeMode.chips.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => setInput(chip)}
                className="border border-dashed border-primary-500/40 text-primary-300 hover:bg-primary-500/10 rounded-full px-3 py-1.5 text-xs transition-colors"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Input — gol style */}
        <form onSubmit={handleSend} className="flex items-center gap-2 px-4 py-3 border-t border-white/10 shrink-0">
          <label htmlFor="assistant-input" className="sr-only">{activeMode.placeholder}</label>
          <input
            id="assistant-input"
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={activeMode.placeholder}
            aria-label={activeMode.placeholder}
            disabled={loading}
            className="flex-1 rounded-full bg-surface-50 border border-white/10 focus:outline-none focus:border-primary-500 px-4 py-2.5 text-sm text-white placeholder-gray-500 transition-colors disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            aria-label="Send"
            className="w-10 h-10 shrink-0 rounded-full bg-primary-500 hover:bg-primary-600 text-white flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <FaPaperPlane size={15} />
            )}
          </button>
        </form>

        {/* Tiny disclaimer */}
        <p className="px-4 pb-2.5 text-[10px] text-gray-500 shrink-0">
          {modeId === 'form'
            ? 'Form bharne mein madad — medical advice nahi. Submit se pehle form zaroor review karein.'
            : 'Website/intro ke jawab — medical advice nahi.'}
        </p>
      </div>
    </>
  );
}
