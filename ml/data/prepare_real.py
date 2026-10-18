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

import glob
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

# BRFSS (CDC "Behavioral Risk Factor Surveillance System") is the free, credential-free item on
# the dataset-accuracy TODO: ~400 k US adults x 500+ columns, one zip of 60-90 MB from
# https://www.cdc.gov/brfss/annual_data/<year>/files/LLCP<year>XPT.zip (see ml/data/README.md).
# Capped like NHANES so the 36-fits-per-disease spec pipeline stays tractable on this 4 GB box.
BRFSS_YEAR = "2025"
BRFSS_MAX_ROWS = 6000
BRFSS_DISEASES = {"heart", "stroke"}

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


def _cap_stratified(df, target="target", max_rows=None):
    """Seeded, target-stratified subsample down to `max_rows` (default NHANES_MAX_ROWS).

    Shared by the NHANES and the BRFSS sources (see the note above).
    """
    max_rows = NHANES_MAX_ROWS if max_rows is None else max_rows
    if len(df) <= max_rows:
        return df
    frac = max_rows / len(df)
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
    if not len(out):
        # Safety net: a renamed/missing source label would otherwise truncate this dataset to a
        # header-only CSV and only fail much later, away from the cause. Keep the old good file.
        REPORT.append({"disease": name, "rows": 0, "dropped_dup": 0, "pos_rate": None,
                       "note": "EMPTY - no usable label in source; existing CSV kept"})
        print(f"[EMPTY]  {name:14s} 0 rows -> kept any existing {name}.csv (check source cols)")
        return
    if name in BRFSS_DISEASES:
        out = _cap_stratified(out, max_rows=BRFSS_MAX_ROWS)
    elif name in NHANES_DISEASES:
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


def _bpx_means(bpx):
    """Mean systolic / diastolic BP over whichever BPXSY1-4 / BPXDI1-4 readings exist."""
    sys_cols = [c for c in bpx.columns if c.startswith("BPXSY")]
    dia_cols = [c for c in bpx.columns if c.startswith("BPXDI")]
    return bpx[sys_cols].mean(axis=1), bpx[dia_cols].mean(axis=1)


