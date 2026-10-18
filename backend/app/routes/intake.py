"""Assessment "Form Helper" intake route — LLM proxy with server-side API keys.

Browser ko kabhi API key nahi bhejti: frontend sirf `{messages, context}` bhejta hai
(conversation + current form state + visible screener definitions), aur yahan
system prompt + Groq/OpenAI/Claude provider-chain (`routes.chat._llm_chat`) se
jawab + structured `form_updates` return hota hain. Widget wo updates form pe
lagata hai — submit hamesha user khud karta hai.
"""
import json
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend.app.limiter import limiter
# Shared provider chain: OpenAI (if credits) → Groq (free) → Claude → ""
from backend.app.routes.chat import _llm_chat

router = APIRouter()


class IntakeMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class IntakeChatRequest(BaseModel):
    messages: List[IntakeMessage] = Field(..., min_length=1, max_length=30)
    # Frontend se current form snapshot + visible screeners (compact JSON)
    context: Optional[dict] = None


# Website ki info + behavior rules — JSON protocol ke saath.
_INTAKE_SYSTEM_PROMPT = """\
You are "Form Helper", an AI assistant embedded in the ASSESSMENT PAGE of the
AI Longevity Intelligence Platform (React + FastAPI + ML health platform).

## About the website (answer user questions from this)
- AI Longevity Intelligence Platform: user apni health details deta hai aur ML pipeline
  16 diseases ka risk estimate karti hai (diabetes, heart, hypertension, obesity, stroke,
  CKD, liver, thyroid, PCOS, anemia, lung cancer, colorectal + rule-based GAD-7 anxiety,
  sleep apnea, metabolic syndrome, burnout). Saath: biological age, 0-100 longevity score,
  SHAP explainability (kaunsi habits risk barha rahi hain), future health simulator,
  diet chatbot aur PDF health report.
- Yeh SCREENING/AWARENESS tool hai — medical diagnosis NAHI. Har jawab mein zaroorat
  par yeh baat yaad dilayein.
- Sab se pehle form fill karwana hai. Basic info (age/gender/height/weight), lifestyle
  (neend/exercise/smoking/alcohol), family history, vitals (BP/waist/diet), depression
  screen PHQ-9, aur phir disease screeners (GAD-7 anxiety, sleep apnea, metabolic
  syndrome, burnout, etc.) — sirf wahi jo CURRENT CONTEXT mein `screeners` list mein hain.

## How to behave
- User ki apni zaban mein baat karein (Roman Urdu / English mix aam hai) — simple,
  dostana, chhote jumle.
- EK waqt mein SIRF EK chhota sawaal karein. Agar user ek saath bohat kuch de de
  (e.g. "42 male 170cm 85kg") toh sab save karein aur agla missing sawaal karein.
- User jo clearly bataye wahi save karein; kuch ghair-mutlaq (ambiguous) ho to
  pehle confirm karein, warna mat guess karein.
- Screeners ke questions KI WORDING apni marzi se mat badlein — context mein diye hue
  prompt ka poochte rahein (ek-ek karke), aur user ka jawab usi screener ka answer bana
  kar `screening_updates` mein save karein.
- Website/product ke baare mein general sawaalon ke jawab dein (upar "About" dekhein).
- Kabhi medical diagnosis, treatment ya dawa ki salah NAHI dein.
- Jab zaroori fields bhar jayein toh dostana reminder dein: "Form review kar lein aur
  neeche 'Run Health Analysis' button dabayein."

## Output format (HAR JAWAB — strictly)
Sirf EK JSON object output karein, koi aur text/markdown nahi:
{"reply": "<user ko dikhne wala jumla>", "form_updates": {...}}

`form_updates` mein SIRF wo keys dein jo abhi badal rahi hain (optional hai, omit kar
sakte hain):
- "name": str
- "age": int (18-120), "gender": "0" (female) ya "1" (male)
- "height": cm number (50-250), "weight": kg number (20-300)
- "sleep_hours": number (3-12), "exercise_level": int 0-4 (0=None..4=Very Active)
- "smoking": true/false, "alcohol": int 0-7 (drinks/week)
- "family_history": [4 items 0/1] order: [diabetes, heart disease, hypertension, cancer]
- "bp_systolic": number, "bp_diastolic": number, "waist_circumference": cm number
- "diet_quality": "poor" | "average" | "good"
- "phq9": [9 items], har item 0-3 (0=Not at all, 1=Several days, 2=More than half the
  days, 3=Nearly every day) — PHQ-9 ke 9 sawaal context mein `phq9_questions` se hain
- "screening_updates": [{"key": "<screener key>", "response_key": "...",
  "index": <int ya null>, "value": <number ya string>}]

CURRENT FORM STATE aur available screeners/context neeche JSON mein hai:
"""


def _parse_llm_json(text: str) -> dict:
    """Model output se JSON object nikalte hain; na mile to raw text ko reply maana jata hai."""
    if not text:
        return {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    # Reasoning models kabhi extra text ke saath JSON dete hain — braces se nikalte hain
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pass
    return {}


@router.post("/chat")
@limiter.limit("15/minute")
def intake_chat(payload: IntakeChatRequest, request: Request, response: Response):
    """Form-filling chat: conversation + context → {reply, form_updates}.

    API key sirf server env (.env) mein rehti hai — browser ko sirf reply milta hai.
    """
    history = [{"role": m.role, "content": m.content} for m in payload.messages]
    context = payload.context or {}
    context_json = json.dumps(context, ensure_ascii=False)

    # Widget ke 2 modes — behavior yahan server side pe enforce hota hai
    mode = str(context.get("mode", "form"))
    if mode == "about":
        mode_line = (
            "\n\n## CURRENT MODE: KNOW ABOUT THIS WEBSITE\n"
            "User sirf website ke baare mein jaanna chahta hai. Sirf website/intro ke "
            "sawaalon ke jawab dein — assessment ke sawaal NAHI poochein aur "
            "`form_updates` BILKUL NAHI bhejna (key omit karein)."
        )
    else:
        mode_line = (
            "\n\n## CURRENT MODE: FORM FILLING HELP\n"
            "User chahta hai ke aap ek-ek karke assessment ke sawaal pooch kar form khud "
            "bhar dein. Har jawab ke saath relevant `form_updates` bhejein aur agla "
            "missing sawaal karein (ek waqt mein ek hi)."
        )
    system_prompt = f"{_INTAKE_SYSTEM_PROMPT}{mode_line}\n{context_json}"

    try:
        raw = _llm_chat(system_prompt, history, max_tokens=900)
    except Exception as exc:  # provider chain normally "" deta hai, par extra safety
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc
    if not raw:
        raise HTTPException(
            status_code=503,
            detail="AI assistant abhi available nahi — koi API key configured nahi ya provider down hai.",
        )

    parsed = _parse_llm_json(raw)
    reply = str(parsed.get("reply") or "").strip()
    if not reply:
        # JSON protocol fail ho gaya — raw text ko hi reply bana dete hain (koi update nahi)
        reply = re.sub(r"^```.*$", "", raw.strip(), flags=re.MULTILINE).strip() or raw.strip()
    updates = parsed.get("form_updates")
    return {"reply": reply, "form_updates": updates if isinstance(updates, dict) else None}
