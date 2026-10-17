"""Diseases + screening metadata routes — 05-API-SPEC §3.

  GET /diseases                        → DISEASE_REGISTRY (ml/models/registry.py) se feed
  GET /screenings/{key}/questions      → SCREENING_QUESTIONS catalog

Registry-driven: naya disease sirf registry entry + engine se aata hai. Naya screener sirf
apna question set idhar add karo — frontend form dynamically render kar lega
(08-FRONTEND §3: questions hardcode nahi karne, naye phase ko redeploy nahi karna).

Question shape (dynamic renderer ke liye):
  id, prompt, type ("scale"|"yes_no"|"choice"|"number"),
  response_key  → screening_responses payload ka key (phase2_risk._build_vector isi se padhta)
  response_index → jab response_key list ho (gad7 answers, burnout exhaustion)
  options[{value,label}] ya min/max/step, required, profile_field (jo pehle se form mein hai)
"""
from fastapi import APIRouter, Depends, HTTPException
from backend.app.middleware.auth import get_current_user
from ml.models.registry import DISEASE_REGISTRY, active_diseases

router = APIRouter()          # prefix /api/v1/diseases
screenings_router = APIRouter()  # prefix /api/v1/screenings (05-API-SPEC §3 — alag path)

# Reusable option sets -------------------------------------------------------
_YES_NO = [{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}]
_GAD7_SCALE = [
    {"value": 0, "label": "Not at all"},
    {"value": 1, "label": "Several days"},
    {"value": 2, "label": "More than half the days"},
    {"value": 3, "label": "Nearly every day"},
]
_EXHAUSTION_SCALE = list(_GAD7_SCALE)
_SATISFACTION_SCALE = [
    {"value": 1, "label": "Very dissatisfied"},
    {"value": 2, "label": "Dissatisfied"},
    {"value": 3, "label": "Neutral"},
    {"value": 4, "label": "Satisfied"},
    {"value": 5, "label": "Very satisfied"},
]

_GAD7_PROMPTS = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid, as if something awful might happen",
]

def _yn_q(qid, prompt, response_key):
    """yes_no question factory — same shape har disease ke liye (response_key engine feature)."""
    return {"id": qid, "prompt": prompt, "type": "yes_no",
            "response_key": response_key, "required": True, "options": _YES_NO}