def _nhanes_base(suffix="J"):
    """Demographics + BMI + smoking + alcohol + physical activity (app base features).

    `suffix` = NHANES cycle letter: `J` 2017-18 (default, all single-cycle app datasets),
    `I` 2015-16, `H` 2013-14, `G` 2011-12, `F` 2009-10 (multi-cycle pooled diseases — see
    `prepare_nhanes_colorectal` / `prepare_nhanes_ckd` / `prepare_nhanes_liver`). SEQN is
    unique across cycles, so the per-cycle frames can be concatenated without collisions.

    Variable availability differs slightly between cycles: the "ever had a drink" question is
    ALQ111 in 2015-18 but ALQ101 (had >=12 drinks in lifetime) in 2009-14; sleep hours are
    SLD012/SLD013 in 2013-18 but SLD010H in 2009-12; PAD615/PAD630 (leisure-activity minutes)
    are guarded with `in columns` checks below. NOTE (coarse, documented): PAD615/PAD630 are
    per-week minutes in 2013-18 but per-DAY minutes in 2009-12, so the 150 cut separates
    active from inactive within each cycle but is not comparable across cycles.
    """
    demo = _xpt(f"DEMO_{suffix}.xpt")[["SEQN", "RIAGENDR", "RIDAGEYR", "INDFMPIR"]].rename(
        columns={"RIAGENDR": "gender", "RIDAGEYR": "age", "INDFMPIR": "income_ratio"})
    demo["gender"] = demo["gender"].map({1: 1, 2: 0})          # app: 1=Male, 0=Female
    bmx = _xpt(f"BMX_{suffix}.xpt")[["SEQN", "BMXBMI"]].rename(columns={"BMXBMI": "bmi"})
    # smoking: SMQ020 ever smoked 100 cigarettes (1=yes,2=no)
    smq = _xpt(f"SMQ_{suffix}.xpt")[["SEQN", "SMQ020"]].rename(columns={"SMQ020": "smoking"})
    smq["smoking"] = smq["smoking"].map({1: 1.0, 2: 0.0})
    # alcohol: ALQ111 (2015-18) / ALQ101 (2013-14) ever had a drink (1=yes,2=no)
    alq = _xpt(f"ALQ_{suffix}.xpt")
    alq_col = next((c for c in ("ALQ111", "ALQ101") if c in alq.columns), alq.columns[1])
    alq = alq[["SEQN", alq_col]].rename(columns={alq_col: "alcohol"})
    alq["alcohol"] = alq["alcohol"].map({1: 1.0, 2: 0.0})
    # physical activity: PAQ (PAD615 vigorous min/week, PAD630 moderate) -> 0/1/2 level
    paq = _xpt(f"PAQ_{suffix}.xpt")
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
    slq = _xpt(f"SLQ_{suffix}.xpt")
    hours = None
    for c in ("SLD012", "SLD013", "SLD010H"):      # SLD010H = 2009-2012 naming
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
    sys_mean, dia_mean = _bpx_means(bpx)
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
    """NHANES hemoglobin (CBC) pooled H+I+J -> Phase-2 `anemia` vector (multi-cycle upgrade).

    The single 2017-18 cycle carried ~8.5 k adults / ~1.3 k cases; pooling three cycles
    triples the diversity behind the seeded 3 000-row cap (NHANES_DISEASES). App symptom
    columns (diet/fatigue/pale/lightheaded/brittle nails) are not collected in NHANES (NaN),
    so this stays LOW_FEATURE_MODEL (age + gender are the only app-usable columns).
    """
    frames = []
    for s in ("H", "I", "J"):
        base = _nhanes_base(s)
        cbc = _xpt(f"CBC_{s}.xpt")[["SEQN", "LBXHGB"]]
        df = base.merge(cbc, on="SEQN", how="inner")
        hgb = df["LBXHGB"]
        # WHO anemia thresholds: <13.0 male, <12.0 female
        thr = np.where(df["gender"] == 1, 13.0, 12.0)
        df["target"] = (hgb < thr).astype(float)
        df.loc[hgb.isna(), "target"] = np.nan
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    _write("anemia", df, "NHANES 2013-2018 (H+I+J) hemoglobin < WHO threshold (13.0 M / 12.0 F); "
                         "multi-cycle pool; no lab features used (app-aligned); app symptoms "
                         "not collected (NaN)")


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
def _nhanes_ckd_cycle(suffix):
    """One NHANES cycle -> CKD label (KIQ022) + the app columns NHANES can supply."""
    base = _nhanes_base(suffix)
    bpx = _xpt(f"BPX_{suffix}.xpt")
    sys_mean, _ = _bpx_means(bpx)
    bpx = bpx[["SEQN"]].assign(bp_systolic=sys_mean)
    diq = _xpt(f"DIQ_{suffix}.xpt")[["SEQN", "DIQ010"]].copy()
    diq["diabetes_flag"] = diq["DIQ010"].map({1: 1.0, 2: 0.0})   # 3 = borderline -> NaN
    diq = diq[["SEQN", "diabetes_flag"]]
    bpq = _xpt(f"BPQ_{suffix}.xpt")[["SEQN", "BPQ020"]].rename(
        columns={"BPQ020": "hypertension_flag"})
    bpq["hypertension_flag"] = bpq["hypertension_flag"].map({1: 1.0, 2: 0.0})
    kiq = _xpt(f"KIQ_U_{suffix}.xpt")[["SEQN", "KIQ022", "KIQ480"]].copy()
    kiq["target"] = kiq["KIQ022"].map({1: 1.0, 2: 0.0})       # 9 = don't know -> NaN
    # KIQ480 = "how many times urinate at night" (1..5+; asked of KIQ005 respondents).
    # Nocturia >= 2/night is the app's "urination changes" yes; refused/DK -> NaN.
    kiq["urination_changes"] = np.nan
    ok = kiq["KIQ480"].between(1, 5)
    kiq.loc[ok, "urination_changes"] = (kiq.loc[ok, "KIQ480"] >= 2).astype(float)
    return _nhanes_merge([base, bpx, diq, bpq, kiq[["SEQN", "target", "urination_changes"]]])


