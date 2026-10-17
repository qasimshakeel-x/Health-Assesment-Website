"""Prepare app-aligned real datasets for `ml/train.py`.

Why this file exists
--------------------
ML_TRAINING.md trains one config-driven pipeline (ml/train.py) on real CSVs. The app's
inference engines build a FIXED feature vector per disease (`disease_risk._build_vector`,
`phase2_risk._build_vector`, `depression.predict_depression`). Ground Rule 6/8 require:

  * only features a user can enter (profile + screening answers),
  * training columns == inference columns (BUG-5),
  * no label-from-feature leakage (ML_TRAINING.md §5).

So this script renames/derives each raw real dataset into `ml/data/real/<disease>.csv`
with EXACTLY the app's feature names + a `target` column, applying the §5 label-from-feature
exclusions. Raw downloads live in `ml/data/real/raw/`; sources are listed in
`ml/data/README.md`.

Run:  python ml/data/prepare_real.py
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

RAW = os.path.join("ml", "data", "real", "raw")
OUT = os.path.join("ml", "data", "real")

# Tractability cap for the big NHANES tables. The spec pipeline is heavy (per disease:
# 5-fold CV AUC + a calibrated 5-fold cross_val_predict + calibration + SHAP ≈ 36 pipeline
# fits of RF(300)+XGB(300)); measured on this 4-vCPU machine that is ~50 s/fit → ~25 min for
# a 6-9 k-row NHANES table, i.e. ~2 h for the five of them. A seeded, target-stratified
# subsample keeps the positive rate and is ample for the 7-14 app features. Documented in
# ml/data/README.md as a limitation.
NHANES_MAX_ROWS = 3000
NHANES_DISEASES = {"diabetes", "hypertension", "obesity", "anemia", "metabolic_syndrome"}

# App inference feature order (must match ml/models/disease_risk.py, phase2_risk.py)
F = {
    "diabetes": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking", "alcohol",
                 "family_diabetes", "family_heart", "family_hypertension", "family_cancer",
                 "freq_urination", "excess_thirst", "weight_loss"],
    "heart": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking", "alcohol",
              "family_diabetes", "family_heart", "family_hypertension", "family_cancer",
              "chest_pain", "short_breath", "palpitations"],
    "hypertension": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking", "alcohol",
                     "family_diabetes", "family_heart", "family_hypertension", "family_cancer",
                     "headaches", "dizziness", "blurred_vision"],
    "obesity": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking", "alcohol",
                "family_diabetes", "family_heart", "family_hypertension", "family_cancer",
                "sugary_diet", "freq_hunger", "hard_lose_weight"],
    "stroke": ["age", "gender", "bmi", "sleep_hours", "exercise_level", "smoking", "alcohol",
               "family_diabetes", "family_heart", "family_hypertension", "family_cancer",
               "bp_systolic", "bp_diastolic", "tia_symptoms", "speech_difficulty",
               "irregular_heartbeat"],
    "ckd": ["age", "bp_systolic", "diabetes_flag", "hypertension_flag", "ankle_swelling",
            "urination_changes", "ckd_fatigue"],
    "liver": ["age", "gender", "bmi", "alcohol", "jaundice", "abdominal_pain", "liver_fatigue"],
    "thyroid": ["age", "gender", "bmi", "fatigue", "weight_change", "temperature_issues",
                "hair_skin"],
    "pcos": ["age", "bmi", "irregular_periods", "weight_gain", "excess_hair", "acne"],
    "anemia": ["gender", "age", "diet_quality", "frequent_fatigue", "pale_cold",
               "lightheadedness", "brittle_nails"],
    "colorectal": ["age", "family_cancer", "diet_quality", "exercise_level", "smoking", "alcohol",
                   "blood_in_stool", "bowel_change", "colorectal_weight_loss"],
    "lung_cancer": ["smoking", "passive_smoke", "age", "family_cancer", "persistent_cough",
                    "coughing_blood", "breath_shortness"],
    "sleep_apnea": ["age", "gender", "bmi", "snoring", "wake_tired", "witnessed_apnea",
                    "daytime_sleepy"],
    "metabolic_syndrome": ["age", "gender", "waist_circumference", "bp_systolic", "bp_diastolic",
                           "diet_quality", "exercise_level", "doctor_high_bp", "doctor_high_sugar",
                           "frequent_thirst_urination"],
    "sleep_apnea_kaggle": ["age", "gender", "bmi", "snoring", "wake_tired", "witnessed_apnea",
                           "daytime_sleepy"],
    "gad7": [f"gad{i}" for i in range(1, 8)],
    "depression": [f"phq{i}" for i in range(1, 10)],
}

REPORT = []


def _xpt(name):
    return pd.read_sas(os.path.join(RAW, name), format="xport")


def _raw_csv(name, **kw):
    return pd.read_csv(os.path.join(RAW, name), **kw)


def _blank(rows, feats, target):
    """Skeleton with app columns + target, all features NaN except given."""
    df = pd.DataFrame(index=range(rows), columns=feats, dtype=float)
    df["target"] = pd.Series([np.nan] * rows, dtype=float)
    return df


def _yn(s):
    """'yes'/'no'/'y'/'n'/1/2 (NHANES 1=Yes,2=No) -> 1/0."""
    def one(v):
        if pd.isna(v):
            return np.nan
        v = str(v).strip().lower()
        if v in ("yes", "y", "true", "1", "1.0"):
            return 1.0
        if v in ("no", "n", "false", "0", "0.0", "2", "2.0"):
            return 0.0
        return np.nan
    return s.map(one)


def _cap_stratified(df, target="target"):
    """Seeded, target-stratified subsample down to NHANES_MAX_ROWS (see the note above)."""
    if len(df) <= NHANES_MAX_ROWS:
        return df
    frac = NHANES_MAX_ROWS / len(df)
    parts = [g.sample(n=max(2, int(round(frac * len(g)))), random_state=42)
             for _, g in df.groupby(target)]
    return pd.concat(parts).sample(frac=1.0, random_state=42)


def _write(name, df, note):
    feats = F[name]
    data = {}
    for c in feats:
        data[c] = (pd.to_numeric(df[c], errors="coerce") if c in df.columns
                   else pd.Series(np.nan, index=df.index))
    out = pd.DataFrame(data)
    out["target"] = (pd.to_numeric(df["target"], errors="coerce") if "target" in df.columns
                     else np.nan)
    out = out[out["target"].notna()].copy()
    if name in NHANES_DISEASES:
        out = _cap_stratified(out)
    # NOTE: no row de-duplication here — NHANES repeated (coarse) feature combos are
    # legitimate distinct subjects and dropping them would gut the dataset (ML_TRAINING §5
    # duplicate check is about identical SOURCE records, done per-source below).
    before = len(out)
    path = os.path.join(OUT, f"{name}.csv")
    out["target"] = out["target"].astype(int)
    out.to_csv(path, index=False)
    REPORT.append({
        "disease": name, "rows": len(out), "dropped_dup": before - len(out),
        "pos_rate": round(float(out["target"].mean()), 4) if len(out) else None,
        "note": note,
    })
    print(f"[prepared] {name:14s} rows={len(out):5d} pos={out['target'].mean():.3f} "
          f"dropped_dup={before - len(out)}  {note}")


# ─────────────────────────────────────────────────────────────── NHANES helpers
def _nhanes_merge(frames):
    df = None
    for f in frames:
        df = f if df is None else df.merge(f, on="SEQN", how="outer")
    return df


def _nhanes_base():
    """Demographics + BMI + smoking + alcohol + physical activity (app base features)."""
    demo = _xpt("DEMO_J.xpt")[["SEQN", "RIAGENDR", "RIDAGEYR", "INDFMPIR"]].rename(
        columns={"RIAGENDR": "gender", "RIDAGEYR": "age", "INDFMPIR": "income_ratio"})
    demo["gender"] = demo["gender"].map({1: 1, 2: 0})          # app: 1=Male, 0=Female
    bmx = _xpt("BMX_J.xpt")[["SEQN", "BMXBMI"]].rename(columns={"BMXBMI": "bmi"})
    # smoking: SMQ020 ever smoked 100 cigarettes (1=yes,2=no)
    smq = _xpt("SMQ_J.xpt")[["SEQN", "SMQ020"]].rename(columns={"SMQ020": "smoking"})
    smq["smoking"] = smq["smoking"].map({1: 1.0, 2: 0.0})
    # alcohol: ALQ111 ever had a drink of any kind of alcohol (1=yes,2=no)
    alq = _xpt("ALQ_J.xpt")
    alq_col = "ALQ111" if "ALQ111" in alq.columns else alq.columns[1]
    alq = alq[["SEQN", alq_col]].rename(columns={alq_col: "alcohol"})
    alq["alcohol"] = alq["alcohol"].map({1: 1.0, 2: 0.0})
    # physical activity: PAQ (PAD615 vigorous min/week, PAD630 moderate) -> 0/1/2 level
    paq = _xpt("PAQ_J.xpt")
    cols = [c for c in ("PAD615", "PAD630", "PAQ620", "PAQ665") if c in paq.columns]
    paq = paq[["SEQN"] + cols].copy()
    active_min = pd.Series(0.0, index=paq.index)
    for c in ("PAD615", "PAD630"):
        if c in paq.columns:
            active_min = active_min.add(paq[c].fillna(0), fill_value=0)
    paq["exercise_level"] = pd.cut(active_min, [-1, 0, 150, 10 ** 9], labels=[0, 1, 2]).astype(float)
    paq = paq[["SEQN", "exercise_level"]]
    # sleep hours: SLD012/SLD013 are the derived weekday/weekend HOURS. (SLQ300/SLQ310 are
    # reported bed/wake TIMES like b'23:00' — not hours, and to_numeric() would blank them.)
    slq = _xpt("SLQ_J.xpt")
    hours = None
    for c in ("SLD012", "SLD013"):
        if c in slq.columns:
            v = pd.to_numeric(slq[c], errors="coerce")
            hours = v if hours is None else hours.fillna(v)
    slq = slq[["SEQN"]].assign(sleep_hours=hours)
    slq.loc[(slq["sleep_hours"] > 20) | (slq["sleep_hours"] < 1), "sleep_hours"] = np.nan
    return _nhanes_merge([demo, bmx, smq, alq, paq, slq])


def prepare_nhanes_diabetes():
    base = _nhanes_base()
    diq = _xpt("DIQ_J.xpt")[["SEQN", "DIQ010", "DIQ170"]].rename(columns={"DIQ170": "family_diabetes"})
    # label: DIQ010 doctor told you have diabetes (1 yes, 2 no, 3 borderline -> drop)
    diq["target"] = diq["DIQ010"].map({1: 1.0, 2: 0.0})
    diq["family_diabetes"] = diq["family_diabetes"].map({1: 1.0, 2: 0.0})
    df = base.merge(diq[["SEQN", "family_diabetes", "target"]], on="SEQN", how="left")
    # BP for other diseases is separate; diabetes app vector has no BP column
    _write("diabetes", df, "NHANES 2017-2018 J: label DIQ010; fam history DIQ170; "
                           "symptoms not collected in NHANES (NaN)")


def prepare_nhanes_hypertension():
    base = _nhanes_base()
    bpx = _xpt("BPX_J.xpt")
    sys_mean = bpx[["BPXSY1", "BPXSY2", "BPXSY3", "BPXSY4"]].mean(axis=1)
    dia_mean = bpx[["BPXDI1", "BPXDI2", "BPXDI3", "BPXDI4"]].mean(axis=1)
    bpx = bpx[["SEQN"]].copy()
    bpx["target"] = ((sys_mean >= 130) | (dia_mean >= 80)).astype(float)
    bpx.loc[sys_mean.isna() | dia_mean.isna(), "target"] = np.nan
    # §5 label-from-feature trap: BP defines the label -> BP excluded from features
    df = base.merge(bpx, on="SEQN", how="left")
    _write("hypertension", df, "NHANES J measured BP (mean SBP>=130 or DBP>=80); "
                               "BP excluded from features per §5")


def prepare_nhanes_obesity():
    base = _nhanes_base()
    base["target"] = (base["bmi"] >= 30).astype(float)
    base.loc[base["bmi"].isna(), "target"] = np.nan
    # §5 trap: BMI defines the label -> BMI excluded from features
    base["bmi"] = np.nan
    _write("obesity", base, "NHANES J measured BMI>=30; BMI excluded from features per §5")


def prepare_nhanes_anemia():
    base = _nhanes_base()
    cbc = _xpt("CBC_J.xpt")[["SEQN", "LBXHGB"]]
    df = base.merge(cbc, on="SEQN", how="left")
    hgb = df["LBXHGB"]
    # WHO anemia thresholds: <13.0 male, <12.0 female
    thr = np.where(df["gender"] == 1, 13.0, 12.0)
    df["target"] = (hgb < thr).astype(float)
    df.loc[hgb.isna(), "target"] = np.nan
    # §5 trap: label derived from hemoglobin -> HGB not a feature (app has no lab input anyway)
    _write("anemia", df, "NHANES J hemoglobin < WHO threshold (13.0 M / 12.0 F); "
                         "no lab features used (app-aligned)")


def prepare_nhanes_sleep_apnea():
    """Sleep apnoea symptoms (SLQ) -> app STOP-BANG-style columns."""
    base = _nhanes_base()
    slq = _xpt("SLQ_J.xpt")
    keep = [c for c in ("SLQ010", "SLQ040", "SLQ050", "SLQ060", "SLQ120") if c in slq.columns]
    slq = slq[["SEQN"] + keep].copy()
    # SLQ010 ever told doctor you have sleep disorder; SLQ040 snore 3+ nights/wk;
    # SLQ050 told doctor about snoring; SLQ060 ever told you stopped breathing (apnea);
    # SLQ120 felt overly sleepy during day 5+ times/month
    df = base.merge(slq, on="SEQN", how="left")
    if "SLQ060" in df.columns:
        df["target"] = df["SLQ060"].map({1: 1.0, 2: 0.0})
    else:
        df["target"] = np.nan
    df["snoring"] = df["SLQ040"].map({1: 1.0, 2: 0.0}) if "SLQ040" in df.columns else np.nan
    df["daytime_sleepy"] = df["SLQ120"].map({1: 1.0, 2: 0.0}) if "SLQ120" in df.columns else np.nan
    _write("sleep_apnea", df, "NHANES J SLQ060 (told stopped breathing) label; "
                              "derived from NHANES (no sleep-lab study)")


def prepare_metabolic_syndrome():
    """IDF metabolic-syndrome label (>=3 of 5 factors) from NHANES J clinical measurements.

    NOTE: the label is a clinical composite of the same inputs (waist/BP/glucose) — the app's
    metabolic_syndrome screener is a rule over those inputs by design (ML_TRAINING §5 trap is
    documented here; flags are recorded by ml/train.py).
    """
    base = _nhanes_base()
    bmx = _xpt("BMX_J.xpt")[["SEQN", "BMXWAIST"]].rename(columns={"BMXWAIST": "waist_circumference"})
    bpx = _xpt("BPX_J.xpt")
    bpx = bpx[["SEQN"]].assign(
        bp_systolic=bpx[["BPXSY1", "BPXSY2", "BPXSY3", "BPXSY4"]].mean(axis=1),
        bp_diastolic=bpx[["BPXDI1", "BPXDI2", "BPXDI3", "BPXDI4"]].mean(axis=1))
    bio = _xpt("BIOPRO_J.xpt")[["SEQN", "LBXSGL"]].rename(columns={"LBXSGL": "glucose"})
    trg = _xpt("TRIGLY_J.xpt")[["SEQN", "LBXTR"]].rename(columns={"LBXTR": "trig"})
    hdl = _xpt("HDL_J.xpt")[["SEQN", "LBDHDD"]].rename(columns={"LBDHDD": "hdl"})
    bpq = _xpt("BPQ_J.xpt")[["SEQN", "BPQ050A", "BPQ020"]].rename(
        columns={"BPQ050A": "bp_med", "BPQ020": "doctor_high_bp"})
    diq = _xpt("DIQ_J.xpt")[["SEQN", "DIQ010"]].rename(columns={"DIQ010": "doctor_high_sugar"})
    df = _nhanes_merge([base, bmx, bpx, bio, trg, hdl, bpq, diq])

    df["doctor_high_bp"] = df["doctor_high_bp"].map({1: 1.0, 2: 0.0})
    df["doctor_high_sugar"] = df["doctor_high_sugar"].map({1: 1.0, 2: 0.0})  # 3=borderline→NaN
    df["diet_quality"] = np.nan                 # NHANES has no simple 3-level diet answer
    df["frequent_thirst_urination"] = np.nan    # not collected in NHANES

    male = df["gender"] == 1
    raw_waist, raw_trig, raw_hdl = df["waist_circumference"], df["trig"], df["hdl"]

    def _factor(ok, cond):
        """Factor value 1/0, or NaN when the underlying measurement is missing."""
        out = pd.Series(np.nan, index=df.index, dtype=float)
        out[ok] = cond[ok].astype(float)
        return out

    comps = pd.DataFrame({
        "waist": _factor(raw_waist.notna(), raw_waist >= np.where(male, 90.0, 80.0)),
        "trig": _factor(raw_trig.notna(), raw_trig >= 150),
        "hdl": _factor(raw_hdl.notna(), raw_hdl < np.where(male, 40.0, 50.0)),
        "bp": _factor(df["bp_systolic"].notna() | df["bp_diastolic"].notna() | df["bp_med"].notna(),
                      (df["bp_systolic"] >= 130) | (df["bp_diastolic"] >= 85) | (df["bp_med"] == 1)),
        "glucose": _factor(df["glucose"].notna() | df["doctor_high_sugar"].notna(),
                           (df["glucose"] >= 100) | (df["doctor_high_sugar"] == 1)),
    })
    assessable = comps.notna().sum(axis=1)
    count = comps.sum(axis=1)
    df["target"] = np.where(assessable >= 4, (count >= 3).astype(float), np.nan)
    _write("metabolic_syndrome", df, "NHANES J IDF metabolic syndrome (>=3 of 5: waist/BP/"
                                     "TG/HDL/glucose); label uses the same inputs as features "
                                     "(documented §5 overlap); thirst not in NHANES")


# ─────────────────────────────────────────────────────────────── non-NHANES
def prepare_ckd():
    df = _raw_csv("ckd.csv")
    df.columns = [c.strip() for c in df.columns]
    out = pd.DataFrame({
        "age": pd.to_numeric(df["age"], errors="coerce"),
        "bp_systolic": pd.to_numeric(df["bp"], errors="coerce"),
        "diabetes_flag": _yn(df["dm"]),
        "hypertension_flag": _yn(df["htn"]),
    })
    out["target"] = df["classification"].astype(str).str.strip().str.lower().map(
        {"ckd": 1.0, "notckd": 0.0})
    # symptoms (ankle_swelling/urination/ckd_fatigue) are not in UCI CKD -> NaN
    _write("ckd", out, "UCI CKD (400 rows) mapped to app vector: age, bp->bp_systolic, "
                       "dm/htn->flags; symptoms NaN (not in dataset)")


def prepare_liver():
    # ILPD CSV from UCI has NO header row
    cols = ["Age", "Gender", "Total_Bilirubin", "Direct_Bilirubin", "Alkaline_Phosphotase",
            "Alamine_Aminotransferase", "Aspartate_Aminotransferase", "Total_Protiens",
            "Albumin", "Albumin_and_Globulin_Ratio", "Dataset"]
    df = pd.read_csv(os.path.join(RAW, "ilpd.csv"), names=cols)
    out = pd.DataFrame({
        "age": pd.to_numeric(df["Age"], errors="coerce"),
        "gender": df["Gender"].astype(str).str.strip().str.lower().map({"male": 1.0, "female": 0.0}),
        "alcohol": np.nan,
    })
    out["target"] = pd.to_numeric(df["Dataset"], errors="coerce").map({1: 1.0, 2: 0.0})
    _write("liver", out, "ILPD (UCI, 583 rows): only age/gender are app-available; "
                         "ILPD has no alcohol column and no symptoms -> NaN")


def prepare_thyroid():
    # hypothyroid.data (UCI) has NO header row and 26 fields (more than the 24 documented
    # names), so read the three fields we need POSITIONALLY: class, age, sex.
    df = pd.read_csv(os.path.join(RAW, "hypothyroid.data"), header=None, usecols=[0, 1, 2],
                     names=["class", "age", "sex"], na_values=["?"], skipinitialspace=True)
    for c in ("class", "sex"):
        df[c] = df[c].astype(str).str.strip()
    out = pd.DataFrame({
        "age": pd.to_numeric(df["age"], errors="coerce"),
        "gender": df["sex"].map({"M": 1.0, "F": 0.0}),
        # app symptoms: fatigue / weight_change / temperature_issues / hair_skin
        "fatigue": np.nan, "weight_change": np.nan,
        "temperature_issues": np.nan, "hair_skin": np.nan,
    })
    out["target"] = df["class"].map(lambda v: 0.0 if str(v).startswith("negative") else 1.0)
    _write("thyroid", out, "UCI hypothyroid (3162 rows): only age/gender app-available; "
                           "TSH/T3/TT4 are labs the app does not collect -> excluded, symptoms NaN")


def prepare_heart():
    cols = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang",
            "oldpeak", "slope", "ca", "thal", "num"]
    df = pd.read_csv(os.path.join(RAW, "processed.cleveland.data"), names=cols, na_values="?")
    out = pd.DataFrame({
        "age": pd.to_numeric(df["age"], errors="coerce"),
        "gender": pd.to_numeric(df["sex"], errors="coerce"),
        "bp_systolic": pd.to_numeric(df["trestbps"], errors="coerce"),   # resting BP is app-available
        "smoking": np.nan,          # Cleveland has no smoking column
        # Cleveland cp: 1 typical angina, 2 atypical angina, 3 non-anginal pain, 4 asymptomatic
        "chest_pain": df["cp"].map({1: 1.0, 2: 1.0, 3: np.nan, 4: 0.0}),
    })
    out["target"] = (pd.to_numeric(df["num"], errors="coerce") > 0).astype(float)
    out.loc[df["num"].isna(), "target"] = np.nan
    # heart app vector has no bp columns -> keep only app columns in _write
    out["bp_systolic"] = np.nan
    _write("heart", out, "UCI Cleveland (303 rows): age/gender/chest-pain only; "
                         "smoking & BP not in app heart vector (kept NaN)")


def prepare_stroke():
    df = _raw_csv("stroke.csv")
    out = pd.DataFrame({
        "age": pd.to_numeric(df["age"], errors="coerce"),
        "gender": df["gender"].astype(str).str.strip().str.lower().map({"male": 1.0, "female": 0.0}),
        "bmi": pd.to_numeric(df["bmi"], errors="coerce"),
        "smoking": df["smoking_status"].astype(str).str.strip().str.lower().map(
            {"smokes": 1.0, "formerly smoked": 1.0, "never smoked": 0.0, "unknown": np.nan}),
        # hypertension/heart_disease are dataset-derived labels; use as history flags only
        "family_hypertension": pd.to_numeric(df["hypertension"], errors="coerce"),
        "family_heart": pd.to_numeric(df["heart_disease"], errors="coerce"),
    })
    out["target"] = pd.to_numeric(df["stroke"], errors="coerce")
    _write("stroke", out, "Kaggle stroke (5110 rows): age/gender/bmi/smoking; "
                          "hypertension & heart_disease used as history flags (not leakage of stroke)")


def prepare_pcos():
    df = _raw_csv("pcos.csv")
    df.columns = [str(c).strip() for c in df.columns]
    out = pd.DataFrame({
        "age": pd.to_numeric(df["Age (yrs)"], errors="coerce"),
        "bmi": pd.to_numeric(df["BMI"], errors="coerce"),
        "irregular_periods": (pd.to_numeric(df["Cycle(R/I)"], errors="coerce") == 4).astype(float),
        "weight_gain": _yn(df["Weight gain(Y/N)"]),
        "excess_hair": _yn(df["hair growth(Y/N)"]),
        "acne": _yn(df["Pimples(Y/N)"]),
    })
    out.loc[df["Cycle(R/I)"].isna() | (pd.to_numeric(df["Cycle(R/I)"], errors="coerce") == 0),
            "irregular_periods"] = np.nan
    out["target"] = _yn(df["PCOS (Y/N)"])
    _write("pcos", out, "Kaggle PCOS (541 rows): Age/BMI/Cycle/weight-gain/hair/acne")


def prepare_lung_cancer():
    df = _raw_csv("lung_cancer.csv")
    df.columns = [str(c).strip() for c in df.columns]
    out = pd.DataFrame({
        "smoking": df["SMOKING"].map({1: 0.0, 2: 1.0}),          # 1=NO, 2=YES in this survey
        "age": pd.to_numeric(df["AGE"], errors="coerce"),
        "persistent_cough": df["COUGHING"].map({1: 0.0, 2: 1.0}),
        "breath_shortness": df["SHORTNESS OF BREATH"].map({1: 0.0, 2: 1.0}),
    })
    out["target"] = _yn(df["LUNG_CANCER"])
    _write("lung_cancer", out, "Kaggle lung-cancer survey (309 rows) -> SMALL_DATASET; "
                               "smoking/cough/shortness-of-breath app-aligned")


def prepare_sleep_apnea_kaggle():
    """Sleep Health & Lifestyle survey (real, 374 rows, CC0) — NHANES J cycle has no
    'stopped breathing' item, so this is the app-aligned real source for sleep apnoea."""
    df = _raw_csv("sleep.csv")
    bmi_map = {"normal weight": 23.0, "normal": 23.0, "overweight": 27.5, "obese": 34.0}
    quality = pd.to_numeric(df["Quality of Sleep"], errors="coerce")
    stress = pd.to_numeric(df["Stress Level"], errors="coerce")
    out = pd.DataFrame({
        "age": pd.to_numeric(df["Age"], errors="coerce"),
        "gender": df["Gender"].astype(str).str.strip().str.lower().map({"male": 1.0, "female": 0.0}),
        "bmi": df["BMI Category"].astype(str).str.strip().str.lower().map(bmi_map),
        "wake_tired": (quality <= 5).astype(float),          # poor sleep quality -> wakes tired
        "daytime_sleepy": (stress >= 7).astype(float),       # high stress -> daytime sleepiness
        "snoring": np.nan, "witnessed_apnea": np.nan,
    })
    out.loc[quality.isna(), "wake_tired"] = np.nan
    out.loc[stress.isna(), "daytime_sleepy"] = np.nan
    out["target"] = (df["Sleep Disorder"].astype(str).str.strip().str.lower()
                     == "sleep apnea").astype(float)
    _write("sleep_apnea", out, "Kaggle Sleep-Health survey (374 rows): BMI category mapped to "
                               "BMI (derived), wake_tired<-sleep quality, daytime_sleepy<-stress; "
                               "SMALL_DATASET")


def prepare_gad7():
    p = os.path.join(RAW, "gad7_raw")
    if not os.path.exists(p):
        print("[skip] gad7 raw missing")
        return
    df = None
    for reader, name in ((lambda: pd.read_csv(p), "csv"),):
        try:
            df = reader()
            break
        except Exception as e:
            print("gad7 csv read failed:", e)
    if df is None:
        try:
            df = pd.read_excel(p)
        except Exception:
            df = pd.read_spss(p)
    df.columns = [str(c).strip().lower() for c in df.columns]
    gag = [c for c in df.columns if c.startswith("gad") and c[3:].isdigit()]
    gag = sorted(gag, key=lambda c: int(c[3:]))[:7]
    if len(gag) < 7:
        print("[skip] gad7: could not find 7 gad item columns; columns =", list(df.columns)[:20])
        return
    out = df[gag].apply(pd.to_numeric, errors="coerce")
    out.columns = [f"gad{i}" for i in range(1, 8)]
    total = out.sum(axis=1)
    out["target"] = (total >= 10).astype(float)     # GAD-7 moderate+ (>=10)
    out.loc[total.isna(), "target"] = np.nan
    _write("gad7", out, "GAD-7 items -> label total>=10 (label derived from items by design; "
                        "same as the clinical rule the app already uses)")


def prepare_depression():
    p = os.path.join(RAW, "gad7_raw")
    if not os.path.exists(p):
        print("[skip] depression raw missing")
        return
    try:
        df = pd.read_csv(p)
    except Exception:
        try:
            df = pd.read_excel(p)
        except Exception:
            df = pd.read_spss(p)
    df.columns = [str(c).strip().lower() for c in df.columns]
    phq = [c for c in df.columns if c.startswith("phq") and c[3:].isdigit()]
    phq = sorted(phq, key=lambda c: int(c[3:]))[:9]
    if len(phq) < 9:
        print("[skip] depression: could not find 9 phq item columns; columns =", list(df.columns)[:20])
        return
    out = df[phq].apply(pd.to_numeric, errors="coerce")
    out.columns = [f"phq{i}" for i in range(1, 10)]
    total = out.sum(axis=1)
    out["target"] = (total >= 10).astype(float)      # PHQ-9 moderate+ (>=10)
    out.loc[total.isna(), "target"] = np.nan
    _write("depression", out, "PHQ-9 items -> label total>=10 (label derived from items by design; "
                              "mirrors the app's PHQ-9 severity rule)")


def prepare_nhanes_colorectal():
    """NHANES 2017-2018 MCQ_J — ever told you had colon/rectum cancer.

    Real, but tiny (55 cases) and only 4 of the app's 9 columns exist in NHANES, so the honest
    outcome is a weak model (ML_TRAINING §6: "tiny Kaggle-scale datasets -> do not trust high
    scores"). Deliberately NOT in NHANES_DISEASES: capping to 3 000 rows would throw away ~13 of
    the 55 positives.
    """
    base = _nhanes_base()
    mcq = _xpt("MCQ_J.xpt")
    cols = [c for c in mcq.columns if str(c).upper().startswith("MCQ230")]
    if not cols:
        print("[skip] colorectal: no MCQ230* columns in MCQ_J.xpt")
        return
    ever = mcq[cols].isin([16.0, 31.0]).any(axis=1).astype(float)   # 16=Colon, 31=Rectum
    df = base.merge(mcq[["SEQN"]].assign(target=ever), on="SEQN", how="inner")
    df = df[df["age"] >= 40]                    # app gate: the colorectal module is 40+
    _write("colorectal", df, "NHANES 2017-2018 J MCQ_J MCQ230A-D code 16 (colon) / 31 (rectum), "
                             "age>=40 (app gate). Family history / symptoms / diet are not "
                             "collected in NHANES -> LOW_FEATURE_MODEL; only 55 cases -> "
                             "HEAVY_IMBALANCE and a weak AUC, as ML_TRAINING §6 predicts")


def main():
    os.makedirs(OUT, exist_ok=True)
    for fn in [prepare_nhanes_diabetes, prepare_nhanes_hypertension, prepare_nhanes_obesity,
               prepare_nhanes_anemia, prepare_metabolic_syndrome, prepare_nhanes_colorectal,
               prepare_ckd, prepare_liver,
               prepare_thyroid, prepare_heart, prepare_stroke, prepare_pcos,
               prepare_lung_cancer, prepare_sleep_apnea_kaggle, prepare_gad7, prepare_depression]:
        try:
            fn()
        except Exception as e:
            print(f"[ERROR] {fn.__name__}: {type(e).__name__}: {e}")
    print("\n=== summary ===")
    for r in REPORT:
        print(r)


if __name__ == "__main__":
    main()
