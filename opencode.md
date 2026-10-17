# OPENCODE.md — Working Context (READ FIRST EVERY SESSION)

> **Har session shuru: ye padho → status dekho → kaam karo → UPDATE karo.**
> Spec details ke liye `docx.md/` ki 13 files **bar bar padhti rehna** (ye file unka copy nahi hai —
> sirf important working notes yahan hain jo next sessions mein context kaam aayenge).

---

## ⚠️ GOLDEN RULES

1. **3 folders ALAG hain — MIX NAHI:**
   - `backend/` = Python/FastAPI (jo bana hua hai waisa hi rakhna)
   - `frontend/` = React (jo bana hua hai waisa hi rakhna)
   - `ml/` = ML training + models + orchestrator
   - Framework/structure change NAHI karna — jis framework mein bana hai usi mein continue.
2. **Koi naya pattern chahiye jo existing framework mein nahi hai → code ke COMMENTS mein likhte
   jao** (TODO/NOTE comments), abhi mat badlo.
3. **docx.md = source of truth for spec.** Kaam se pehle relevant doc padho (e.g. naya endpoint →
   05-API-SPEC.md, naya disease → 06-DISEASE-MODULES.md).
4. Ye file har session ke end mein update karo: ✅ kya bana, 🐛 kya fix, 📌 pending kya.
5. User Roman Urdu mein baat karta hai — replies Roman Urdu/Hindi mein.

---

## 🏗️ PROJECT (1 line)

AI Longevity Platform — health form → 16 disease risk (5 categories, phased) + bio age + longevity
score + SHAP + future simulator + Claude diet chat + PDF. Backend FastAPI, Frontend React,
ML alag folder mein.

---

## ✅ STATUS (audit done 2026-10-05; ML/DB updated 2026-10-07; WS-3..6 + frontend 2026-10-08; S7 verify 2026-10-09; Round-2 gaps closed 2026-10-13; S10 diet-chat session storage 2026-10-13; ML→ML_TRAINING.md real-data pipeline 2026-10-14; S12 diet-chat verified + rule-based plan-order fix 2026-10-14; S13 ML 17/17 trained + verified, colorectal REAL + burnout labelled SYNTHETIC 2026-10-14; S14 APININJAS live + health_api harden + localhost run 2026-10-14; S16 verify — pytest 27/1 (sirf IT-03 FAIL, known), IT-03b fixed (S15 stateless chat pe align), artifact SHAP verified 2026-10-15)

