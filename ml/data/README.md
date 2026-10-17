# ml/data — datasets & sources

| Path | Status | Used by |
|---|---|---|
| `ml/data/real/` | **ACTIVE** — real, app-aligned datasets (16 diseases) | `ml/train.py` (via `ml/train_config.py`) |
| `ml/data/real/raw/` | raw downloads (immutable inputs) | `ml/data/prepare_real.py` |

Ground Rule 1 of `docx.md/ML_TRAINING.md`: **no model is trained on synthetic data.** Every
artifact in `ml/models/` is trained from a real dataset listed below. The old synthetic
generators (`ml/data/generate_datasets.py`, `ml/data/generate_synthetic.py`) and the
`ml/data/synthetic/*.csv` files they wrote were **deleted on 2026-10-17**; the feature-name
schema they carried had already moved to `ml/models/constants.py` (`PHASE1_SCHEMAS`).

> **`burnout` deliberately has no ML model.** No real dataset matches the app's burnout inputs,
> so the app serves the clinically-validated rule `ScreeningClassifier.score_burnout()` rather
> than a model trained on generated data — see [Why burnout has no ML model](#why-burnout-has-no-ml-model).

## How the active data is produced

```
ml/data/real/raw/*            (raw NHANES .xpt + UCI/Kaggle .csv/.data, downloaded once)
        │  python ml/data/prepare_real.py
        ▼
ml/data/real/<disease>.csv    (EXACTLY the app's inference columns + `target`)
        │  python -m ml.train --all
        ▼
ml/models/<disease>.joblib  +  ml/reports/<disease>_metrics.json  +  model cards
```

`prepare_real.py` renames/derives each raw file into the app's fixed feature vector
(`ml/models/disease_risk.py::_build_vector`, `ml/models/phase2_risk.py::_build_vector`) so
that **training columns == inference columns** (BUG-5) and applies the §5
"label-from-feature" exclusions (e.g. BP is dropped from the hypertension features because
BP defines its label).

## Sources & licences

| Disease | Raw file(s) | Source | Licence |
|---|---|---|---|
| diabetes | `DEMO_J, BMX_J, SMQ_J, ALQ_J, PAQ_J, SLQ_J, DIQ_J` | NHANES 2017–2018 (J), US CDC/NCHS | US public domain |
| hypertension | `… + BPX_J` | NHANES 2017–2018 (J) | US public domain |
| obesity | `…` (BMI label) | NHANES 2017–2018 (J) | US public domain |
| anemia | `… + CBC_J` (haemoglobin) | NHANES 2017–2018 (J) | US public domain |
| metabolic_syndrome | `… + BPX_J, BMX_J(waist), BIOPRO_J, TRIGLY_J, HDL_J, BPQ_J` | NHANES 2017–2018 (J) | US public domain |
| sleep_apnea | `sleep.csv` | Kaggle "Sleep Health & Lifestyle" | CC0 |
| heart | `processed.cleveland.data` | UCI ML Repo — Cleveland Heart Disease | CC BY 4.0 |
| ckd | `ckd.csv` | UCI ML Repo — Chronic Kidney Disease | CC BY 4.0 |
| liver | `ilpd.csv` | UCI ML Repo — Indian Liver Patient Dataset | CC BY 4.0 |
| thyroid | `hypothyroid.data` | UCI ML Repo — Hypothyroid | CC BY 4.0 |
| stroke | `stroke.csv` | Kaggle "Stroke Prediction Dataset" (fedesoriano) | CC0 |
| pcos | `pcos.csv` | Kaggle "PCOS" | see dataset page |
| lung_cancer | `lung_cancer.csv` | Kaggle "Lung Cancer" survey | see dataset page |
| gad7 | `gad7_raw` (GAD-7 items) | Figshare GAD-7 questionnaire | CC BY |
| depression | `gad7_raw` (PHQ-9 items) | Figshare PHQ-9 questionnaire | CC BY |
| colorectal | `… + MCQ_J` (MCQ230A-D) | NHANES 2017–2018 (J) | US public domain |
| ~~burnout~~ | `burnout_mendeley.xlsx` + questionnaire `.pdf` | Mendeley Data, "Burnout Risks Bangladeshi Physicians" (`10.17632/3d7h58d4k3.3`) | CC BY 4.0 — **downloaded, NOT used** (not app-aligned) |

> Licences are recorded from each dataset's landing page. Re-verify before any redistribution.

## Honesty notes (read before trusting a metric)

* **App-aligned projection, not the full source.** Many real datasets do not collect the
  app's lifestyle/symptom questions, so those columns are `NaN` for every row. The imputer
  skips them and the model simply cannot learn from them — this is recorded per dataset as
  `LOW_FEATURE_MODEL` in `ml/train_config.py` and in each model card.
* **Labels derived from the same inputs already exist in the app** (GAD-7 ≥ 10, PHQ-9 ≥ 10,
  IDF metabolic-syndrome ≥ 3/5). These are flagged
  `EXPECTED_LEAKAGE_LABEL_FROM_FEATURES` by `ml/train.py` when test AUC is very high; they
  exist to *validate* the clinical rule, not to beat it.
* **Small datasets** (< 500 rows: heart, ckd, liver, pcos, lung_cancer, sleep_apnea) carry a
  `SMALL_DATASET` flag and wide confidence intervals.
* **Targets are targets, not requirements.** `TARGET_AUC=0.85` / `TARGET_MACRO_F1=0.80`;
  a model that misses them is reported as `BELOW_TARGET` in `ml/reports/SUMMARY.md`, not
  hidden.

## Why burnout has no ML model

The app's burnout inputs are `work_hours`, `job_satisfaction` (1–5) and three exhaustion items
(0–3). A real candidate dataset was found and downloaded — **Mendeley Data, "Burnout Risks
Bangladeshi Physicians"** (`10.17632/3d7h58d4k3.3`, CC BY 4.0, 1 434 rows + questionnaire PDF)
— but it was **rejected because its columns mean something different from the app's inputs**
(BUG-5: training columns must equal inference columns). The questionnaire confirms why:

| app input | app meaning | Mendeley column | what that column actually is (per the questionnaire) |
|---|---|---|---|
| `work_hours` | hours per week (0–80) | `Working_Hour` | nominal **bin code** 1–6; bin edges are not published |
| `job_satisfaction` | 1–5 satisfaction rating | `Dissatisfaction` | *symptom type*: 1=Anxiety, 2=Fatigue, 3=Insomnia, 4=Agitation, 5=Depression |
| `exhaustion_1..3` | 3 items × 0–3 | `Mental_Disturbances` | *coping strategy*: 1=Switch workplace, 2=Medication, 3=Vacation, 4=Time management, … 6=Social-skill training |

Trained anyway with the most defensible mapping (1 of 5 columns), it scores **test AUC 0.515 —
chance**. The dataset also stores no MBI/self-test item scores, only the derived severity bin.
So the honest outcome is **no ML model**: the app serves the rule-based
`ScreeningClassifier.score_burnout()`, which is a clinical rule (not random), and no synthetic
placeholder is produced for API/UI completeness.

### The options that were evaluated (identical `ml/train.py` pipeline, `SEED=42`)

| option | rows | positive rate | usable app features | CV AUC | test AUC | verdict |
|---|---|---|---|---|---|---|
| colorectal — REAL NHANES `MCQ_J` | 3 882 | 1.4 % | 4 / 9 | 0.579 ± 0.045 | **0.694** | **used** — real signal (SHAP top: `age` 0.72, then `exercise_level`, `smoking`, `alcohol`) |
| colorectal — generated | 1 500 | 38.4 % | 9 / 9 | 0.833 ± 0.030 | 0.752 | deleted — a *higher* score with zero meaning (the label was generated from the same latent factor as the features) |
| burnout — REAL Mendeley | 1 434 | 75.5 % | 1 / 5 (wrong semantics) | 0.521 ± 0.037 | 0.515 | discarded — chance level |
| burnout — generated | 1 200 | 42.8 % | 5 / 5 | 0.818 ± 0.025 | 0.877 | deleted — placeholder, no real-world evidence |

The generated colorectal row is the lesson worth quoting in the FYP report: a generated dataset
can be tuned to *outscore* the real one while carrying no real information. The real model is
preferred despite the lower AUC, and no generated artifact survives in the repo.

## Row counts

| Disease | Rows used | Source rows | Note |
|---|---|---|---|
| diabetes | 3000* | 8709 | stratified subsample |
| hypertension | 3000* | 6717 | stratified subsample |
| obesity | 3000* | 8005 | stratified subsample |
| anemia | 3000* | 7528 | stratified subsample |
| metabolic_syndrome | 3000* | 6175 | stratified subsample |
| colorectal | 3882 | 3882 | full (age ≥ 40 app gate) — only **55 positives** |
| stroke | 5110 | 5110 | full |
| thyroid | 3163 | 3162 | full |
| gad7 | 776 | 776 | full |
| depression | 776 | 776 | full |
| liver | 583 | 583 | full |
| pcos | 541 | 541 | full |
| ckd | 400 | 400 | full |
| sleep_apnea | 374 | 374 | full |
| lung_cancer | 309 | 309 | full |
| heart | 303 | 303 | full |

`*` **NHANES subsample.** `prepare_real.py` caps the five big NHANES tables at
`NHANES_MAX_ROWS = 3000` with a **seeded, target-stratified** sample (`SEED=42`), so the positive
rate is unchanged. Reason: the spec pipeline does ~36 RF+XGB fits per disease
(5-fold CV AUC + a calibrated `cross_val_predict` + calibration + SHAP). Measured on this
4-vCPU machine that is ~30-50 s per fit → ~25 min for a 6-9 k-row table, i.e. ~2 h for those
five alone. 3,000 rows keeps the whole 16-disease run reasonable and is ample for the 7-14 app
features. `colorectal` is deliberately **not** capped: it has only 55 positives, so dropping rows
would throw away cases. Widen `NHANES_MAX_ROWS` (or set it to `10**9`) and re-run to use the full
tables.

## Exact source URLs (downloaded 2026-10-14)

NHANES 2017-2018 (J) — base `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/`
(`DEMO_J`, `BMX_J`, `BPX_J`, `SMQ_J`, `ALQ_J`, `PAQ_J`, `SLQ_J`, `DIQ_J`, `BPQ_J`, `MCQ_J`,
`CBC_J`, `BIOPRO_J`, `TRIGLY_J`, `HDL_J`, `GHB_J`, `DPQ_J` — all `.xpt`).

| Raw file | URL |
|---|---|
| `ilpd.csv` | `https://archive.ics.uci.edu/ml/machine-learning-databases/00225/Indian%20Liver%20Patient%20Dataset%20(ILPD).csv` |
| `processed.cleveland.data` | `https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data` |
| `hypothyroid.data` | `https://archive.ics.uci.edu/ml/machine-learning-databases/thyroid-disease/hypothyroid.data` |
| `ChronicKidneyDisease.zip` | `https://archive.ics.uci.edu/static/public/336/chronic+kidney+disease.zip` (kept for provenance; the `.rar` inside needs unrar/7-Zip, so the CSV mirror below is used) |
| `ckd.csv` | `https://raw.githubusercontent.com/dphi-official/Datasets/master/Chronic%20Kidney%20Disease%20(CKD)%20Dataset/ChronicKidneyDisease.csv` |
| `stroke.csv` | `https://raw.githubusercontent.com/chandanverma07/DataSets/master/healthcare-dataset-stroke-data.csv` |
| `sleep.csv` | `https://raw.githubusercontent.com/broskunta/Sleep-Health-and-Lifestyle-Dataset/main/Sleep_health_and_lifestyle_dataset.csv` |
| `pcos.csv` | `https://raw.githubusercontent.com/NEHAKIRANNAYAK/PCOS-Detection/main/PCOS_data.csv` |
| `lung_cancer.csv` | `https://raw.githubusercontent.com/Wafulaprecy/Lung-cancer/main/lung_cancer_survey.csv` |
| `gad7_raw` (GAD-7 **and** PHQ-9 items) | `https://ndownloader.figshare.com/files/12990629` |
| `burnout_mendeley.xlsx` (kept for provenance, not trained) | `https://data.mendeley.com/public-files/datasets/3d7h58d4k3/files/5b94f2ba-cbf5-45f4-92fd-4985faa2dc2d/file_downloaded` |
| `burnout_mendeley_questionnaire.pdf` (kept for provenance) | `https://data.mendeley.com/public-files/datasets/3d7h58d4k3/files/1d5728a9-a485-49cb-976f-733ae311ead3/file_downloaded` |

## Duplicate-row investigation (ML_TRAINING.md §5)

Checked on the **raw source files**. A duplicate inside the coarse app-aligned space is *not*
evidence of duplicate records (many distinct people share the same age/gender/lifestyle
answers — e.g. the age+gender-only projections for thyroid/anemia look heavily duplicated by
construction).

| Source | exact duplicate rows |
|---|---|
| stroke (5110), pcos (541), sleep (374), ckd (400), cleveland (303), GAD-7/PHQ-9 (776) | 0 |
| ILPD (583) | 13 |
| hypothyroid (3163) | 77 |
| lung cancer survey (309) | 33 |

`lung_cancer` (309 rows, 33 duplicates, positive rate 0.874) is the least trustworthy dataset
here and already carries `SMALL_DATASET` + heavy-imbalance caveats. Duplicates were **not**
removed: that would shrink an already tiny dataset, and the duplicates exist in the source, not
in the mapping.

## Re-running

```powershell
python ml/data/prepare_real.py            # raw/ -> ml/data/real/*.csv  (app-aligned, seeded cap)
python -m ml.train --all                  # ml/models/*.joblib + ml/reports/*_metrics.json + SUMMARY.md
python -m ml.smoke_test                   # acceptance §10 check on every trained artifact
python -m ml.report                       # -> ml/reports/REPORT.md (ML_TRAINING §12 report)
```

`ml/reports/SUMMARY.md` and `ml/reports/REPORT.md` are both generated from the metrics JSONs
(`python -m ml.train --summary` and `python -m ml.report`), so they can never drift from the
trained models.

## Limitations (state these in the FYP report)

* Public datasets are small and population-specific (NHANES = US adults, ILPD = Indian
  patients, the Kaggle sets are tiny), so performance on Pakistani users is unproven —
  revalidate on local clinical data before any real deployment.
* The app-aligned projection is narrower than published baselines, so several diseases land in
  `BELOW_TARGET`; that is the honest result (Ground Rule 4), not a bug.
* Derived fields are approximations: BMI-category → BMI (sleep apnoea), questionnaire-total
  labels (GAD-7/PHQ-9), IDF composite (metabolic syndrome).
* The three non-NHANES-derived NHANES diseases (hypertension/obesity/anemia) deliberately drop
  the measurement that defines their label (§5), leaving very few usable predictors.
* **`colorectal`** is the weakest real model: 55 positives in 3 882 rows (1.4 %), only 4 of 9 app
  features available, test AUC 0.694 and the test set contains ~11 cases. Treat it as a
  population-level *awareness* signal; `thyroid` (0.537) is close to chance for the same reason.
* **`burnout`** has no ML model at all: the only real candidate dataset is not app-aligned, so
  the app serves the rule-based `ScreeningClassifier.score_burnout()`.
* This is a **screening and awareness tool, not a diagnostic device**.
