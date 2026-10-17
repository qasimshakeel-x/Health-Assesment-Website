# Data Model — AI Longevity Intelligence Platform

PostgreSQL 16, SQLAlchemy 2.x ORM, Alembic migrations, 3NF. All tables: SERIAL PK,
`created_at`/`updated_at` audit timestamps.

## 1. Core Tables (from original SRS/SDD)

### `auth_users` (see `03-AUTH.md` §6 for the split-table rationale)
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| email | VARCHAR(255) UNIQUE | |
| password_hash | VARCHAR(255) | bcrypt |
| role | VARCHAR(20) | `user` \| `admin` |
| created_at | TIMESTAMP | |

### `user_profiles`
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| auth_user_id | INTEGER FK → auth_users.id | |
| name | VARCHAR(100) | |
| age | INTEGER | 18–120 |
| gender | INTEGER | 0=Female, 1=Male |
| height, weight | FLOAT | cm, kg |
| bmi | FLOAT | computed |
| sleep_hours | FLOAT | 3.0–12.0 |
| exercise_level | INTEGER | 0–4 |
| smoking | BOOLEAN | |
| alcohol | INTEGER | 0–7 drinks/week |
| family_history | INTEGER[] | [diabetes, heart, hypertension, cancer] |
| phq1..phq9 | INTEGER[9] (JSONB) | 0–3 each |
| created_at | TIMESTAMP | |

### `prediction_results`
id PK, `user_id` FK, `diabetes_risk / heart_risk / hypertension_risk / obesity_risk` (FLOAT 0–100),
`biological_age` (FLOAT), `longevity_score` (FLOAT 0–100), `depression_level` (VARCHAR),
`depression_confidence` (FLOAT), `created_at`.
> With the 16-disease expansion, this table either grows very wide or (recommended) splits — see §2.

### `shap_explanations`
id PK, `prediction_id` FK, `disease` (VARCHAR), `feature_name` (VARCHAR), `shap_value`
(FLOAT −1.0 to +1.0), `rank` (INT).

### `chat_sessions`
id PK, `prediction_id` FK (lazy-created on first message), `messages` (JSONB array of
`{role, content, timestamp}`), `system_prompt` (TEXT), `created_at`, `last_message_at`.

### `report_log`
id PK, `user_id` FK, `pdf_path` (VARCHAR 512), `generated_at`, `file_size_kb`,
`status` (success/failed).

### `admin_action_log` (new, required by `03-AUTH.md` §5)
id PK, `admin_user_id` FK → auth_users.id, `action` (VARCHAR — e.g. `delete_user`,
`retrain_model`), `target_id` (INTEGER, nullable), `timestamp`.

## 2. Schema Change for 16-Disease Expansion
Do **not** keep adding columns to `prediction_results` for every new disease — it won't scale past a
handful and breaks the "add a disease = one registry entry" goal in `02-ARCHITECTURE.md` §5.
Instead, normalize:

### `disease_risk_results` (replaces the per-disease columns on `prediction_results`)
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| prediction_id | INTEGER FK → prediction_results.id | |
| disease_key | VARCHAR(50) | e.g. `diabetes`, `stroke`, `ckd`, `pcos`, `lung_cancer` — matches `DISEASE_REGISTRY` key |
| category | VARCHAR(30) | cardiovascular / metabolic / mental_wellness / lifestyle_linked / cancer_screening |
| risk_percent | FLOAT | 0.0–100.0 |
| risk_label | VARCHAR(20) | Low / Moderate / High / Very High |
| confidence | FLOAT | nullable, model confidence if available |
| created_at | TIMESTAMP | |

`prediction_results` keeps only the cross-cutting aggregates: `biological_age`, `longevity_score`,
`depression_level`, `depression_confidence`, plus (new) `anxiety_level`, `anxiety_confidence`.

`shap_explanations.disease` should reference `disease_key` from the same vocabulary as
`disease_risk_results.disease_key` so SHAP rows join cleanly for any of the 16 diseases.

### `screening_responses` (new — holds the extra questions Phase 2–5 diseases need)
| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| user_profile_id | INTEGER FK → user_profiles.id | |
| screening_key | VARCHAR(50) | `gad7`, `sleep_apnea`, `pcos`, `anemia`, `burnout`, `thyroid`, `lung_cancer_exposure` |
| responses | JSONB | the actual answers for that screener, shape varies by key |
| created_at | TIMESTAMP | |

This keeps `user_profiles` from accumulating 20+ nullable columns as diseases are phased in —
each screener's questions live in its own JSONB blob, only written when that phase is enabled.

## 3. Data Dictionary (key fields)
| Attribute | Table | Type | Range/Format | Description |
|---|---|---|---|---|
| age | user_profiles | INTEGER | 18–120 | chronological age |
| bmi | user_profiles | FLOAT | 10.0–60.0 | auto-calculated |
| sleep_hours | user_profiles | FLOAT | 3.0–12.0 | avg nightly sleep |
| exercise_level | user_profiles | INTEGER | 0–4 | 0=Sedentary … 4=Very Active |
| smoking | user_profiles | BOOLEAN | — | current smoker |
| alcohol | user_profiles | INTEGER | 0–7 | drinks/week |
| family_history | user_profiles | INTEGER[] | [0,1]×4 | diabetes, heart, hypertension, cancer |
| phq1–phq9 | user_profiles | INTEGER[9] JSONB | 0–3 | PHQ-9 answers |
| risk_percent | disease_risk_results | FLOAT | 0.0–100.0 | ensemble/model probability |
| longevity_score | prediction_results | FLOAT | 0.0–100.0 | category-weighted composite |
| biological_age | prediction_results | FLOAT | 18.0–120.0 | penalty-formula estimate |
| depression_level | prediction_results | VARCHAR(20) | No/Mild/Moderate/Mod-Severe/Severe | PHQ-9 classification (5-tier, see `01-PRD.md`) |
| shap_value | shap_explanations | FLOAT | −1.0 to +1.0 | feature contribution |

## 4. Entity Relationships
```
auth_users (1) ───── (1) user_profiles
user_profiles (1) ───── (N) prediction_results
prediction_results (1) ───── (N) disease_risk_results     [NEW — replaces flat columns]
prediction_results (1) ───── (N) shap_explanations
prediction_results (1) ───── (0..1) chat_sessions          [lazy-created]
user_profiles (1) ───── (N) screening_responses            [NEW]
user_profiles (1) ───── (N) report_log
auth_users (1, admin) ───── (N) admin_action_log            [NEW]
```

## 5. Indexing
- B-tree: `user_profiles.id`, `prediction_results.user_id`, `disease_risk_results.prediction_id`,
  `disease_risk_results.disease_key`.
- Hash: `chat_sessions.prediction_id`.
- Unique: `auth_users.email`.

## 6. Migration Note
If the team already built the original flat `prediction_results` schema before reading this doc, write
an Alembic migration that: (1) creates `disease_risk_results`, (2) backfills the 4 existing disease
columns into rows of it, (3) drops the old columns in a later migration once the backfill is verified —
don't do it in one destructive step.