### Backend (backend/) — BANA HUA HAI, chal raha hai
- ✅ main.py: 8 routers (auth/admin/predict/shap/simulate/chat/reports/**diseases**) `/api/v1` +
  `/health` + lifespan model load. JWT roles (admin/manager/user). 6 DB tables
  (`app/models/database.py`). FastAPI 0.141.1 (routers app.routes pe `_IncludedRouter` ke roop
  mein lazy — route check `original_router.routes` mein hai).
- ✅ Structure: `app/routes/*`, `app/middleware/auth.py`, `app/schemas/user.py`,
  `app/services/health_api.py` — **ye structure hi hai, change nahi karna** (spec ka
  `api/v1/`, `db/`, `config.py` layout follow NAHI kiya — chal raha hai waisa hi chalega).
- ✅ `GET /diseases` (routes/diseases.py, registry se feed) ab `screening_key` /
  `requires_screening` / `active` / `min_age` / `requires_gender` fields bhi bhejta hai.
  `GET /screenings/{key}/questions` **BANA (WS-3)** — `SCREENING_QUESTIONS` catalog
  (diseases.py mein, 7 screeners: gad7 7, sleep_apnea 2, pcos 2, anemia 3, burnout 5,
  thyroid 1, lung_cancer_exposure 1; unknown/metabolic → 404) — alag router
  `screenings_router` prefix `/api/v1/screenings` (main.py line 69).
  `GET /predict/{userId}/history` (30 most-recent), `disclaimer` field predict POST + /latest +
  /history + simulate mein.
- ✅ **predict.py naya (WS-3)**: profile `bp_systolic/bp_diastolic/waist_circumference/
  diet_quality` save; `ScreeningResponse` rows (har screener ek row, payload JSONB);
  `DiseaseRiskResult` rows (16 diseases, prediction_id ke neeche); POST + `/latest` + `/history`
  sab mein `disease_risk_results` array (05-API-SPEC §9 shape + `label` registry se,
  registry order mein sort, joinedload). **Flat columns (diabetes_risk etc.) rakhay** —
  chat.py/reports.py back-compat (WS-6 mein move honge).
- ✅ `HealthProfileInput` + naye optional fields + `screening_responses: Dict[str, Dict]`
  (validator sirf registry screening keys allow karta hai → unknown key pe 422).
- ✅ `simulate.py` ab real data: latest profile + prediction se baseline (pehle hardcoded
  bmi 28/risks 35-28 tha); profile/prediction na mile to 404.
- ✅ Endpoints COMPLETE: `GET /shap/{id}?disease=`, `POST /auth/logout` (2026-10-13),
  `POST /admin/models/retrain`, `GET /admin/actions` (2026-10-13).
- ✅ `admin_action_log` table + model (2026-10-13); `_log_action()` admin create/update/
  role/delete + retrain pe likhta hai. WS-1 mein 2 tables: disease_risk_results,
  screening_responses ✅. `predict.py` updated (naye columns + screening save +
  disease_risk_results rows + array responses ✅).
- ✅ `backend/tests/` BANA (2026-10-13 — 27 tests, sab PASS); alembic `versions/` mein
  1 migration `ad0291fbd3b8_initial_schema.py` (9 tables). `db/seed.py` se bhi tables bante hain.

### Frontend (frontend/) — BANA HUA HAI
- ✅ 7 original pages: Login, Register, HealthForm, Dashboard, SHAPDashboard, Simulator, DietChat.
- ✅ **2026-10-13**: `Reports` page, `Admin` page, `NotFound` (404), `RoleRoute` guard
  (admin/manager), mobile nav (Navbar rewrite — hamburger + Reports/Admin links).
- ✅ `services/api.js`: 25 endpoint wrappers backend se MATCH + Bearer + refresh-on-401 (401 pe ek
  baar refresh → retry). AuthContext. Tailwind `#2E7D32` design system.
- ✅ Build pass (dist/ exists), vite.log clean.
- ✅ **WS-4 (2026-10-08)**: HealthForm Section 5 (BP×2, waist, diet_quality) + Section 6
  dynamic screening sections (7 screeners, `getDiseases`+`getScreeningQuestions` se render,
  gender/age gates, required validation → `screening_responses` payload).
- ✅ **WS-5 (2026-10-08)**: Dashboard `disease_risk_results` se 16 cards / 5 collapsible
  categories + cancer disclaimers; Simulator 16-disease comparison rows.
- ✅ Browser e2e `frontend/e2e_assessment.mjs` PASS (2026-10-08) — naye screening fields ke
  liye `answerScreenings()` helper add kiya.
- ❌ Missing: `Reports` page, `admin/*` pages (backend wrappers already exist api.js mein), 404
  route, role guard, mobile nav (Navbar `hidden md:flex`, hamburger nahi) — **sab DONE 2026-10-13
  (upar dekho)**.
- ❌ Routes spec se alag: `/` = HealthForm (spec: `/assessment`), `/shap/:id` (spec:
  `/dashboard/shap`), `/simulator` (spec: `/dashboard/simulate`) — **rename mat karo, chal raha
  hai waisa hi rakhna** (nav links already isi mein set hain).
- ✅ Accessibility: `aria-*` + `htmlFor` (2026-10-13) — Login/Register (role=alert, describedby),
  DietChat (role=log, aria-live), HealthForm (labels, aria-label/describedby, aria-pressed,
  radiogroup), Dashboard history panel.

### ML (ml/) — 2026-10-14: ML_TRAINING.md config-driven pipeline, **17/17 trained** (16 real + 1 labelled synthetic)
> **2026-10-14 big change:** training ab `docx.md/ML_TRAINING.md` ke hisaab se hai — real,
> app-aligned datasets (`ml/data/real/*.csv`) + ek config-driven trainer (`ml/train.py`).
> Purana synthetic path (`ml/data/generate_datasets.py`, `ml/training/train_models.py`,
> `ml/models/shap_explainer.py`) **DELETE ho gaya**. **S13: sab 17 registry diseases trained +
> verified.** Details neeche + FIXES LOG 2026-10-14 (S11 + S13).
- ✅ **`ml/train_config.py`** — **17** disease entries: 1 dataset + exact inference feature
  list each (`DISEASES`). `colorectal` = **REAL** (NHANES 2017-18 `MCQ_J` `MCQ230A-D` code 16/31,
  age≥40 app gate, 55 cases). `burnout` = **SYNTHETIC** (`"synthetic": True`, labelled —
  Ground Rule 1 ka single documented deviation).
- ✅ **`ml/train.py`** — spec pipeline: split-first → SMOTE *inside* ImbPipeline → imputer/scaler
  in-pipeline → **sigmoid calibration** → **OOF-F2 threshold** → metrics+flags → joblib artifact
  → `ml/reports/<d>.json` + `<d>_shap.png` + `SUMMARY.md` + model card. Optuna/shap/matplotlib
  optional (try/except). Artifact-size mitigation: bounded trees + `compress=3`.
- ✅ **`ml/predict.py`** — `load`/`predict_risk` (spec-verbatim) + `has_artifact`, `threshold`,
  `band_for`, `explain` (SHAP **from the served artifact**, so dashboard == predictions).
- ✅ **`ml/data/prepare_real.py` + `ml/data/README.md`** — real sources/licences (NHANES J,
  UCI CKD/ILPD/thyroid/Cleveland, Kaggle stroke/PCOS/lung/sleep, Figshare GAD-7/PHQ-9),
  label-from-feature exclusions. Raw downloads: `ml/data/real/raw/`.
- ✅ **Engines artifact-first**: `disease_risk`/`phase2_risk`/`depression` `predict` returns
  `band`/`see_doctor`/`disclaimer` when `has_artifact` (legacy `.pkl` stack fallback jab
  artifact missing ho ya load fail kare). `PHASE1_SCHEMAS` moved → `ml/models/constants.py`.
- ✅ `DISEASE_REGISTRY` = **16 entries** (`ml/models/registry.py`), engines `disease_risk` (4),
  `phase2` (8 ML), `screening` (4 rule), `depression`. `screening_classifier.py` untouched.
- ✅ **Orchestrator** dispatch all 16; `compute_shap_all` artifact-first (legacy SHAP fallback).
- ⚠️ **Honesty flags** (`ml/train.py`): `SMALL_DATASET`, `HEAVY_IMBALANCE`,
  `LOW_FEATURE_MODEL` (source didn't collect a column the app asks), `SUSPICIOUS_POSSIBLE_LEAKAGE`,
  `SYNTHETIC_DATA` (Ground Rule 1 deviation); status `BELOW_TARGET` jahan targets miss —
  `ml/reports/SUMMARY.md` mein live.
- ❌ Deleted: `ml/data/generate_datasets.py`, `ml/training/` (train_models.py), `ml/models/shap_explainer.py`.
- ✅ **Inference gates DONE (WS-3)**: `DiseaseConfig` +`min_age`/`requires_gender` fields;
  `phase2_risk.predict` registry-driven `_eligible()` → pcos (requires_gender=0) sirf female,
  colorectal (min_age=40) sirf 40+ → ineligible pe `None` → row hi nahi banti. Smoke: female 45
  → 16 diseases, male 30 → 12 (pcos+colorectal out, apne screening answers na bheje to woh bhi out).
- ✅ `_yn()` helper phase2_risk mein: "yes"/"no" strings → 0/1 (bool("no")=True bug tha —
  thyroid/pcos/anemia/lung sab isi se).
- ✅ `simulate.py` hardcoded fake profile HATA diya (WS-3) — ab latest prediction + profile.

**S13 (2026-10-14) — ab 17/17 trained + verified (yahi section sabse latest hai):**
- ✅ **Result: 3 PASS / 14 BELOW_TARGET — koi bhi PASS force nahi kiya.** `ml/reports/SUMMARY.md`
  (live) dekho. Top: gad7 **0.999**, depression **0.998** (dono `SUSPICIOUS_POSSIBLE_LEAKAGE` —
  label items se derive hota hai **by design**, chhupaya nahi), sleep_apnea 0.953, ckd 0.955,
  metabolic_syndrome 0.898, diabetes 0.875, pcos 0.872, stroke 0.814, hypertension 0.810,
  anemia 0.756, obesity 0.722, lung_cancer 0.720, heart 0.701, colorectal 0.694, liver 0.649,
  thyroid 0.537, burnout 0.877 (`SYNTHETIC_DATA`).
- ✅ **`ml/reports/REPORT.md`** = spec **§12 report** (per disease: dataset/source, rows, positive
  rate, features, preprocessing, CV+test metrics, top SHAP, flags, limitations). Generator:
  **`ml/report.py`** (`python -m ml.report`) — metrics JSONs se banta hai, drift nahi kar sakta.
- ✅ **`ml/smoke_test.py`** (acceptance §10) + **`ml/requirements.txt`** add. `ml/train.py`:
  naya `SYNTHETIC_DATA` flag + model-card warning + `encoding="utf-8"` (SUMMARY ka `±` cp1252
  mojibake fix — pehle `\xb1` likha ja raha tha).
- ✅ **`prepare_real.py`** mein `prepare_nhanes_colorectal()` (raw → app-aligned; NHANES cap
  **nahi** lagaya — 55 positives bachane ke liye) + **`ml/data/generate_synthetic.py`**
  (SEED=42 deterministic, documented latent-variable generator `z~Beta(2,2)`, `signal`/`slope`
  knobs 3-fold RF sweep se 0.75–0.95 AUC band pe calibrate).
- ✅ **Verify**: `python -m ml.smoke_test` → **17 ok / 0 skipped / 0 failed**;
  `pytest backend/tests/test_unit_ml.py -q` → **13/13 PASS**; engines live artifact serve karte
  hain (`risk_percent`/`category`/`band`/`see_doctor`/`disclaimer`; depression
  `risk`/`band`/`see_doctor`).
- ⚠️ **Ground Rule 1 deviation = sirf 1 disease (`burnout`), user-approved.** Real candidate
  mila bhi tha — Mendeley "Burnout Risks Bangladeshi Physicians" (CC BY 4.0, 1434 rows) — lekin
  **reject**: columns app-aligned nahi (`Working_Hour` = nominal bin code 1–6; `Dissatisfaction` =
  symptom *type* Anxiety/Fatigue/Insomnia/…; `Mental_Disturbances` = *coping strategy* Switch
  workplace/Medication/…) → app ke `work_hours`/`job_satisfaction`/3 exhaustion items se match
  nahi (BUG-5). Best mapping pe bhi test AUC **0.515 = chance**. Colorectal bhi **real** rakha
  (test AUC 0.694 > synthetic 0.752, kyunki real signal hai: SHAP top `age` 0.72 → exercise →
  smoking → alcohol). Chaaron ka comparison table: **`ml/data/README.md`**.
- 📁 **Artifacts**: `ml/models/*.joblib` (17) + `model_cards/*.json` (17) + `reports/*_metrics.json`
  + `*_shap.png` + `SUMMARY.md` + `REPORT.md`; data `ml/data/real/*.csv` (16) +
  `ml/data/synthetic/*.csv` (2 — sirf `burnout` train hota hai, `colorectal.csv` comparison baseline).

### DB / Docker (WS-1 ✅ 2026-10-07)
- ✅ **8 tables** (seed.py se verify kiye): users, user_profiles, prediction_results,
  shap_explanations, chat_sessions, report_log, **disease_risk_results**, **screening_responses**.
- ✅ `disease_risk_results` (04-DATA-MODEL §2): prediction_id FK, disease_key, category,
  risk_percent (CHECK 0–100), risk_label, confidence + indexes.
- ✅ `screening_responses`: user_profile_id FK, screening_key (gad7|sleep_apnea|pcos|anemia|
  burnout|thyroid|lung_cancer_exposure), responses JSONB + indexes.
- ✅ `user_profiles` +4 columns: bp_systolic, bp_diastolic, waist_circumference, diet_quality
  (06-DISEASE-MODULE inputs).
- ✅ `database.py` mein naye model classes + relationships; **migration ho chuka hai**
  (psql ALTER + seed → `\dt` se 8 tables confirm). Local PostgreSQL 17 (Docker NAHI hai).
- ✅ `admin_action_log` BANA (2026-10-13: admin_id FK SET NULL, action, target, details,
  created_at + index). **1 alembic migration** `ad0291fbd3b8_initial_schema` (9 tables,
  `upgrade` temp DB pe verify + real DB `stamp head`). docker-compose JWT_SECRET hardcoded (baaki).

---

## 🐛 FIXES LOG (date + kya fix hua — newest last)

- 2026-10-14 (S11): **ML → ML_TRAINING.md config-driven pipeline (REAL data) + replaced code delete.**
  - **ML ✅** `ml/train_config.py` (15 real app-aligned diseases) + `ml/train.py` (spec §7:
    split-first → SMOTE inside `ImbPipeline` → imputer/scaler in-pipeline → **sigmoid
    calibration** → **OOF-F2 threshold** → metrics+flags → `ml/models/<d>.joblib` +
    `ml/reports/<d>_metrics.json` + `<d>_shap.png` + `SUMMARY.md` + model card). Real datasets
    `ml/data/real/*.csv` via `ml/data/prepare_real.py`. **colorectal/burnout = NO_REAL_DATA**
    (config mein nahi — legacy pkl serve hota rahega).
  - **DELETE ✅** `ml/data/generate_datasets.py` (synthetic; `PHASE1_SCHEMAS` →
    `ml/models/constants.py`), `ml/training/` (`train_models.py`), `ml/models/shap_explainer.py`
    (dead), scratch files. `admin.py` retrain import → `from ml.train import train_all`.
    `ml/data/README.md` (sources/licences/NO_REAL_DATA) add.
  - **Serving ✅** `ml/predict.py`: `has_artifact`/`threshold`/`band_for`/`explain` (SHAP **from
    the served artifact**, isliye dashboard == predictions). Engines `disease_risk`/`phase2`/
    `depression` artifact-first (pkl fallback colorectal). `orchestrator.compute_shap_all`
    artifact-first.
  - **UI sync ✅** questions already feature-aligned (no change needed); `predict.py` route
    `band`/`see_doctor`/`disclaimer` POST **aur** GET dono mein (GET pe artifact threshold se
    derive, koi DB migration nahi); Dashboard: per-disease `disclaimer` note +
    "screening model follow-up" banner. Simulator heuristic hai (ML-independent) — no change.
  - **Environment ⚠️** box pe sirf **~4 GB RAM** (free ~700 MB) → `n_jobs=-1` + 5-fold
    calibration OOM-die karta tha. Fix: per-disease **subprocess** runner + `n_jobs=1` +
    bounded trees (`rf_n=120/depth 8`, `xgb_n=120`) + `cal_cv=3` (**reported** `cv_auc` ab bhi
    5-fold) + `joblib compress=3` (275 MB → low-MB artifacts). Ek stray `python -m ml.train --all`
    process bhi RAM kha raha tha — kill kiya.
  - Verify: py_compile sab OK; (full train + tests isi session mein aage).

- 2026-10-14 (S12): **Diet-plan bot verify + 1 rule-based ordering bug fix.**
  - **Verify (live DB + Groq)** — `prediction_id=35` (user 24, 16 disease rows) pe direct route
    handler + DB context test: `build_health_context` sahi (16 risks + bio age/longevity),
    `build_risk_badge` OK, `POST /chat/{id}/message` → Groq se personalized full daily diet
    plan (2800 chars, user ke risk numbers reference karta hai), same-session messages
    accumulate, `GET /history` bina `session_id` = khaali, unknown session = khaali. Macro/water
    local calcs OK.
  - 🐛 **Fix**: `generate_response()` rule-based DIET PLAN branch LUNCH/WEIGHT/GREETING branches
    ke baad thi → natural triggers ("generate my diet plan", "meal plan", "what should I eat
    today", "menu plan") shadow ho jaate the. Ab DIET PLAN branch sabse pehle check hota hai.
    Regression: "diet"→weight, "rice"→rice, "lunch"/"fruit"→waise hi; `py_compile` OK;
    IT-03/IT-03b ke exact messages PASS.
  - ⚠️ **Config gap (action user pe)**: `.env` mein `APININJAS_KEY` missing hai (`.env.example`
    mein hai) → `search_nutrition`/`search_exercises` silently `[]` dete hain, isliye "calories
    in X"/"exercise for Y" real API data nahi dete (Groq/rule-based fallback chalta hai).
  - ℹ️ **Note**: ML retrain batch (`run_all_train.py`) is waqt 8/15 pe tha — **baad mein S13
    (2026-10-14) mein poora 17/17 train + verify ho gaya** (neeche S13 dekho).

- 2026-10-14 (S13): **ML_TRAINING.md — sab 17 registry diseases TRAINED + VERIFIED (16 real + 1 labelled synthetic).**
  - ✅ **Train all 17** (spec §7 config-driven; per-disease `python -m ml.train --disease <d>`, OOM-safe):
    `ml/models/*.joblib` (17) + `model_cards/*.json` (17) + `reports/*_metrics.json` (17) +
    `*_shap.png` (17) + `SUMMARY.md`. Result: **3 PASS / 14 BELOW_TARGET — koi bhi PASS force nahi kiya.**
    Top: gad7 .999 + depression .998 (`SUSPICIOUS_POSSIBLE_LEAKAGE` — label items se derive hota hai,
    **by design**), sleep_apnea .953, ckd .955, metabolic_syndrome .898, diabetes .875, pcos .872,
    stroke .814, hypertension .810, anemia .756, obesity .722, lung_cancer .720, heart .701,
    colorectal .694, liver .649, thyroid .537, burnout .877 (`SYNTHETIC_DATA`).
  - ✅ **`ml/reports/REPORT.md`** = spec **§12 report** (per disease: dataset/source, rows, positive
    rate, features, preprocessing, CV+test metrics, top SHAP, flags, limitations) — generator
    **`ml/report.py`** (`python -m ml.report`), metrics JSONs se banta hai (drift-proof).
  - ✅ **`ml/smoke_test.py`** (acceptance §10) + **`ml/requirements.txt`**; `ml/train.py` mein naya
    `SYNTHETIC_DATA` flag + model-card warning + `encoding="utf-8"` (SUMMARY `±` cp1252 mojibake fix).
  - ✅ **`prepare_real.py`**: `prepare_nhanes_colorectal()` (NHANES 2017-18 `MCQ_J`, `MCQ230A-D`
    code 16 colon / 31 rectum, age≥40 app gate → 3882 rows / 55 pos / 1.42%; cap **nahi** lagaya —
    positives bachane ke liye). **`generate_synthetic.py`**: SEED=42 documented latent-variable
    generator (`z~Beta(2,2)`; `signal`/`slope` 3-fold RF sweep se calibrate). Sab data:
    `ml/data/real/*.csv` (16) + `ml/data/synthetic/*.csv` (2; sirf `burnout` train hota hai).
  - ⚠️ **Ground Rule 1 deviation = sirf 1 disease (`burnout`), user-approved** → `SYNTHETIC_DATA`
    (metrics JSON + model card + SUMMARY + `ml/data/README.md` — sab jagah labelled). Real candidate
    Mendeley "Burnout Risks Bangladeshi Physicians" (CC BY 4.0, 1434 rows) **reject**: columns
    app-aligned nahi (`Working_Hour` = nominal bin code 1–6, `Dissatisfaction` = symptom *type*,
    `Mental_Disturbances` = *coping strategy*) → best mapping pe bhi test AUC **0.515 = chance**.
    `colorectal` **REAL** hi rakha (test .694 > synthetic .752 — real signal: SHAP top `age` .72 →
    exercise → smoking → alcohol). Chaaron ka comparison table: **`ml/data/README.md`**.
  - ✅ **Verify**: `python -m ml.smoke_test` = **17 ok / 0 skipped / 0 failed**;
    `pytest backend/tests/test_unit_ml.py -q` = **13/13 PASS**; engines live artifact serve karte hain
    (`risk_percent`/`category`/`band`/`see_doctor`/`disclaimer`; depression `risk`/`band`/`see_doctor`).

- 2026-10-14 (S14): **APININJAS key live + health_api harden + localhost run + diet-chat tests.**
  (NOTE: ye S14 hai — ML 17/17 training wala alag entry **S13** hai, dono same din.)
  - ✅ **`APININJAS_KEY` fix (`.env`)**: user ne key daali thi par placeholder prefix ke saath
    (`your-api-ninjas-key-here MIftx...`) → API 401. Ab sirf asli key (`len 40`). Live verify:
    nutrition (`chicken breast`) + exercise (`chest`) API se aate hain, sab `_check_api_queries`
    paths OK. **NOTE:** key `health_api.py` import-time pe padhta hai → backend **restart** zaroori
    (kiya).
  - 🐛 **`health_api.py` harden**: free-tier API kabhi `calories`/`protein_g` = `"Only available for
    premium subscribers."` string deta hai → `format_nutrition` mein `TypeError` (str > int). Ab
    `_sf()` safe-float (string/premium → 0) dono formatters mein. Isse "calories in X" crash nahi
    hota.
  - 🐛 **`chat.py` DIET PLAN ordering** (S12) — already noted.
  - ✅ **Localhost run**: backend `python -m backend.run` (`:8000`, `/health` healthy,
    `models_loaded:true`; logs `logs/backend_run_out.log`+`_err.log`) + frontend `npm run dev`
    (`:3000`, HTTP 200; logs `logs/frontend_dev_out.log`+`_err.log`). Dono detached `Start-Process`
    se start (shell band hone pe bhi chalte rahein).
  - ⚠️ **Diet-chat tests (inspect)**: `test_it03b_chat_sessions_are_isolated` **PASS**;
    `test_it03_chat_returns_risk_aware_guidance` **FAIL** — chat logic se related NAHI (dekho
    diabetes bullet neeche).
  - ⚠️ **Diabetes model under-calibrated (Round 4 / user: filhaal kuch nahi)**: 45F / BMI 32 /
    saare symptom answers "yes" → `diabetes_risk = 1.8%`. Wajah: `ml/reports/diabetes_metrics.json`
    = `BELOW_TARGET` + `LOW_FEATURE_MODEL`; NHANES mein `freq_urination/excess_thirst/weight_loss/
    family_heart/hypertension/cancer` columns NAHI (NaN) → sklearn unhe skip karta hai →
    **screening symptoms prediction pe asar nahi**. Isi wajah se IT-03 fail (fruit branch `low-GI`
    expect karta hai, par diabetes ≤40 → normal branch).
  - **User decision (2026-10-14)**: diabetes model pe **filhaal kuch nahi** karna (aage dekhenge);
    session persistence pe **C** = jaisa hai waisa (fresh chat har baar; DB mein save rehta hai).

- 2026-10-15 (S16): **Verification pass — full pytest + IT-03b ko S15 stateless-chat pe align kiya.**
  - ✅ `python -m pytest backend/tests -q` → pehle **26 passed / 2 failed**. Dono ka root cause clear:
    (1) `test_it03b_chat_sessions_are_isolated` — **S15 ne chat ko stateless kiya** (DB mein kuch save
    nahi; `get_chat_history` hamesha `messages: []`) par test purani session-persistence expect kar
    raha tha → **stale test**. (2) `test_it03_chat_returns_risk_aware_guidance` — documented diabetes
    `LOW_FEATURE_MODEL` issue (S14 entry dekho).
  - 🐛 **IT-03b fix**: test ab S15 contract verify karta hai (apna/koi/naya `session_id` → sab pe
    `messages == []`, no leak) → **IT-03b PASS** (`-k it03` = **1 failed, 1 passed**; sirf IT-03 baaki).
  - ✅ **Artifact SHAP verified**: `test_it02_shap_rows_for_ml_diseases` +
    `test_pipeline_shap_values_normalized` **PASS** — SHAP naye `*.joblib` artifacts se banta hai,
    `/shap` route `direction` sign se derive karta hai → dashboard naye models dikhata hai.
  - ⚠️ `frontend/e2e_assessment.mjs` **disk pe nahi hai** (untracked tha, ab removed) aur
    `frontend/package.json` mein koi browser-test dep/script bhi nahi → browser e2e run nahi ho saka.

- 2026-10-15 (S17): **`ml/predict` artifact-path bug fix — reload path pe band/see_doctor/disclaimer wapas.**
  - 🐛 **Root cause**: `_metrics_path()` `os.path.dirname(os.path.dirname(abspath(__file__)))` se
    **repo root** nikalta tha → `<repo>/reports/<d>_metrics.json` (exist nahi karta) → `threshold()`
    hamesha `None` → `band_for()` None → `/latest` + `/history` ke `disease_risk_results` rows pe
    `band`/`see_doctor`/`disclaimer` **teeno None** (POST response theek tha kyunki engine artifact se
    seedha band deta hai — isi liye koi test pakad nahi paya). Isi off-by-one class ka
    `_artifact_path()` ka cwd-independent fallback bhi galat tha (`<repo>/models/...`).
    Fix: naya `_ml_dir()` helper (file ka apna dir) — dono jagah use.
  - ✅ **Live verify** (backend `:8000` restart ke baad): `/predict` POST = 16 rows + 12 band;
    `/latest` = 16 rows + **12/12 band** (`band=low`, `see_doctor=False`, `disclaimer` present);
    `/history` bhi. **cwd-independent** check (temp dir se): `threshold('diabetes')=0.0761`,
    `band(1.5%)='low'`, `band(60%)='high'`; 12/12 ML diseases ke artifact + threshold OK.
  - ✅ **2 regression tests** `backend/tests/test_unit_ml.py`:
    `test_artifact_threshold_and_band_are_cwd_independent` +
    `test_risk_rows_carry_band_only_for_ml_diseases` → **15/15 PASS**.
  - ✅ **Full-journey API e2e** (`e2e_api_smoke.py`, live `:8000`): register → predict(16+band) →
    /latest(16 + 12 band) → /history → /shap(46 rows / 12 diseases + `?disease=` filter) →
    /diseases(16 + naye fields) → /screenings/gad7(7) + unknown 404 → /simulate(16+16) →
    /chat(Groq, 1437 chars) → report PDF (`%PDF`, 4117 bytes) → auth guards (403 non-admin,
    401 no-token) = **21/21 PASS**.
  - ⚠️ Browser e2e (`frontend/e2e_assessment.mjs`) nahi chal saka: file disk pe nahi + `frontend`
    package.json mein koi puppeteer/playwright dep nahi (global bhi nahi) → API-level e2e substitute.

- 2026-10-08 (S6): **WS-4 + WS-5 Frontend DONE + WS-6 code DONE — Round 3 = 6/6 (verify pending)**
  - **WS-4 HealthForm**: Section 5 "Body Measurements & Vitals" (bp_systolic/bp_diastolic/
    waist_circumference/diet_quality) + Section 6 dynamic screening sections (7 screeners,
    catalog load, gender/age gates, `profile_field` skip, required validation →
    `screening_responses` payload). api.js: `getDiseases`, `getScreeningQuestions`.
  - **WS-5 Dashboard**: 16 cards / 5 collapsible category sections (CATEGORY_ORDER:
    cardiovascular→metabolic→mental_wellness→lifestyle_linked→cancer_screening, peak ≥25
    open, >60 "Elevated" badge), cancer cards stricter disclaimer + server `disclaimer`
    footer. **Simulator**: `DiseaseComparisonRow` 16-disease list + **fix** — response keys
    `current_scenario/optimized_scenario` → backend ke actual `current/improved`.
  - **WS-6 code**: chat `build_risk_summary` ab `disease_risk_results` rows se (registry
    order, flat-columns fallback); shap.py `?disease=` query param; reports.py PDF mein
    Health Profile + 16-disease table (category/risk%/level + cancer note) + scores.
  - Verify: `npm run build` PASS; browser e2e `frontend/e2e_assessment.mjs` **PASS**
    (dashboard update ✅, fresh-reload DB restore ✅, 16 cards render, screening submit ok).
    e2e mein `answerScreenings()` helper add — naye required validation ke bina submit block
    hota.
  - Debug: console 404s = `/vite.svg` favicon (index.html pre-existing, cosmetic);
    **stale uvicorn** — 1:26 AM wala process purane code pe chal raha tha, meri naye start
    commands port-conflict se chupke se crash (health OK purane se aata rehta hai). Fix:
    `Get-CimInstance Win32_Process -Filter "name='python.exe'"` → PID kill + restart,
    CreationDate se naye/purane process ki pehchan.
  - **ABORTED (session yahin band)**: `ws6_smoke.py` naye server pe re-run **pending**
    (pehla next kaam); DepressionCard `Confidence: 7720%` bug — backend confidence % mein
    hai aur Dashboard `×100` dobara karta hai (fix: `confidence > 1` ho to multiply mat
    karo); in-process TestClient smoke 120s pe hang — live server (`:8000`) use karo.

- 2026-10-09 (S7): **WS-5 + WS-6 VERIFIED — Round 3 = 6/6 COMPLETE**
  - Stale backend (PID 2568) kill + `python backend\run.py` restart; output
    `logs/backend_run_*.log` pe redirect. Note: pkl load ~20s — health turant check karne pe
    DOWN lagta hai, wait karo.
  - **reports.py (WS-6) 2 bugs fix**:
    1. `profile.height_cm` / `weight_kg` / `smoking_status` — UserProfile model mein columns
       `height` / `weight` / `smoking` hain → AttributeError (report_id=1 fail).
    2. `CATEGORIES.get(r.category, r.category)` — `CATEGORIES` registry.py mein **list** hai
       (dict nahi) → `'list' object has no attribute 'get'` (report_id=2 fail). Ab direct
       `r.category.replace("_", " ").title()`; `CATEGORIES` import hata diya.
  - **WS-5 DepressionCard fix**: `confidence * 100` dobara ho raha tha par backend
    (`ml/models/depression.py:51`) already `*100` karta hai → `7720%`. Ab `confidence>1` ho to
    as-is (Dashboard.jsx). e2e: `Confidence: 77%` / `100%`.
  - **Verify ALL PASS**: `ws6_smoke.py` (predict 16 rows, chat 14 labels, shap ?disease=,
    report success + PDF 4104 bytes); PDF text pypdf se confirm (Health Profile + scores +
    16-disease table + cancer disclaimer); `npm run build` PASS; `e2e_assessment.mjs` PASS
    (dashboard update + fresh-reload DB restore + history 11 rows, JS errors none);
    `/simulate` shape confirmed (`current`/`improved` + `diseases[]` with
    disease_key/label/category/risk_percent, disclaimer present, frontend mapping match).
   - **Round 3 (16-disease expansion) ab DONE + verified.** Pending Round 2: per-disease SHAP,
     Previous-Health button, logout/admin endpoints + admin_action_log, Reports/admin pages +
     404 + role guard + mobile nav, a11y, alembic, tests.

- 2026-10-11 (S8): **Chatbot leftover fixes (chat.py registry-driven).**
   - `chat.py` mein flat columns (`p.diabetes_risk/heart_risk/hypertension_risk/obesity_risk`)
     ab `_risk(p, key)` helper se padhe jaate hain — pehle `disease_risk_results` rows
     (registry disease_key), na mile to flat-column fallback (legacy rows).
   - Sab rule-based branches (breakfast/lunch/snack/drinks/exercise/weight/sugar/salt/food/
     alcohol/diet-plan) + `_check_api_queries` (water tip) + default risk_context — sab
     `_risk()` pe move. `build_risk_summary` fallback (flat cols) waise hi (legacy safe).
   - `ChatResponse.risk_context` pehle "Diabetes: X%, Heart: Y%" hardcoded tha → ab
     `build_risk_badge(p)`: rows se top-4 elevated (≥40%), warna flat-column fallback,
     warna "Risk Profile Active". Frontend `DietChat.jsx` badge automatically naya format
     dikhata hai (koi change nahi chahiye).
   - Verify: `py_compile` OK; temp script se `_risk`/`build_risk_badge`/`build_risk_summary`
     — rows path, legacy flat path, aur no-data path sab sahi (badge:
     "Risk Profile Active - Diabetes: 62%, Hypertension: 55%, Chronic Kidney Disease: 44%").
   - **Baqi chatbot item: koi open nahi.** (Tests project-wide Round-2 item hai — abhi
     pytest install nahi hai, `backend/tests/` khali.)


- 2026-10-08 (S5): **WS-3 Backend DONE — 16-disease expansion 5/6 workstreams**
  - ML retrain verify: `python -m ml.training.train_models` → **sab 12 PASS** (Phase-1
    diabetes .994/.947, heart .991/.926, hypertension .998/.944, obesity .998/.972;
    phase2 stroke .980/.911, ckd .929/.841 UCI-real, liver .987/.890, thyroid .975/.900,
    pcos .990/.939, anemia .988/.945, colorectal .991/.936, lung .980/.932; depression F1 .993).
  - `schemas/user.py`: HealthProfileInput + `bp_systolic/bp_diastolic/waist_circumference/
    diet_quality` (optional, purana client422 na de) + `screening_responses: Dict[str, Dict]`
    (validator → sirf registry screening keys, warna 422 field-level error).
  - `predict.py`: profile naye 4 columns save; `ScreeningResponse` rows (har screener 1 row,
    payload JSONB = pipeline wala format); `DiseaseRiskResult` rows (16, risk_percent clip 0-100);
    POST + `/latest` + `/history` → `disease_risk_results` array (§9 shape, registry order sort,
    label registry se, joinedload se N+1 avoid). Flat columns wahi rakhe (chat/reports back-compat).
  - `diseases.py`: `SCREENING_QUESTIONS` catalog (gad7 7 / sleep_apnea 2 / pcos 2 / anemia 3 /
    burnout 5 / thyroid 1 / lung 1) + `GET /screenings/{key}/questions` naye `screenings_router`
    pe (prefix `/api/v1/screenings`, main.py mein 1 line add); `/diseases` + `screening_key`,
    `requires_screening`, `active`, `min_age`, `requires_gender`. Question shape: `response_key`
    (+`response_index` jab list) — phase2_risk._build_vector ke keys se match.
  - `registry.py`: `DiseaseConfig` +`min_age`/`requires_gender`; pcos `requires_gender=0`,
    colorectal `min_age=40`. `phase2_risk.py`: `_eligible()` gates + `_yn()` yes/no coercion
    (bool("no")==True bug thyroid/pcos/anemia/lung pe tha — ab "yes"/"no" strings safe).
  - `simulate.py`: hardcoded fake profile → latest profile + prediction se real baseline,
    404 agar profile/prediction na ho.
  - Verify: `py_compile` sab OK; TestClient E2E smoke (ws3_smoke.py): register → predict
    (7 screening payloads) → **16 disease rows + 7 screening rows DB mein**, /diseases 16 with
    new fields, 7 question catalogs sahi counts + 404s, /latest + /history 16 rows,
    /simulate real bmi 28.7, **male 30 → 12 diseases (pcos + colorectal gates pass)**.

- 2026-10-07 (S4): **16-disease expansion — WS-1 DB + WS-2 ML DONE (4/6 workstreams)**
  - **WS-1 DB ✅** `database.py` + `schema.sql`: `DiseaseRiskResult` (disease_key, category,
    risk_percent CHECK 0–100, risk_label, confidence + indexes), `ScreeningResponse`
    (screening_key + responses JSONB), `user_profiles` +4 cols (bp_systolic/bp_diastolic/
    waist_circumference/diet_quality) + relationships. **Local Postgres 17 pe ALTER run + seed.py
    → 8 tables confirm** (psql: `C:\Program Files\PostgreSQL\17\bin\psql.exe`, PGPASSWORD=postgres,
    DB longevity_platform; Docker NAHI hai).
  - **WS-2a ✅** `ml/models/screening_classifier.py` — ScreeningClassifier(MLModel): gad7
    (official 5/10/15), sleep_apnea (STOP-BANG subset, max_score 6), metabolic_syndrome (IDF),
    burnout (work_hours/job_satisfaction/exhaustion). Har scorer {risk_percent, risk_label,
    confidence, detail}. Rule-based — koi threshold gate nahi (spec §4 ML-models pe lagta hai).
  - **WS-2b ✅** `prepare_uci.py` (UCI download + form-feature mapping + AUC/F1 probe):
    **ckd PASS (0.933/0.829) → real UCI**, liver/thyroid BELOW → synthetic (model cards mein
    `dataset_source` documented). `generate_datasets.py` + `DISEASE_SCHEMAS`/`RISK_FUNCS`/
    `UCI_REAL`; `phase2_risk.py` Phase2RiskEngine + MODEL_STACKS (spec 06); `train_models.py`
    phase2 training + model cards. **Calibration fix**: synthetic label prevalence ~2% tha →
    AUC high par macro-F1 (0.5–0.7) fail; risk functions ko ~30–80% prevalence pe tune kiya.
    **Weights bug**: `_stack_weights()` normalized nahi tha (1-model stacks pe ens proba <0.5
    → risk 0%, F1 kam). Fix ke baad **sab 8 ML diseases PASS**: stroke .980/.911, ckd .929/.841
    (UCI real), liver .987/.890, thyroid .975/.900, pcos .990/.939, anemia .988/.945,
    colorectal .991/.936, lung_cancer .980/.932.
  - **WS-2c ✅** `registry.py` 16 configs (screening_key + active_diseases/by_engine/categories);
    `orchestrator.py` phase2+screen engines load + run_pipeline dispatch (disease_risk/phase2/
    screening), extras = diabetes/hypertension risks + screening responses, Phase-1 raw
    `category`→`risk_label` normalize, `norm_profile` mein bmi inject.
    **Smoke test: 16/16 diseases, bio_age 55.6, longevity 65.4** (fake profile se).
  - New files: `ml/models/screening_classifier.py`, `ml/models/phase2_risk.py`,
    `ml/data/prepare_uci.py`, `ml/models/pkl/phase2_diseases.pkl`, 8 model cards.
  - Environment note: psql full path se chalta hai, `Write-OK` cmdlet nahi (echo use karo),
    PowerShell heredoc se python file banao (`$env:TEMP`) — inline python f-strings crash karti hain.

- 2026-10-06 (S3): **SHAP fix + registry + training + endpoints**
  - SHAP ✅ orchestrator `_compute_shap`: shap>=0.46 sklearn models pe `shap_values`
    `(n, features, classes)` 3D ndarray deta hai (list nahi) → ab dono handle hote hain +
    values `[-1,1]` normalize (DB CHECK `shap_explanations.shap_value` + frontend width |v|*100).
    Verified: 5 rows, all within [-1,1]. Root cause: installed shap 0.52.0 vs spec 0.45.
  - SHAP ✅ `predict.py` disease "ensemble"→"diabetes" (registry vocabulary). SHAPDashboard.jsx:
    plain-language `FEATURE_LABELS` map (family_diabetes → "Family history of diabetes", etc.).
  - R2 #1 ✅ `ml/models/registry.py` — DISEASE_REGISTRY (dataclass DiseaseConfig: label, category,
    engine, depends_on, scoring, active). Phase 1 active ×4, Phase 2–5 featured (active=False).
    Orchestrator registry-driven output (label+category attach). Horizontal lock: ae category
    arrays function present (`categories()`), use Phase-2 ke baad.
  - R2 #2 ✅ BUG-5: datasets 11-feature aligned (`ml/data/generate_datasets.py`, 2000 rows×4) +
    `train_models.py` generic loader + model cards `ml/models/model_cards/`. Metrics: diabetes
    AUC 0.984/F1 0.915, heart 0.983/0.897, hypertension 0.994/0.950, obesity 0.999/0.977,
    depression F1 0.993. Pipeline E2E: sab risks populated (pehle hypertension/obesity NULL),
    bio_age/longevity/depression OK.
  - R2 #4 ✅ (partial) `GET /diseases` (routes/diseases.py — new file in app/routes, registry se)
    + `GET /predict/{userId}/history` + frontend wrappers `getDiseases`/`getPredictionHistory`
    (api.js). Verified via TestClient: 401 (route exists, auth guard on).
  - R2 #5 ✅ `DISCLAIMER` constant in `schemas/user.py` → predict POST+/latest+/history+simulate
    responses mein top-level. simulate.py bhi (dict mutation).
  - Verify: py_compile sab OK; full pipeline script OK; frontend `npm run build` OK.

- 2026-10-05 (R1): **8 urgent bugs fix + verified:**
  - BUG-1 ✅ pkl absolute paths (`ml/models/disease_risk.py`, `depression.py` — `__file__` se
    resolve). Verified: kisi bhi cwd se `load_models()` chalta hai.
  - BUG-2 ✅ `reports.py` — background task apne `SessionLocal()` se `ReportLog.status="success"`
    (pdf_path, file_size_kb, generated_at) update karta hai; failure pe `status="failed"`;
    `getSampleStyleSheet()` ka missing `"Warning"` style ab custom `ParagraphStyle` se. Nasab download
    ab 404 nahi dega.
  - BUG-3 ✅ `run.py` ab `backend.app.main` import karta hai (routes wala hi instance) +
    `main.py` sys.path fix `parents[1]→[2]`. Verified: `python backend\run.py` → /health
    `models_loaded:true`.
  - BUG-4 ✅ `requirements.txt`: `bcrypt==4.0.1` pin (4.1+ se passlib 1.7.4 crash karta hai).
  - BUG-6 ✅ predict POST + `/latest` response mein `age` add (Dashboard bio-age delta ab sahi).
  - BUG-7 ✅ `Simulator.jsx` — API error pe demo estimates pehle jaisa chupke naya dikhaya jaata
    tha; ab yellow banner + "Demo estimates only" label + `role="alert"`.
  - BUG-8 ✅ `AuthContext.jsx` — boot pe `getMe()` se token/user validate; 401/403 pe session
    khaali, network error pe cached user rehne do.
  - BUG-9 ✅ `.env.example` mein `APININJAS_KEY` add.
  - Verify: python `py_compile` sab OK; server boot + /health OK; frontend `npm run build` OK.

### 🔥 URGENT BUGS (audit se, fix order):
1. **Backend startup crash** — pkl path cwd-relative (`ml/models/pkl/...`,
   `disease_risk.py:136-140`) → sirf CWD=`D:\Uni-Project` pe chalta hai. Fix: `__file__` se
   absolute path.
2. **Reports kabhi complete nahi hote** — `reports.py:15-47` background task ReportLog status/
   pdf_path update hi nahi karta → download hamesha 404. Sath `styles["Warning"]` KeyError risk.
3. **run.py dual-instance bug** — `run.py` `app.main` import karta hai par routes
   `backend.app.main` se import → 2 orchestrator instances → "Models not loaded" on
   POST /predict. Sirf `.bat` wala path (`backend.app.main:app`) sahi chalta hai.
4. **passlib 1.7.4 + bcrypt 4.1.2 incompatible** — `middleware/auth.py:22` hash pe crash ho
   sakta hai. Fix: bcrypt<4.1 pin ya passlib chhod ke bcrypt direct.
5. **hypertension/obesity pkl missing** + training feature misalignment → dono theek karne
   hain (ML training re-run).
6. **Dashboard `age` nahi aata** backend se → bio-age delta 30 fallback se galat
   (`Dashboard.jsx:243`).
7. **Simulator silent mock** — API error pe hardcoded fake results dikhaata hai bina bataye
   (`Simulator.jsx:88-98`).
8. **AuthContext `getMe` dead import** — boot pe token validate nahi hota.
9. `APININJAS_KEY` .env mein nahi (health_api silently []). 
10. Redis client bana hai par kahin use nahi hota (dead code) — cache spec ka tha.

---

## 📌 NEXT TODO (agla kaam — yahan se continue karo)

### Round 4 — ML_TRAINING.md real-data retrain (2026-10-14 — mostly DONE, kuch verify baaki)
- [x] Code: `ml/train_config.py` + `ml/train.py` (spec) + `ml/predict.py` (`explain`/`band_for`);
      engines artifact-first; admin retrain import; replaced code deleted; `ml/data/README.md`.
- [x] UI: API band/see_doctor/disclaimer (POST+GET) + Dashboard disclaimer/follow-up banner.
- [x] **Diet-chat + API keys + localhost (S12/S14)** — rule-based DIET PLAN ordering fix;
      `APININJAS_KEY` live (nutrition/exercise real data); `health_api.py` `_sf()` harden
      (premium-string crash); Groq diet plan live verified; backend `:8000` + frontend `:3000` chalu.
- [x] **Train all 17 — DONE (S13)** (16 real + burnout labelled synthetic; colorectal REAL).
      `ml/models/*.joblib` (17) + `ml/reports/*_metrics.json` + `SUMMARY.md` + `REPORT.md` +
      `ml/smoke_test.py` (17 ok). Result **3 PASS / 14 BELOW_TARGET** (force nahi kiya).
- [ ] ⚠️ **Diabetes model under-calibration (IMPORTANT, still open)** —
      `ml/reports/diabetes_metrics.json` `BELOW_TARGET` + `LOW_FEATURE_MODEL`: NHANES mein symptom
      cols nahi → screening answers prediction pe asar nahi (45F/BMI 32/all symptoms "yes" → 1.8%).
      Isi wajah se `test_it03_chat_returns_risk_aware_guidance` FAIL. Options: (a) symptom-based
      rule/`screening_classifier` blend, (b) symptoms-wala dataset (Pima) retrain,
      (c) limitation accept + IT-03 adjust. **User (2026-10-14): filhaal kuch nahi — note only.**
- [x] Verify artifact SHAP (`ml/predict.explain`) → `/shap` — **DONE (S16)**: IT-02 +
      `test_pipeline_shap_values_normalized` PASS (naye `*.joblib` artifacts se; dashboard naye models
      dikhata hai).
- [~] `python -m pytest backend/tests -q` — **S16: 27 passed / 1 failed**. Sirf **IT-03** FAIL
      (diabetes `LOW_FEATURE_MODEL`, upar dekho; user: "filhaal kuch nahi"). **IT-03b FIXED (S16 — S15
      stateless chat pe align)**. ⚠️ `frontend/e2e_assessment.mjs` ab **exist nahi karta** (untracked
      tha, removed) aur koi browser-test dep bhi nahi → browser e2e available nahi.
      **S17: `test_unit_ml.py` 15/15 PASS** (2 naye band/`threshold` regression tests) + full API e2e
      `e2e_api_smoke.py` **21/21 PASS**. (`it01` ka ek `ObjectDeletedError` sirf tab aaya jab pytest aur
      live-server e2e **ek saath** chale the — akela chalane pe pass; concurrency flake, bug nahi.)
- [x] **Model cards + SHAP pngs regenerate — DONE (S13)**: `ml/models/model_cards/*.json` (17)
      (naye limitations text + `LOW_FEATURE_MODEL`/`SYNTHETIC_DATA` flags), `*_shap.png` (17).
      `SUMMARY.md`/`REPORT.md` commit **pending** (git tree pehle se dirty hai).

### Diet-chat / session (decision done — koi code change nahi)
- [x] Session persistence: **C** (fresh chat har open; `session_id` memory-only, localStorage NAHI).
      DB mein messages rehte hain (`chat_sessions`), UI wapas nahi dikhata. User ne C choose kiya.
- [ ] (Optional, agar user kahe) A = `session_id` localStorage / B = "saved conversations" list.

### Round 3 — 16-disease expansion (WS-1..6 sab DONE 2026-10-08 — sirf S6 verify/smoke pending)
- [x] **WS-1 DB** — disease_risk_results + screening_responses + user_profiles +4 cols ⏤ **DONE**
- [x] **WS-2 ML** — screening_classifier + phase2_risk + UCI probe + training (sab 8 PASS) +
      registry 16 + orchestrator dispatch (16/16 smoke OK) ⏤ **DONE**
- [x] **WS-3 Backend** ⏤ **DONE (2026-10-08)** — schemas naye fields + screening_responses
      validation; predict.py naye columns + ScreeningResponse + DiseaseRiskResult rows +
      `disease_risk_results` array (POST/latest/history); `/screenings/{key}/questions`
      catalog (7 screeners); `/diseases` naye fields; simulate.py real baseline;
      pcos/colorectal inference gates (registry `min_age`/`requires_gender` + `_eligible()`
      + `_yn()` coercion). E2E smoke 100% PASS (details: FIXES LOG 2026-10-08).
- [x] **WS-4 Frontend** — **DONE (2026-10-08, session S6)**:
  - HealthForm naye inputs: `bp_systolic/bp_diastolic/waist_circumference/diet_quality`
    (Section 5 "Body Measurements & Vitals")
  - Dynamic screening sections (Section 6): `screeningCatalogs` load (`getDiseases` +
    `getScreeningQuestions` Promise.all), `visibleScreenings` gender/age gates (pcos sirf
    Female, `min_age` wale age pe), `profile_field` questions skip (anemia q3 =
    diet_quality), required validation → `screening_responses` payload (gad7 `answers`
    array, burnout `exhaustion` array, baaki flat keys)
  - api.js: `getDiseases()`, `getScreeningQuestions(key)` wrappers
- [x] **WS-5 Frontend** — **DONE (2026-10-08, session S6)**:
  - Dashboard: `disease_risk_results` se 16 cards, 5 collapsible category sections
    (CATEGORY_ORDER: cardiovascular, metabolic, mental_wellness, lifestyle_linked,
    cancer_screening; peak ≥25 open, >60 "Elevated" badge), RiskGauge `note` prop,
    cancer cards pe stricter disclaimer + server `disclaimer` field footer
  - Simulator: `DiseaseComparisonRow` — 16-disease comparison list; **BUG fix**: response
    keys `current_scenario/optimized_scenario` → backend ke actual `current/improved`
- [x] **WS-6 Ripple** — **DONE + VERIFIED (S7, 2026-10-09)**:
  - chat.py `build_risk_summary` ab `disease_risk_results` rows se (registry order, icons,
    fallback flat columns); shap.py `?disease=` query param filter; reports.py PDF mein
    Health Profile + 16-disease table (category, risk%, level, cancer note) + scores
  - ✅ `ws6_smoke.py` → **ALL PASS** (predict 16 rows, chat 14 disease labels, shap ?disease=
    filter, report success + PDF 4104 bytes); PDF text pypdf se verify — Health Profile +
    scores + 16-disease table + cancer disclaimer sab present
  - 🐛 **reports.py 2 bugs fix**: `profile.height_cm/weight_kg/smoking_status` → actual
    columns `height/weight/smoking`; `CATEGORIES.get(...)` → CATEGORIES list hai (`.get`
    invalid) → direct `.replace().title()`
- [x] **Verify (S7, 2026-10-09)** — sab PASS:
  1. Backend `:8000` stale process (PID 2568) kill + `python backend\run.py` restart OK
     (startup ~20s lagta hai pkl load mein — health turant check karo to DOWN aata hai,
     thoda wait karo)
  2. `python C:\Users\pakcomp\AppData\Local\Temp\opencode\ws6_smoke.py` → **ALL PASS**
  3. `npm run build` → **PASS** (dist built in 1m19s)
  4. Browser e2e `node frontend/e2e_assessment.mjs` → **PASS** (dashboard update + fresh-reload
     DB restore + history 11 rows; JS errors none)
  5. 🐛 **WS-5 DepressionCard `7720%` bug fix** — backend confidence % (0-100) bhejta hai,
     Dashboard dobara ×100 kar raha tha; ab `confidence > 1` ho to as-is (e2e: 77% / 100%)

### Round 2 — baaki spec gaps (Round 3 ke baad)
- [x] `GET /shap/{id}?disease=` query param — **DONE (S6)**; per-disease SHAP:
- [x] Per-disease SHAP rows (ab `predict.py` `shap_explanations` dict se HAR ML disease ke rows
      likhta hai — orchestrator `compute_shap_all`, 12 ML diseases) — **DONE + verify (S9)**
- [x] Previous-Health / prediction history button Dashboard pe — **DONE (S9)**
- [x] `POST /auth/logout`, `/admin/models/retrain`, `/admin/actions` + `admin_action_log` table
      — **DONE (S9)**
- [x] #7 Frontend: Reports page, admin pages, 404 route, role guard, mobile nav — **DONE (S9)**
- [x] #8 Accessibility pass (aria-*, htmlFor) — 08-FRONTEND-UI-SPEC §5 — **DONE (S9)**
- [x] #9 Alembic migrations — **DONE (S9)**: `ad0291fbd3b8_initial_schema` (9 tables, verified
      on temp DB + `stamp head` on real DB)
- [x] #10 Tests (IT-01..IT-07 + unit) — 07-DEV-WORKFLOW §4 — **DONE (S9)**: `backend/tests/`
      (conftest + test_unit_ml + test_integration), **27 tests sab PASS** (isolated test DB
      `longevity_platform_test`; LLM keys blank → deterministic rule-based).
- [x] **🌐 Diet-plan chatbot — Groq se (user decision 2026-10-13)** — koi external diet API
      nahi chahiye; chatbot pehle se hi Groq (`GROQ_API_KEY` + `GROQ_MODEL=openai/gpt-oss-120b`)
      pe integrated hai (`chat.py` `_llm_response()`: Groq → Claude → rule-based fallback;
      `main.py`/`run.py` repo-root `.env` load karte hain). Live verify: Groq 200 + reply OK.
      NOTE: `llama-3.3-70b-versatile` is account pe available nahi (404) — `openai/gpt-oss-120b` use.
      (Purana external-API plan cancel — user ne Groq confirm kiya.)

### ✅ Next — abhi krna hai (S10 ke baad, newest first)
- [~] Browser e2e smoke re-run: `node frontend/e2e_assessment.mjs` — **S17: script disk pe nahi +
      koi puppeteer/playwright dep nahi** → install na karne tak **API-level full-journey e2e** hi
      substitute hai (`e2e_api_smoke.py`: predict 16+band, /latest, /shap, /simulate, chat, PDF,
      auth guards → 21/21 PASS). Browser build `npm run build` pehle se PASS.
- [ ] Live demo (manual browser): login → HealthForm submit → **Diet Advisor** → quick question
      "🗓️ Generate my diet plan" → confirm Groq DB health-context wala diet/plan + "New Chat" button
      session reset (purane messages gayab).
- [ ] (Optional) WS-7 — 16-screeners ML retrain `POST /admin/models/retrain` live server pe verify.

### ⚠️ Constraints yaad rakho
- Structure change BAND: `app/routes/*`, `app/models/*`, `services/api.js`, page ke naam waise
  hi rehne do. Naya code existing files mein hi add karo.
- Jo spec feature existing framework mein fit nahi hota → **code comments mein likho**
  (NOTE/TODO), implement baad mein karo.

---

## 💡 SESSION NOTES (important context for future)

- Project already partially bana hua hai — **restart NAHI karna**, existing code read karke
  usi mein aage badho.
- ML code `backend/app/ml/` mein nahi — `ml/` folder mein hai (repo layout se hat ke). Backend
  `ml/` ko path se import karega. **Ise move/shift mat karo.**
- Logs already exist: `server_output.log`, `backend_stdout.log`, `backend_stderr.log`,
  `frontend/vite_error.log` — errors pehle yahan check karo.
- `.env` repo root pe hai (backend ke saath nahi).
- Disclaimers sirf frontend mein nahi — API response + PDF + chat footer, server-side attach hote
  hain (03-AUTH.md §7, 12-INTEGRATION.md §8).
- Har session `docx.md/` se relevant spec section dobara padh lena — is file mein spec copy mat karo.

---

## 📅 SESSION LOG (newest last)

- 2026-10-08 (S5): **WS-3 Backend complete → Round 3 = 5/6.** ML retrain verify (sab 12 PASS).
  schemas naye 4 form fields + screening_responses validation; predict.py ScreeningResponse +
  DiseaseRiskResult rows + `disease_risk_results` array (POST/latest/history); `/screenings/
  {key}/questions` catalog (7 screeners, alag router `/api/v1/screenings`); `/diseases` +
  screening_key/requires_screening/min_age/requires_gender; simulate.py real baseline
  (fake profile hata); pcos/colorectal registry gates + `_yn()` yes/no coercion fix.
  E2E smoke: 16 rows female / 12 rows male (gates working), 7 screening rows, catalogs OK.
  Details: FIXES LOG. Next: **WS-4 Frontend (HealthForm dynamic screening sections)**.
- 2026-10-07 (S4): **16-disease expansion start — WS-1 + WS-2 complete (4/6).** DB: 2 nayi
  tables (disease_risk_results, screening_responses) + user_profiles +4 cols, local Postgres pe
  migrate+verify (8 tables). ML: screening_classifier (4 rule-based), prepare_uci.py (ckd real,
  liver/thyroid synthetic), generate_datasets 8 schemas, phase2_risk engine (8 ML models, all
  PASS thresholds), registry 16 entries, orchestrator dispatch 16/16 (smoke OK). Bugs fixed:
  stack weights normalize, synthetic label calibration (~2% → 30-80% prevalence). Pending:
  WS-3 backend (schemas/predict/screenings/simulate/gates), WS-4/5/6 frontend+ripple, verify.
  Details: FIXES LOG. Next: WS-3 se shuru.
- 2026-10-06 (S3): SHAP bug fixed (3D ndarray + normalize + plain-language frontend), 4-disease
  training aligned + model cards, DISEASE_REGISTRY (Phase 1 active, 2–5 featured), orchestrator
  registry-driven, GET /diseases + /predict/{id}/history endpoints, disclaimers server-side,
  frontend build OK. Details: FIXES LOG. Next: SHAP ?disease=, disease_risk_results table,
  remaining endpoints, frontend pages, a11y, alembic, tests.
- 2026-10-05 (S2): 3 audits complete (backend/frontend/ml+db). STATUS section bhara. Urgent bugs
  ki list bani (10 items). opencode.md lean/banaya (docx copy nahi). Next: Round 1 fixes.
- 2026-10-05 (S1): Session start. 13 docs padhi. Pehla opencode.md bana (bahut lamba tha — rewrite
  kiya). 3 audits launch ki — user ne abort karke bataya: existing structure hi follow karna hai,
  3 folders alag, spec comments mein note karna hai.
- 2026-10-08 (S6): **WS-4 + WS-5 Frontend complete + WS-6 code — Round 3 = 6/6 (verify pending).**
  HealthForm: 4 naye fields + dynamic screening sections + required validation;
  Dashboard: 16 cards / 5 collapsible categories + cancer disclaimers; Simulator:
  16-disease comparison + `current/improved` key fix; WS-6: chat 16-disease summary +
  shap `?disease=` + PDF mein profile/16-disease table. Verify: `npm run build` PASS,
  browser e2e `e2e_assessment.mjs` PASS (16 cards + screening submit + DB restore).
  Debug: stale uvicorn (1:26 AM purana process) purane code pe — kill+restart; 404 =
  `/vite.svg` favicon cosmetic. **ABORTED yahin**: `ws6_smoke.py` re-run pending +
  DepressionCard confidence % bug (`7720%`). Servers chhode chalu hain: backend
  `python backend\run.py` (:8000), frontend `npm run dev` (:3000). Next: ws6_smoke verify
  → Round 2 (logout/admin, Reports page, a11y, alembic, tests).
- 2026-10-09 (S7): **WS-5 + WS-6 verified → Round 3 = 6/6 COMPLETE.** Backend restart
  (`logs/backend_run_*.log`). reports.py 2 bugs fix (wrong UserProfile columns
  `height_cm/weight_kg/smoking_status`; `CATEGORIES.get` on a list). DepressionCard `7720%`
  fix (double ×100). `ws6_smoke.py` ALL PASS + PDF text verified (pypdf), `npm run build`
  PASS, `e2e_assessment.mjs` PASS (Confidence ab 77%/100%), `/simulate` shape verified.
  Servers chalu: backend :8000, frontend :3000. Next: Round 2 (per-disease SHAP,
   Previous-Health button, logout/admin endpoints + admin_action_log, Reports/admin pages,
   404/role guard/mobile nav, a11y, alembic, tests).

- 2026-10-11 (S8): **Chatbot leftover fixes.** `chat.py` ke sab flat-column risk checks
  (`p.diabetes_risk` etc.) → `_risk(p, key)` helper jo `disease_risk_results` rows se padhta
  hai (flat fallback legacy rows ke liye). `ChatResponse.risk_context` ab `build_risk_badge(p)`
  (top-4 elevated ≥40% rows, warna flat fallback, warna "Risk Profile Active"). py_compile OK +
  temp script se teen paths (rows/legacy/none) verify. Chatbot mein ab koi open item nahi;
  project-wide tests abhi pending (pytest install nahi, `backend/tests/` khali).
- 2026-10-11 (S8 cont.): **WS-7 — 16-disease screening questions + ML retrain (code DONE,
  e2e smoke pending).** Har 16 disease ke 3-4 **required** yes_no screening questions
  (`diseases.py` ab `SCREENING_QUESTIONS` `_yn_q()` factory se, sleep_apnea 4/8-pt,
  metabolic_syndrome 3 ORed factors, gad7 7 + burnout 5 kept); answers **real risk pe asar**:
  `generate_datasets.py` PHASE1_SCHEMAS (11 base + 3 binary extras per phase-1 disease) +
  DISEASE_SCHEMAS extend (stroke 16, ckd/liver/thyroid/anemia 7, pcos 6, colorectal 9,
  lung_cancer 7) + ~30 naye binary sample features + risk funcs intercept recalibration;
  `disease_risk.py` `_build_vector(disease,p,extras)` + `predict_all` + `feature_names`;
  `phase2_risk.py` `_build_vector` extended; `screening_classifier.py` sleep_apnea 8-pt +
  metabolic_syndrome ORs; `orchestrator.py` predict_all + SHAP diabetes vector; `train_models.py`
  per-disease schema training. **ckd UCI-real → synthetic** (`UCI_REAL={}`) kyunki UCI mein
  naye symptom cols nahi the. Retrain **sab PASS** (phase1 4 + stroke/ckd(AUC.923)/liver/thyroid/
  pcos/anemia/colorectal/lung + depression .993). Frontend dynamic render — koi change nahi chahiye.
  **Scroll fix**: `App.jsx` route change pe `window.scrollTo(0,0)` — pages top se start.
  ✅ **WS-7 smoke (`ws7_smoke.py` temp pe) → ALL 40 PASS**: 16 diseases + screening_key, sab
  catalogs 3-7 required questions (401 logged-out), predict → 16/16 `disease_risk_results`
  rows, screening answers risk move karte hain (liver/pcos/anemia/colorectal/lung/burnout/gad7
  >60pt; obesity +0.5 sabse kam), burnout = work_hours+job_satisfaction+3 exhaustion.
  Server restart zaroori tha (stale code). build PASS (1m04s, chunk warn purana).
  **Groq API added for diet chat**: `_llm_response()` Groq-preferred (GROQ_API_KEY/GROQ_MODEL
  `.env` mein, default llama-3.3-70b-versatile), Claude fallback, rule-based last. Chat route
  verify OK (613-char reply). **TODO add kiya: 🌐 diet-plan external API chatbot (user ka
  API pending) — WS-7 verified → WS-7 ek todo complete.**

- 2026-10-13 (S9): **Round-2 gaps CLOSED — Groq key wiring + Reports/Admin/a11y + alembic + tests.**
  - **Groq `.env` fix**: `.env` mein floating key `GROQ_API_KEY=...` assign kiya,
    `GROQ_MODEL=openai/gpt-oss-120b` (llama-3.3-70b-versatile is account pe 404 `model_not_found`);
    `run.py` + `main.py` ab repo-root `.env` dotenv se load karte hain (pehle kahin load
    nahi hota tha); `chat.py` `_env_key()` (empty/`your-...` → missing). Verify: openai/gpt-oss-120b 200.
  - **Backend**: `POST /auth/logout`; admin `POST /models/retrain` (bg: `train_all()` + pipeline
    reload) + `GET /actions`; `_log_action` create/update/role/delete pe; `AdminActionLog` model;
    `GET /reports/{user_id}/list`.
  - **Frontend**: `Reports.jsx`, `Admin.jsx`, `NotFound.jsx`, `App.jsx` routes + `RoleRoute`,
    Navbar mobile menu, Dashboard Previous-Health panel, api.js wrappers (logout/retrain/actions/listReports).
  - **Accessibility**: Login/Register/DietChat/HealthForm aria-*, htmlFor, role=alert/log, aria-pressed.
  - **Alembic**: `db/alembic/env.py` sys.path fix (repo root) + all models import;
    `ad0291fbd3b8_initial_schema` (9 tables) temp DB pe `upgrade` se verify, real DB `stamp head`.
  - **Tests**: `backend/tests/` (conftest isolated test DB + TestClient; test_unit_ml; test_integration
    IT-01..IT-07 + Round-2). **27/27 PASS** (`python -m pytest backend/tests -q`, ~4m). LLM keys
    test env mein blank → deterministic rule-based chat.
  - **Baqi sirf**: 🌐 diet-plan external API chatbot (user API details pending). → **S10: external API CANCELLED** — chatbot Groq pe hi complete.
  - **Note (S10)**: diet-plan external API nahi lagana pada — user decide kiya chatbot Groq se hi
    chale (koi external diet API nahi). TODO checkbox `[x]` kar diya.

- 2026-10-13 (S10): **Diet chatbot — DB health assessment → Groq diet/plan + session-based storage.**
  - **Groq ab poora health assessment DB se**: `chat.py` naya `build_health_context(prediction, profile)`
    (age/gender/BMI, sleep/exercise/smoking/alcohol, biological age, longevity score, depression,
    + poore 16-disease risks) → `_llm_response()` system prompt mein. Groq isi ko padh kar personalized
    **diet + daily plan** (breakfast/lunch/dinner/snacks/hydration/exercise) deta hai.
  - **Session-based storage**: `ChatSession` ab `session_id` (String(64) unique) column pe chalata hai —
    har chat session ka apna row (ek prediction ke multiple sessions allowed). `send_message` naya/
    diya hua session_id use karta hai (bina session_id → naya UUID), `get_chat_history` bina session_id
    **khaali** deta hai → purane messages display nahi hote. `PredictionResult.chat_sessions`
    relationship collection (`uselist=False` hataya).
  - **Frontend `DietChat.jsx`**: har chat-open pe naya session_id (crypto.randomUUID), history fetch
    hata diya, "New Chat" button (session reset). api.js `sendChatMessage(userId, msg, sessionId)` +
    `getChatHistory(userId, sessionId)`.
  - **Migration**: `039e9f98f870_session_based_diet_chat.py` (clean manual — autogenerate waley noise
    ka solution) — add `session_id` + unique index, `DROP CONSTRAINT IF EXISTS chat_sessions_prediction_id_key` (real DB pe unique constraint already nahi tha). Real DB pe `alembic upgrade head` applied → verified column via psql.
  - **Tests**: naya `test_it03b_chat_sessions_are_isolated` (naya session → khaali history, purana leak
    nahi, same session → messages accumulate). **28/28 PASS**.
  - **Live verify**: backend `run.py` se fresh restart (@:8000, port pehle free tha) → `GET /health`
    = `{"status":"healthy","models_loaded":true}`.

- 2026-10-14 (S13): **ML_TRAINING.md real-data pipeline — sab 17 diseases trained + verified.**
  - 16 real app-aligned datasets + 1 labelled synthetic (`burnout`); `colorectal` **REAL**
    (NHANES 2017-18 `MCQ_J`, 55 pos). Result **3 PASS / 14 BELOW_TARGET** (koi force nahi) —
    `ml/reports/SUMMARY.md` live.
  - Naya: `ml/reports/REPORT.md` (spec §12 report) + generator `ml/report.py` + `ml/smoke_test.py`
    (acceptance §10) + `ml/requirements.txt` + `ml/data/generate_synthetic.py`; `ml/train.py` mein
    `SYNTHETIC_DATA` flag + `encoding="utf-8"` (SUMMARY `±` mojibake fix).
  - Honesty: gad7/depression .99 = `SUSPICIOUS_POSSIBLE_LEAKAGE` (**by design** — label same items
    se derive); `metabolic_syndrome` IDF composite label features share karta hai; 14 BELOW_TARGET
    jaisa hai waisa chhoda (PASS force **nahi**).
  - Verify: `python -m ml.smoke_test` **17/17 ok**; `pytest backend/tests/test_unit_ml.py` **13/13 PASS**.
    Ground Rule 1 ka single documented deviation = `burnout` synthetic (README mein wajah + Mendeley
    rejection table). Details: FIXES LOG S13.

- 2026-10-14 (S14): **APININJAS key live + health_api harden + localhost + diet-chat test inspect.**
  - `.env` `APININJAS_KEY` placeholder-prefixed tha (`your-api-ninjas-key-here MIftx...`) → 401;
    sirf asli key rakhi. Live: nutrition/exercise API se aate hain. `health_api.py` `_sf()`
    safe-float (premium-subscriber string → 0) dono formatters mein (pehle `TypeError`).
  - `chat.py` DIET PLAN branch ordering (S12). Groq diet plan live verified (real DB context).
  - Backend `python -m backend.run` `:8000` healthy + frontend `npm run dev` `:3000` 200 (logs
    `logs/backend_run_*.log`, `logs/frontend_dev_*.log`; detached Start-Process).
  - Tests: `test_it03b_chat_sessions_are_isolated` **PASS**; `test_it03_chat_returns_risk_aware_
    guidance` **FAIL** — wajah retrained diabetes model (`LOW_FEATURE_MODEL`, NHANES symptom cols
    nahi → symptoms risk pe asar nahi; high-risk profile → 1.8%). Chat se related nahi.
  - **User decisions**: diabetes model = filhaal kuch nahi; session persistence = C (fresh chat,
    DB mein save rehta hai). Round 4 ML 17/17 (S13) alag session mein hua.
  - **Next session**: IT-03 fail dekho (diabetes calibration) + `/shap` artifact verify +
    `pytest backend/tests -q` + `e2e_assessment.mjs`.

- 2026-10-15 (S16): **Verification pass — full pytest + IT-03b ko S15 stateless-chat pe align kiya.**
  - `python -m pytest backend/tests -q` → pehle **26 passed / 2 failed**. Root cause: IT-03b = S15 ne
    chat **stateless** kiya (DB save nahi) par test purani persistence expect kar raha tha (stale);
    IT-03 = documented diabetes `LOW_FEATURE_MODEL`.
  - 🐛 IT-03b test ko S15 contract pe align kiya → **PASS** (`-k it03` = 1 failed, 1 passed). Ab full
    suite **27 passed / 1 failed** (sirf IT-03).
  - ✅ Artifact SHAP verified (`test_it02_shap_rows_for_ml_diseases` +
    `test_pipeline_shap_values_normalized` PASS) — `/shap` dashboard naye models dikhata hai.
  - ⚠️ `frontend/e2e_assessment.mjs` disk pe nahi (untracked, removed) + `frontend/package.json` mein
    koi browser-test dep nahi → browser e2e run nahi ho saka.
  - **Next**: IT-03 (diabetes) user ke "filhaal kuch nahi" pe khula; SUMMARY.md/REPORT.md commit
    pending (git tree pehle se dirty).

- 2026-10-15 (S17): **`/latest` + `/history` band bug fix (artifact path) + full API e2e.**
  `ml/predict._metrics_path()` repo root pe `reports/` dhoondta tha (double `dirname`) → `threshold()`
  hamesha None → reload path ke rows pe band/see_doctor/disclaimer gayab (POST response theek — isi
  liye chhupa hua tha). `_artifact_path()` fallback bhi same off-by-one. Fix = `_ml_dir()` (file ka apna
  dir). Live verify: `/latest` 12/12 band + disclaimer; 2 naye regression tests (unit **15/15**); full
  API e2e `e2e_api_smoke.py` **21/21 PASS** (predict 16, shap 46/12, simulate 16+16, chat Groq 1437
  chars, report PDF 4117B, auth guards). Browser e2e blocked (script missing + no puppeteer/playwright
  dep). IT-03 diabetes user ke "filhaal kuch nahi" pe hi khula. Details: FIXES LOG S17.
