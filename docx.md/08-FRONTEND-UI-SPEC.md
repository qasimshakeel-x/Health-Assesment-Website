# Frontend / UI Spec — AI Longevity Intelligence Platform

React.js 18 SPA, Tailwind CSS 3, Recharts + Chart.js, Axios. WCAG 2.1 AA compliance required.

## 1. Design System
- Palette: primary `#2E7D32` (green medical), accent `#81C784`, warning `#F9A825`,
  danger `#C62828`, neutral grays for text/background.
- Typography: system font stack or a single accessible sans-serif (e.g. Inter), min 16px body text.
- Responsive breakpoints: 375px (mobile) → 768px (tablet) → 1920px (desktop). Mobile-first.
- Every interactive element has visible focus states (keyboard navigation is a hard requirement,
  not optional — this is tested in Sprint 5 exit criteria).
- All form inputs: `aria-label`; all error messages: linked via `aria-describedby`.

## 2. Routing / Pages
| Route | Screen | Auth |
|---|---|---|
| `/login`, `/register` | Auth screens | Public |
| `/assessment` | Health Profile Form | Protected |
| `/dashboard` | Risk Dashboard | Protected |
| `/dashboard/shap` | SHAP Explainability Dashboard | Protected |
| `/dashboard/simulate` | Future Health Simulator | Protected |
| `/chat` | Diet Chat | Protected |
| `/reports` | PDF report history / download | Protected |
| `/admin/*` | Admin panel | Protected + admin role |

## 3. Screen Specs

### Health Profile Form (`/assessment`)
- Fields: age (number), gender (radio), height/weight (number, auto-computes BMI live),
  sleep hours (slider 3–12), exercise level (5-option select), smoking (toggle), alcohol (0–7
  select), family history (4 checkboxes: diabetes/heart/hypertension/cancer), PHQ-9 (9 radio-
  button rows, 0–3 scale).
- **Phase-gated extra sections** (render only if `GET /diseases` reports that phase active):
  GAD-7 (7 rows), sleep-apnea 2 questions, PCOS block (only if gender=Female), anemia 3
  questions, burnout block, thyroid fatigue question, lung-cancer passive-smoke question.
  Build this as a dynamic section renderer driven by `GET /screenings/{key}/questions`
  (see `05-API-SPEC.md` §3) — do not hardcode which questions show; new phases should not
  require a frontend redeploy for the form itself.
- Client-side validation mirrors backend Pydantic rules (age 18–120, sleep 3–12, all required) →
  green tick per valid field, inline red error + fix-it message per invalid field.
- Submit → `POST /predict` → loading spinner (never a blank screen) → redirect to `/dashboard`.
- Privacy notice banner must render above the form before any data entry.

### Risk Dashboard (`/dashboard`)
- Disease risk cards grouped into the 5 categories from `06-DISEASE-MODULES.md`
  (Cardiovascular / Metabolic / Mental Wellness / Lifestyle-Linked / Cancer Screening), each a
  collapsible section so 16 diseases doesn't overwhelm the page — collapse categories with no
  elevated risk by default, expand ones with Moderate+ findings.
- Each disease: gauge chart, color-coded by `risk_label` (Low=green, Moderate=yellow,
  High=orange, Very High=red).
- Bio Age comparison card: chronological vs biological age, delta clearly labeled +/-.
- Longevity Score meter with category badge (Poor/Moderate/Good/Excellent).
- Yellow warning banner on any `risk_percent > 60`: *"This is an AI prediction, not a medical
  diagnosis. Consult a qualified doctor."*
- Cancer Screening category cards carry the stricter disclaimer from `06-DISEASE-MODULES.md`
  Phase 5 note, always visible on the card, not just on hover/click.
- Buttons: Download PDF, Open Diet Chat, View SHAP Explanations, Run Future Simulation.

### SHAP Explainability Dashboard (`/dashboard/shap`)
- Per-disease accordion panel (only for diseases actually run in this prediction).
- Horizontal bar chart: dark = increases risk, light = decreases risk (convention must stay
  consistent across every disease, see `07-DEV-WORKFLOW.md` debugging note).
- Waterfall plot toggle for cumulative prediction build-up.
- Plain-language top-5 factor list under each chart (no raw feature names — translate
  `feature_name` to a human sentence, e.g. `bmi_over_30=1` → "BMI above 30").

### Future Health Simulator (`/dashboard/simulate`)
- Dual panel: Current vs Improved.
- Sliders: sleep improvement (+0 to +3h), activity increase (+0 to +2 levels), smoking cessation
  toggle, diet improvement (none/moderate/strict), year horizon selector (1/5/10).
- Recalculates **client-side** using cached model coefficients from the initial `/simulate` response
  — no API call per slider drag, only on initial load (see `02-ARCHITECTURE.md` Observer pattern).
- Grouped bar chart: Biological Age, top disease risks, Longevity Score — current vs improved.

### Diet Chat (`/chat`)
- Chat bubble UI, risk-context badge pinned at top (e.g. "High Diabetes Risk Active · High
  Stroke Risk Active").
- Typing indicator while waiting for Claude response.
- Yellow alert card for any flagged/contraindicated food request, with suggested alternatives.
- Every AI message footer: "Consult a registered dietitian." (rendered by frontend if not already
  present in the response, as a safety net).
- Graceful fallback UI (not a broken chat) if backend returns the `504` Claude-timeout case.

### Reports (`/reports`)
- List of past generated reports (`report_log` entries) with status, date, download link.
- "Generate New Report" button → `POST /reports/{userId}/generate` → polling spinner against
  `/reports/{reportId}/status` → auto-download or enable download button on `success`.

### Admin Panel (`/admin/*`)
- User list with latest prediction summary, search/filter.
- Delete user (confirmation modal — destructive action).
- Trigger model retraining per `disease_key`, with a status indicator.
- Action log view (`admin_action_log`).
- Not linked from the regular patient navigation; route itself still enforces role check
  server-side (never rely on hiding the link as the only protection).

## 4. State Management
- Auth state (tokens, user, role) in a top-level context/store; access token attached via Axios
  interceptor; on `401`, interceptor attempts one silent `/auth/refresh` before failing to login redirect.
- Latest prediction result cached in app state after `/predict` or `/predict/{userId}/latest`, reused
  across Dashboard / SHAP / Simulator / Chat screens rather than re-fetched per screen.
- Form state for the Health Profile Form should be resilient to accidental navigation (local draft
  in memory, not localStorage, since this is health data — see `09-ML-TRAINING-SPEC.md`/privacy
  notes if a draft-save feature is ever added).

## 5. Accessibility Checklist (Sprint 5 exit criteria)
- [ ] Full keyboard navigation through every form and dashboard
- [ ] `aria-label` on all inputs, `aria-describedby` on all error messages
- [ ] Color is never the only signal for risk level (pair with text label, e.g. "High" not just red)
- [ ] Charts have a text-equivalent summary for screen readers
- [ ] Contrast ratios meet WCAG 2.1 AA on the green medical palette (verify `#2E7D32`/`#81C784`
      combinations against white and dark backgrounds, don't assume)
- [ ] Focus is managed correctly on modal open/close (e.g. admin delete-confirmation)