def prepare_nhanes_ckd():
    """NHANES KIQ_U kidney questions pooled H+I+J -> Phase-2 `ckd` vector (dataset-accuracy TODO).

    Replaces the 400-row UCI CKD file, whose AUC 0.955 was inflated: 400 rows, and the dm/htn
    flags double as inputs to the clinical label. Label = KIQ022 "ever told weak/failing
    kidneys" (3.2-4.2% of adults, ~660 cases over 3 cycles). Real app columns: age, measured
    bp_systolic (BPX), diabetes_flag (DIQ010), hypertension_flag (BPQ020), urination_changes
    (KIQ480 nocturia >=2). ankle_swelling / ckd_fatigue are not collected in NHANES (NaN).
    Deliberately NOT in NHANES_DISEASES: capping to 3 000 rows would throw away most positives.
    """
    df = pd.concat([_nhanes_ckd_cycle(s) for s in ("H", "I", "J")], ignore_index=True)
    _write("ckd", df, "NHANES 2013-2018 (H+I+J) pooled: label KIQ022 (ever told weak/failing "
                      "kidneys); age/measured-BP (BPX)/diabetes (DIQ010)/high-BP history "
                      "(BPQ020)/nocturia >=2 (KIQ480) real; ankle-swelling & fatigue not "
                      "collected (NaN); replaces the inflated 400-row UCI set; unweighted")


def prepare_nhanes_liver():
    """NHANES MCQ liver questions pooled H+I+J -> Phase-2 `liver` vector (dataset-accuracy TODO).

    Replaces UCI ILPD (583 rows, age/gender usable). Label = MCQ160L "ever told you had any
    liver condition" (2.4-3.3% of adults, ~480 cases over 3 cycles). Real app columns: age,
    gender, bmi, alcohol (ALQ ever-drink), jaundice (MCQ203); abdominal_pain / liver_fatigue
    are not collected in NHANES (NaN). MCQ203 was new in 2013-14, hence cycles H+I+J (not F/G).
    Deliberately NOT in NHANES_DISEASES: capping would throw away most positives.
    """
    frames = []
    for s in ("H", "I", "J"):
        base = _nhanes_base(s)
        mcq = _xpt(f"MCQ_{s}.xpt")[["SEQN", "MCQ160L", "MCQ203"]].copy()
        mcq["target"] = mcq["MCQ160L"].map({1: 1.0, 2: 0.0})   # 7/9 -> NaN
        mcq["jaundice"] = mcq["MCQ203"].map({1: 1.0, 2: 0.0})
        frames.append(base.merge(mcq[["SEQN", "target", "jaundice"]], on="SEQN", how="inner"))
    df = pd.concat(frames, ignore_index=True)
    _write("liver", df, "NHANES 2013-2018 (H+I+J) pooled: label MCQ160L (ever told any liver "
                        "condition); age/gender/bmi/alcohol (ALQ ever-drink)/jaundice (MCQ203) "
                        "real; abdominal-pain & fatigue not collected (NaN); replaces 583-row "
                        "UCI ILPD; unweighted sample")


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


def _prepare_heart_cleveland():
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


def _prepare_stroke_kaggle():
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


def _colorectal_cycle(suffix):
    """One NHANES cycle → ever-told colon/rectum cancer (MCQ230A-D code 16 / 31), age >= 40.

    Returns None when the cycle's MCQ file has no MCQ230* columns (variable renamed) so a single
    unreadable cycle cannot silently poison the pool with mislabelled rows. The MCQ230 cancer-
    type codes are identical across the 2009-2018 cycles (verified against the F/G codebooks).
    """
    base = _nhanes_base(suffix)
    mcq = _xpt(f"MCQ_{suffix}.xpt")
    cols = [c for c in mcq.columns if str(c).upper().startswith("MCQ230")]
    if not cols:
        print(f"[warn] colorectal {suffix}: no MCQ230* columns -> cycle skipped")
        return None
    ever = mcq[cols].isin([16.0, 31.0]).any(axis=1).astype(float)   # 16=Colon, 31=Rectum
    df = base.merge(mcq[["SEQN"]].assign(target=ever), on="SEQN", how="inner")
    return df[df["age"] >= 40]                  # app gate: the colorectal module is 40+


_CRC_CYCLES = ("F", "G", "H", "I", "J")         # NHANES 2009-10 .. 2017-18


