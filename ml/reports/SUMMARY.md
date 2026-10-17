# Training Summary

| Disease | Rows | CV AUC | Test AUC | Recall | Macro F1 | Brier | Status | Flags |
|---|---|---|---|---|---|---|---|---|
| anemia | 3000 | 0.7594±0.0321 | 0.7558 | 0.7474 | 0.5533 | 0.113 | BELOW_TARGET | LOW_FEATURE_MODEL |
| ckd | 400 | 0.9359±0.0298 | 0.9547 | 0.98 | 0.6772 | 0.0699 | BELOW_TARGET | SMALL_DATASET, LOW_FEATURE_MODEL |
| colorectal | 3882 | 0.5785±0.0448 | 0.6942 | 0.0909 | 0.5189 | 0.0139 | BELOW_TARGET | HEAVY_IMBALANCE, LOW_FEATURE_MODEL |
| depression | 776 | 0.9959±0.0024 | 0.9978 | 1.0 | 0.9358 | 0.0181 | PASS | EXPECTED_LEAKAGE_LABEL_FROM_FEATURES |
| diabetes | 3000 | 0.8861±0.0235 | 0.8754 | 0.8548 | 0.6541 | 0.0772 | BELOW_TARGET | LOW_FEATURE_MODEL |
| gad7 | 776 | 0.9968±0.0026 | 0.9991 | 1.0 | 0.905 | 0.0139 | PASS | EXPECTED_LEAKAGE_LABEL_FROM_FEATURES |
| heart | 303 | 0.7742±0.0338 | 0.7008 | 0.8214 | 0.5978 | 0.221 | BELOW_TARGET | SMALL_DATASET, LOW_FEATURE_MODEL |
| hypertension | 3000 | 0.8032±0.016 | 0.8099 | 0.9668 | 0.6221 | 0.1664 | BELOW_TARGET | LOW_FEATURE_MODEL |
| liver | 583 | 0.6245±0.026 | 0.6492 | 0.9398 | 0.4777 | 0.1963 | BELOW_TARGET | LOW_FEATURE_MODEL |
| lung_cancer | 309 | 0.6135±0.1123 | 0.7199 | 1.0 | 0.4655 | 0.1066 | BELOW_TARGET | SMALL_DATASET, LOW_FEATURE_MODEL |
| metabolic_syndrome | 3000 | 0.9027±0.0072 | 0.898 | 0.9349 | 0.7245 | 0.1146 | BELOW_TARGET | LOW_FEATURE_MODEL |
| obesity | 3000 | 0.7272±0.0244 | 0.7218 | 0.9444 | 0.5362 | 0.1833 | BELOW_TARGET | LOW_FEATURE_MODEL |
| pcos | 541 | 0.8412±0.0259 | 0.872 | 0.8611 | 0.7523 | 0.1241 | BELOW_TARGET | - |
| sleep_apnea | 374 | 0.9128±0.0642 | 0.9529 | 1.0 | 0.9103 | 0.0613 | PASS | SMALL_DATASET, LOW_FEATURE_MODEL |
| stroke | 5110 | 0.821±0.0167 | 0.8142 | 0.82 | 0.5058 | 0.0433 | BELOW_TARGET | HEAVY_IMBALANCE, LOW_FEATURE_MODEL |
| thyroid | 3163 | 0.5875±0.0925 | 0.5365 | 0.6333 | 0.2928 | 0.045 | BELOW_TARGET | HEAVY_IMBALANCE, LOW_FEATURE_MODEL |

## Legend

- **PASS** = test AUC >= 0.85 AND macro F1 >= 0.8
- **BELOW_TARGET** = at least one target missed (mostly data-limited — see flags below)
- **LOW_FEATURE_MODEL** = the source dataset does not collect some app features, so the model cannot use them (honest limitation, not a bug)
- **SMALL_DATASET** = fewer than 500 rows
- **HEAVY_IMBALANCE** = positive rate below 10% or above 90%
- **EXPECTED_LEAKAGE_LABEL_FROM_FEATURES** = the label is derived from the features by design (mirrors the app's clinical rule for the PHQ-9/GAD-7 screeners), so the near-perfect AUC is expected and the ML model adds no new signal over the rule
- **SUSPICIOUS_POSSIBLE_LEAKAGE** = test AUC > 0.97 without a documented reason — investigate before trusting
