# ml/report.py
"""Build ml/reports/REPORT.md — the ML_TRAINING.md §12 report for the FYP documentation.

Reads the *actual* artifacts written by `ml/train.py` (every `ml/reports/<disease>_metrics.json`
plus the matching model card) so the document can never drift from the trained models.

Run:  python -m ml.report
"""
import json
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPORTS = _HERE / "reports"
CARDS = _HERE / "models" / "model_cards"

PREPROCESSING = (
    "Stratified 80/20 train/test split FIRST (`SEED=42`); median imputation + standard scaling "
    "inside the pipeline (fit on training folds only); SMOTE inside the imblearn pipeline "
    "(training folds only); RandomForest(120, depth 8) + XGBoost(120, depth 4) + "
    "LogisticRegression soft-vote (0.4/0.4/0.2); sigmoid calibration (3-fold); decision "
    "threshold from out-of-fold F2 (recall-oriented). The test set is scored once."
)

DISCLAIMER = (
    "> **This is a screening and awareness tool, not a diagnostic device.** Models must be "
    "revalidated on local clinical data before any real-world use."
)

def _load():
    metrics = []
    for path in sorted(REPORTS.glob("*_metrics.json")):
        m = json.loads(path.read_text())
        card_path = CARDS / f"{m['disease']}.json"
        if card_path.exists():
            m["_card"] = json.loads(card_path.read_text())
        metrics.append(m)
    return metrics


def _fmt_flags(m):
    flags = list(m.get("flags", []))
    missing = m.get("missing_features") or []
    parts = []
    if flags:
        parts.append(", ".join(flags))
    if missing:
        parts.append("columns unusable in training (all-NaN in the source): " + ", ".join(missing))
    return "; ".join(parts) or "none"


def build():
    ms = _load()
    n_pass = sum(1 for m in ms if m["status"] == "PASS")
    lines = [
        "# ML Training Report (ML_TRAINING.md §12)",
        "",
        f"Generated `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}` from "
        f"`ml/reports/*_metrics.json` + `ml/models/model_cards/*.json` — "
        f"regenerate with `python -m ml.report`.",
        "",
        f"**{len(ms)} diseases trained · {n_pass} PASS · {len(ms) - n_pass} BELOW_TARGET** "
        "(targets: AUC ≥ 0.85 and macro F1 ≥ 0.80 — a missed target is reported, not hidden).",
        "",
        "## Summary",
        "",
        "| Disease | Dataset | Rows | Pos. rate | Features | CV AUC | Test AUC | Recall | Macro F1 | Status | Flags |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m in ms:
        ds = m["dataset"]
        short = ds.split(" — ")[0].split(" -- ")[0].split(" (")[0].strip()
        if len(short) > 40:
            short = short[:40].rstrip() + "…"
        lines.append(
            f"| `{m['disease']}` | {short} | {m['rows']} | {m['positive_rate']:.2%} | "
            f"{len(m['features'])} | {m['cv_auc_mean']:.3f} ± {m['cv_auc_std']:.3f} | "
            f"{m['test_auc']:.3f} | {m['test_recall']:.3f} | {m['test_macro_f1']:.3f} | "
            f"{m['status']} | {_fmt_flags(m)} |")
    lines += ["", f"{DISCLAIMER}", "", "## Per disease", ""]

    for m in ms:
        name = m["disease"]
        lines += [f"### `{name}`", "",
                  f"- **Dataset:** {m['dataset']}",
                  f"- **Rows:** {m['rows']} (positive rate {m['positive_rate']:.2%})",
                  f"- **Features ({len(m['features'])}):** {', '.join(m['features'])}",
                  f"- **Preprocessing:** {PREPROCESSING}",
                  f"- **CV AUC:** {m['cv_auc_mean']:.4f} ± {m['cv_auc_std']:.4f}  |  "
                  f"**Test AUC:** {m['test_auc']:.4f}  |  **Recall:** {m['test_recall']:.4f}  |  "
                  f"**Precision:** {m['test_precision']:.4f}  |  **Macro F1:** {m['test_macro_f1']:.4f}  |  "
                  f"**Brier:** {m['brier_score']:.4f}  |  **Threshold:** {m['threshold']}"]
        shap = m.get("top_features_shap") or {}
        if shap:
            lines.append("- **Top SHAP features:** " + ", ".join(
                f"`{k}` {v}" for k, v in list(shap.items())[:6]))
        lines.append(f"- **Flags:** {_fmt_flags(m)}")
        lines.append(f"- **Status:** {m['status']}")
        card = m.get("_card") or {}
        lims = card.get("known_limitations") or []
        if lims:
            lines.append("- **Limitations:**")
            lines += [f"  - {x}" for x in lims]
        lines.append("")

    (REPORTS / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORTS / 'REPORT.md'} for {len(ms)} diseases")
    return ms


if __name__ == "__main__":
    build()