# {screening_key: catalog} — har active disease ka apna 3-4 question set (WS-7).
# response_key → phase2_risk._build_vector / disease_risk._build_vector feature names se match.
SCREENING_QUESTIONS = {
    # ── Phase 1 ────────────────────────────────────────────────────────────────
    "diabetes": {
        "label": "Diabetes Symptoms",
        "instructions": "Common early warning signs of high blood sugar.",
        "questions": [
            _yn_q("dm_q1", "Do you urinate much more often than usual?", "freq_urination"),
            _yn_q("dm_q2", "Do you feel unusually thirsty most of the time?", "excess_thirst"),
            _yn_q("dm_q3", "Have you lost weight without trying?", "weight_loss"),
        ],
    },
    "heart": {
        "label": "Heart Disease Symptoms",
        "instructions": "Symptoms that may point to heart problems.",
        "questions": [
            _yn_q("hd_q1", "Do you get chest pain or pressure during activity?", "chest_pain"),
            _yn_q("hd_q2", "Do you feel short of breath with mild exertion?", "short_breath"),
            _yn_q("hd_q3", "Do you notice a racing, fluttering, or pounding heartbeat?", "palpitations"),
        ],
    },
    "hypertension": {
        "label": "Hypertension Symptoms",
        "instructions": "Symptoms sometimes linked with high blood pressure.",
        "questions": [
            _yn_q("ht_q1", "Do you get frequent headaches?", "headaches"),
            _yn_q("ht_q2", "Do you often feel dizzy or lightheaded?", "dizziness"),
            _yn_q("ht_q3", "Do you have blurred vision?", "blurred_vision"),
        ],
    },
    "obesity": {
        "label": "Weight & Diet Habits",
        "instructions": "Eating patterns linked with weight gain.",
        "questions": [
            _yn_q("ob_q1", "Do you frequently drink sugary drinks or eat sweets?", "sugary_diet"),
            _yn_q("ob_q2", "Do you feel hungry again soon after meals?", "freq_hunger"),
            _yn_q("ob_q3", "Do you find it very hard to lose weight?", "hard_lose_weight"),
        ],
    },
    # ── Phase 2 ────────────────────────────────────────────────────────────────
    "stroke": {
        "label": "Stroke Warning Signs",
        "instructions": "Stroke / TIA (mini-stroke) related signs.",
        "questions": [
            _yn_q("st_q1", "Have you ever had sudden weakness or numbness on one side of the body?",
                  "tia_symptoms"),
            _yn_q("st_q2", "Have you ever had sudden trouble speaking or understanding speech?",
                  "speech_difficulty"),
            _yn_q("st_q3", "Have you been told your heartbeat is irregular (e.g. atrial fibrillation)?",
                  "irregular_heartbeat"),
        ],
    },
    "sleep_apnea": {
        "label": "Sleep Apnea (STOP-BANG subset)",
        "instructions": "4 questions + your BMI, age, gender, blood pressure complete the STOP-BANG score.",
        "questions": [
            _yn_q("sa_q1", "Do you snore loudly?", "snoring"),
            _yn_q("sa_q2", "Do you wake up feeling tired even after a full night of sleep?", "wake_tired"),
            _yn_q("sa_q3", "Has anyone seen you stop breathing or gasp during sleep?", "witnessed_apnea"),
            _yn_q("sa_q4", "Do you often feel sleepy during the day?", "daytime_sleepy"),
        ],
    },
    "gad7": {
        "label": "Anxiety (GAD-7)",
        "instructions": "Over the last 2 weeks, how often have you been bothered by the following problems?",
        "questions": [
            {
                "id": f"gad7_q{i + 1}",
                "prompt": prompt,
                "type": "scale",
                "response_key": "answers",
                "response_index": i,
                "required": True,
                "options": _GAD7_SCALE,
            }
            for i, prompt in enumerate(_GAD7_PROMPTS)
        ],
    },
    # ── Phase 3 ────────────────────────────────────────────────────────────────
    "ckd": {
        "label": "Kidney (CKD) Symptoms",
        "instructions": "Signs sometimes seen with reduced kidney function.",
        "questions": [
            _yn_q("ckd_q1", "Do you have swelling in your ankles, feet, or legs?", "ankle_swelling"),
            _yn_q("ckd_q2", "Have you noticed changes in urination (foamy, more/less frequent)?",
                  "urination_changes"),
            _yn_q("ckd_q3", "Do you feel persistently tired or low on energy?", "ckd_fatigue"),
        ],
    },
    "liver": {
        "label": "Liver Disease Symptoms",
        "instructions": "Signs that may indicate liver strain.",
        "questions": [
            _yn_q("lv_q1", "Have you noticed yellowing of the eyes or skin (jaundice)?", "jaundice"),
            _yn_q("lv_q2", "Do you have pain or swelling in the upper abdomen?", "abdominal_pain"),
            _yn_q("lv_q3", "Do you feel persistently tired or fatigued?", "liver_fatigue"),
        ],
    },
    "metabolic_syndrome": {
        "label": "Metabolic Syndrome",
        "instructions": "3 questions + waist/BP/diet/activity from earlier sections complete the IDF check.",
        "questions": [
            _yn_q("ms_q1", "Has a doctor told you your blood pressure is high?", "doctor_high_bp"),
            _yn_q("ms_q2", "Has a doctor told you your blood sugar is high?", "doctor_high_sugar"),
            _yn_q("ms_q3", "Do you often feel thirsty or urinate frequently?",
                  "frequent_thirst_urination"),
        ],
    },
    # ── Phase 4 ────────────────────────────────────────────────────────────────
    "thyroid": {
        "label": "Thyroid Disorder",
        "instructions": "4 questions — thyroid symptoms.",
        "questions": [
            _yn_q("thy_q1", "Do you often feel fatigued or exhausted during the day?", "fatigue"),
            _yn_q("thy_q2", "Have you had unexplained weight gain or loss?", "weight_change"),
            _yn_q("thy_q3", "Do you often feel unusually cold or unusually hot?", "temperature_issues"),
            _yn_q("thy_q4", "Have you noticed dry skin or thinning hair?", "hair_skin"),
        ],
    },
    "pcos": {
        "label": "PCOS",
        "instructions": "Shown only to female users (registry requires_gender = Female).",
        "questions": [
            _yn_q("pcos_q1", "Are your menstrual periods irregular?", "irregular_periods"),
            _yn_q("pcos_q2", "Have you gained weight without a clear reason?", "weight_gain"),
            _yn_q("pcos_q3", "Have you noticed excess facial or body hair growth?", "excess_hair"),
            _yn_q("pcos_q4", "Do you have persistent acne or very oily skin?", "acne"),
        ],
    },
    "anemia": {
        "label": "Anemia",
        "instructions": "4 questions + your diet quality rating (from earlier section).",
        "questions": [
            _yn_q("anemia_q1", "Do you feel unusually tired or fatigued often?", "frequent_fatigue"),
            _yn_q("anemia_q2", "Do you look pale or feel cold often?", "pale_cold"),
            _yn_q("anemia_q3", "Do you often feel dizzy or lightheaded?", "lightheadedness"),
            _yn_q("anemia_q4", "Are your nails brittle or spoon-shaped?", "brittle_nails"),
            # diet_quality profile column se padha jata hai (phase2_risk._build_vector)
            {"id": "anemia_q5", "prompt": "How would you describe your everyday diet?",
             "type": "choice", "response_key": "diet_quality", "required": True,
             "profile_field": "diet_quality",
             "options": [{"value": "poor", "label": "Poor"},
                         {"value": "average", "label": "Average"},
                         {"value": "good", "label": "Good"}]},
        ],
    },
    "burnout": {
        "label": "Burnout",
        "instructions": "Work pattern + 3 emotional-exhaustion items (0–3 scale).",
        "questions": [
            {"id": "bo_q1", "prompt": "How many hours do you typically work per week?",
             "type": "number", "response_key": "work_hours", "required": True,
             "min": 0, "max": 80, "step": 1},
            {"id": "bo_q2", "prompt": "How satisfied are you with your job?",
             "type": "scale", "response_key": "job_satisfaction", "required": True,
             "options": _SATISFACTION_SCALE},
            {"id": "bo_q3", "prompt": "I felt exhausted because of my work", "type": "scale",
             "response_key": "exhaustion", "response_index": 0, "required": True,
             "options": _EXHAUSTION_SCALE},
            {"id": "bo_q4", "prompt": "I felt tired when I got up in the morning", "type": "scale",
             "response_key": "exhaustion", "response_index": 1, "required": True,
             "options": _EXHAUSTION_SCALE},
            {"id": "bo_q5", "prompt": "I felt emotionally drained because of my work",
             "type": "scale", "response_key": "exhaustion", "response_index": 2, "required": True,
             "options": _EXHAUSTION_SCALE},
        ],
    },
    # ── Phase 5 (cancer screening — stricter disclaimer) ─────────────────────────
    "colorectal": {
        "label": "Colorectal Cancer — screening signs",
        "instructions": "Population-level screening questions (not a diagnosis).",
        "questions": [
            _yn_q("cr_q1", "Have you noticed blood in your stool?", "blood_in_stool"),
            _yn_q("cr_q2", "Have your bowel habits changed recently (constipation/diarrhea)?",
                  "bowel_change"),
            _yn_q("cr_q3", "Have you lost weight without trying?", "colorectal_weight_loss"),
        ],
    },
    "lung_cancer_exposure": {
        "label": "Lung Cancer — risk factors",
        "instructions": "Cancer screening questions (stricter disclaimer applies).",
        "questions": [
            _yn_q("lc_q1", "Are you regularly exposed to secondhand smoke at home or work?",
                  "passive_smoke"),
            _yn_q("lc_q2", "Do you have a persistent cough (more than 3 weeks)?", "persistent_cough"),
            _yn_q("lc_q3", "Have you ever coughed up blood?", "coughing_blood"),
            _yn_q("lc_q4", "Do you get short of breath easily?", "breath_shortness"),
        ],
    },
}