def prepare_nhanes_colorectal():
    """NHANES MCQ230A-D (colon/rectum cancer) pooled over 2009-10 (F) .. 2017-18 (J).

    S18 pooled H+I+J (3 882/55 -> 11 463/120 cases); this pass adds the two earlier cycles
    (F/G, ~7 700 more 40+ adults) for a further positive-count bump. Still LOW_FEATURE_MODEL:
    family history / symptoms / diet are not collected in NHANES.
    Deliberately NOT in NHANES_DISEASES: capping to 3 000 rows would throw away most positives.
    """
    frames = [d for d in (_colorectal_cycle(s) for s in _CRC_CYCLES) if d is not None]
    if not frames:
        print("[skip] colorectal: no usable NHANES cycle (MCQ230* missing)")
        return
    df = pd.concat(frames, ignore_index=True)
    cycles = "+".join(_CRC_CYCLES)
    _write("colorectal", df, f"NHANES {cycles} MCQ230A-D code 16 (colon) / 31 (rectum), age>=40 "
                             "(app gate), five cycles pooled. Family history / symptoms / diet are "
                             "not collected in NHANES -> LOW_FEATURE_MODEL")


# ─────────────────────────────────────────────────────────────── BRFSS (CDC, free)
# Raw: unzip `LLCP<year>XPT.zip` from
#   https://www.cdc.gov/brfss/annual_data/<year>/files/LLCP<year>XPT.zip
# into `ml/data/real/raw/` — no credentials, unlike BioLINCC/PhysioNet/NSRR. The 2025 file has
# 283 columns and ~400 k respondents. CDC renames the yes/no questions between releases
# (`DRNKANY5` -> `DRNKANY6`), so every name below goes through `_num`, which degrades an
# unmapped column to NaN instead of crashing the run (and `_write` refuses to blank a dataset).
BRFSS_COLS = [
    "_AGE80", "SEXVAR", "SEX", "_BMI5", "SLEPTIM1", "SMOKE100",
    "DRNKANY6", "DRNKANY5", "_TOTINDA", "EXERANY2",
    "_MICHD", "CVDCRHD4", "CVDINFR4", "CVDSTRK3",
    "BPHIGH6", "BPHIGH5", "_RFHYPE6", "DIABETE4",
]


_BRFSS_CACHE = None       # parse the 600 MB XPT once per run, not once per disease


def _brfss():
    """Chunked, column-projected read of the BRFSS combined file (~400 k x 283 cols).

    Returns None when the download is missing, so `prepare_brfss_*` can fall back to their
    legacy source rather than overwrite a good dataset with nothing. Parsed once and cached:
    XPT parsing is the slow part of `prepare_real.py` and several diseases share the file.
    """
    global _BRFSS_CACHE
    if _BRFSS_CACHE is not None:
        return _BRFSS_CACHE
    paths = sorted(glob.glob(os.path.join(RAW, "LLCP*.XPT")))
    if not paths:
        print("[skip] BRFSS not downloaded - see ml/data/README.md (BRFSS) -> legacy source used")
        return None
    parts = []
    for chunk in pd.read_sas(paths[-1], format="xport", chunksize=50_000):
        parts.append(chunk[[c for c in BRFSS_COLS if c in chunk.columns]])
    _BRFSS_CACHE = pd.concat(parts, ignore_index=True)
    return _BRFSS_CACHE


