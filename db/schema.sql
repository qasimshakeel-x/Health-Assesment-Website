-- AI Longevity Intelligence Platform — PostgreSQL Schema
-- Database: PostgreSQL 16

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- USER PROFILES (health intake)
-- ============================================================
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    age INTEGER NOT NULL CHECK (age BETWEEN 18 AND 120),
    gender INTEGER NOT NULL CHECK (gender IN (0, 1)),
    height FLOAT NOT NULL,
    weight FLOAT NOT NULL,
    bmi FLOAT GENERATED ALWAYS AS (weight / POWER(height / 100.0, 2)) STORED,
    sleep_hours FLOAT NOT NULL CHECK (sleep_hours BETWEEN 3.0 AND 12.0),
    exercise_level INTEGER NOT NULL CHECK (exercise_level BETWEEN 0 AND 4),
    smoking BOOLEAN DEFAULT FALSE,
    alcohol INTEGER DEFAULT 0 CHECK (alcohol BETWEEN 0 AND 7),
    family_history INTEGER[] NOT NULL DEFAULT '{0,0,0,0}',
    phq9 INTEGER[] NOT NULL,
    -- Phase 2+ inputs (06-DISEASE-MODULES: BP stroke/metabolic, waist metabolic, diet colorectal/anemia/liver)
    bp_systolic FLOAT,
    bp_diastolic FLOAT,
    waist_circumference FLOAT,
    diet_quality VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);

-- ============================================================
-- SCREENING RESPONSES (extra Phase 2-5 questions — 04-DATA-MODEL §2)
-- ============================================================
CREATE TABLE screening_responses (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    screening_key VARCHAR(50) NOT NULL,
    responses JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_screening_responses_user_profile_id ON screening_responses(user_profile_id);
CREATE INDEX idx_screening_responses_key ON screening_responses(screening_key);

-- ============================================================
-- PREDICTION RESULTS
-- ============================================================
CREATE TABLE prediction_results (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    diabetes_risk FLOAT,
    heart_risk FLOAT,
    hypertension_risk FLOAT,
    obesity_risk FLOAT,
    biological_age FLOAT,
    longevity_score FLOAT,
    depression_level VARCHAR(20),
    depression_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_prediction_results_user_profile_id ON prediction_results(user_profile_id);

-- ============================================================
-- DISEASE RISK RESULTS (normalized per-disease scores — 04-DATA-MODEL §2)
-- prediction_results ke flat columns purane hain (back-compat); naye 16 diseases idhar jate hain
-- ============================================================
CREATE TABLE disease_risk_results (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER NOT NULL REFERENCES prediction_results(id) ON DELETE CASCADE,
    disease_key VARCHAR(50) NOT NULL,
    category VARCHAR(30) NOT NULL,
    risk_percent FLOAT NOT NULL CHECK (risk_percent BETWEEN 0.0 AND 100.0),
    risk_label VARCHAR(20) NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_disease_risk_results_prediction_id ON disease_risk_results(prediction_id);
CREATE INDEX idx_disease_risk_results_disease_key ON disease_risk_results(disease_key);

-- ============================================================
-- SHAP EXPLANATIONS
-- ============================================================
CREATE TABLE shap_explanations (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER NOT NULL REFERENCES prediction_results(id) ON DELETE CASCADE,
    disease VARCHAR(50) NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    shap_value FLOAT NOT NULL CHECK (shap_value BETWEEN -1.0 AND 1.0),
    rank INTEGER NOT NULL
);

CREATE INDEX idx_shap_explanations_prediction_id ON shap_explanations(prediction_id);

-- ============================================================
-- CHAT SESSIONS
-- ============================================================
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER NOT NULL REFERENCES prediction_results(id) ON DELETE CASCADE,
    messages JSONB DEFAULT '[]',
    system_prompt TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_prediction_id ON chat_sessions USING HASH(prediction_id);

-- ============================================================
-- REPORT LOG
-- ============================================================
CREATE TABLE report_log (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    pdf_path VARCHAR(512),
    generated_at TIMESTAMP DEFAULT NOW(),
    file_size_kb FLOAT,
    status VARCHAR(20) DEFAULT 'pending'
);