def _registry_config_for_screening(screening_key: str):
    for cfg in DISEASE_REGISTRY.values():
        if cfg.screening_key == screening_key:
            return cfg
    return None


@router.get("")
def list_diseases(current_user: dict = Depends(get_current_user)):
    """Active DISEASE_REGISTRY entries — frontend isi se decide karta hai kaunse sections
    render karne hain (05-API-SPEC §3, 08-FRONTEND §3)."""
    return {
        "diseases": [
            {
                "disease_key": cfg.disease_key,
                "label": cfg.label,
                "category": cfg.category,
                "engine": cfg.engine,
                "scoring": cfg.scoring,
                "requires": ["health_profile"],
                # Dynamic screening sections (WS-4): frontend in fields se form banata hai
                "screening_key": cfg.screening_key or None,
                "requires_screening": bool(cfg.screening_key),
                "active": cfg.active,
                # Inference gates (06): pcos card sirf Female ko, colorectal sirf age>=40
                "min_age": cfg.min_age or None,
                "requires_gender": cfg.requires_gender,
            }
            for cfg in active_diseases().values()
        ]
    }


@screenings_router.get("/{screening_key}/questions")
def get_screening_questions(
    screening_key: str,
    current_user: dict = Depends(get_current_user),
):
    """Question set for one screener (05-API-SPEC §3) — form ka dynamic renderer isi se chalta hai."""
    entry = SCREENING_QUESTIONS.get(screening_key)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No question set for screening key '{screening_key}'",
        )
    cfg = _registry_config_for_screening(screening_key)
    return {
        "screening_key": screening_key,
        "label": entry["label"],
        "disease_key": cfg.disease_key if cfg else None,
        "requires_gender": cfg.requires_gender if cfg else None,
        "min_age": (cfg.min_age or None) if cfg else None,
        "instructions": entry.get("instructions"),
        "questions": entry["questions"],
    }