def _num(df, *names):
    """First of `names` present in `df`, as numeric; all-NaN Series when none exist."""
    for n in names:
        if n in df.columns:
            return pd.to_numeric(df[n], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _brfss_base(df):
    """The Phase-1 app base features BRFSS actually asks about (7 of the 14).

    Left for `_write` to fill with NaN (BRFSS surveys no family history and no symptoms):
    `family_diabetes/heart/hypertension/cancer` + the 3 screening symptoms per disease.
    `exercise_level` is 0/1 — BRFSS only asks whether there was *any* leisure activity in the
    past 30 days (`_TOTINDA`), which is coarser than the NHANES 0/1/2 cut and the app's 0-4
    scale; that limitation is recorded in the source note.
    """
    out = pd.DataFrame(index=df.index)
    age = _num(df, "_AGE80", "AGE")
    out["age"] = age.where((age >= 18) & (age <= 120))          # adults only (BRFSS rule)
    out["gender"] = _num(df, "SEXVAR", "SEX").map({1: 1.0, 2: 0.0})   # app: 1=Male, 0=Female
    bmi = _num(df, "_BMI5")                                      # BMI x 100, 9999 = "don't know"
    out["bmi"] = bmi.where((bmi > 0) & (bmi < 9999)) / 100.0
    sleep = _num(df, "SLEPTIM1")                                 # 77 = DK, 99 = refused
    out["sleep_hours"] = sleep.where((sleep >= 1) & (sleep <= 24))
    out["smoking"] = _num(df, "SMOKE100").map({1: 1.0, 2: 0.0})  # ever smoked 100 cigarettes
    out["alcohol"] = _num(df, "DRNKANY6", "DRNKANY5").map({1: 1.0, 2: 0.0})
    out["exercise_level"] = _num(df, "_TOTINDA", "EXERANY2").map({1: 1.0, 2: 0.0})
    return out


def prepare_brfss_heart():
    """BRFSS coronary heart disease -> Phase-1 `heart` vector (dataset-accuracy TODO #1).

    UCI Cleveland gave 3 usable columns on 303 rows. BRFSS cannot supply `chest_pain` or family
    history either, but it supplies age/gender/BMI/sleep/physical-activity/smoking/alcohol for
    ~400 k adults: 3 real predictors -> 7, and 303 -> a nationally-sourced sample.
    """
    df = _brfss()
    if df is None:
        return _prepare_heart_cleveland()
    out = _brfss_base(df)
    # _MICHD = CDC's derived "ever told coronary heart disease OR myocardial infarction"
    # (1=Yes, 2=No). Fall back to the two raw questions if the derived flag is ever renamed.
    m = _num(df, "_MICHD")
    if m.notna().any():
        lab = m.map({1: 1.0, 2: 0.0})
    else:
        chd, mi = _num(df, "CVDCRHD4"), _num(df, "CVDINFR4")
        lab = pd.Series(np.nan, index=out.index, dtype=float)
        lab[(chd == 1) | (mi == 1)] = 1.0              # either diagnosis = heart disease
        lab[(chd == 2) & (mi == 2)] = 0.0              # both explicitly "no"
    out["target"] = lab
    _write("heart", out, f"BRFSS {BRFSS_YEAR} (CDC, ~400k US adults): label = _MICHD (ever told "
                         "coronary heart disease or heart attack); 7 of 14 app columns real - "
                         "family history and chest-pain/shortness-of-breath/palpitations are not "
                         "surveyed in BRFSS (NaN); unweighted sample (survey weights unused)")


def prepare_brfss_stroke():
    """BRFSS stroke history -> Phase-2 `stroke` vector (replaces the Kaggle 5 110-row set).

    Also fixes a latent train/inference mismatch in the old mapping: it put the Kaggle columns
    `hypertension`/`heart_disease` (the respondent's *own* conditions) into `family_hypertension`
    / `family_heart` (the app asks the user for their *family* history), so the model learned a
    personal-history effect and then applied it to a family-history flag at inference. BRFSS has
    no family-history question, so those columns are honestly NaN here instead.
    """
    df = _brfss()
    if df is None:
        return _prepare_stroke_kaggle()
    out = _brfss_base(df)
    out["target"] = _num(df, "CVDSTRK3").map({1: 1.0, 2: 0.0})
    _write("stroke", out, f"BRFSS {BRFSS_YEAR} (CDC): label = CVDSTRK3 (ever told stroke); "
                          "7 of 16 app columns real; family history/BP/symptoms not surveyed "
                          "(NaN) - deliberately, see prepare_brfss_stroke docstring; "
                          "unweighted sample (survey weights unused)")


def main():
    os.makedirs(OUT, exist_ok=True)
    for fn in [prepare_nhanes_diabetes, prepare_nhanes_hypertension, prepare_nhanes_obesity,
               prepare_nhanes_anemia, prepare_metabolic_syndrome, prepare_nhanes_colorectal,
               prepare_nhanes_ckd, prepare_nhanes_liver,
               prepare_thyroid, prepare_brfss_heart, prepare_brfss_stroke, prepare_pcos,
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
