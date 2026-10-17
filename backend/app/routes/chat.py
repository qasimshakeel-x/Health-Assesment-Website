"""Diet Chat route — rule-based health diet chatbot with risk-aware context + live API integrations."""
import os
import re
import uuid
import random
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.models.database import get_db, User, PredictionResult, UserProfile
from backend.app.schemas.user import ChatMessage, ChatResponse
from backend.app.middleware.auth import get_current_user
from backend.app.services.health_api import (
    search_nutrition, search_exercises, calculate_macros,
    format_nutrition, format_nutrition_comparison, format_exercises,
    format_fitness_plan, format_macro_response,
)

router = APIRouter()

DISCLAIMER = "\n\n⚕️ *This is AI-generated dietary guidance, not medical advice. Please consult a registered dietitian or healthcare provider for personalized plans.*"


# ─── Muscle & exercise type mappings for API ───
MUSCLE_MAP = {
    "chest": "chest", "pecs": "chest", "pectoral": "chest", "chest muscle": "chest",
    "biceps": "biceps", "bicep": "biceps", "arms": "biceps",
    "triceps": "triceps", "tricep": "triceps",
    "back": "back", "lats": "back", "lat": "back", "upper back": "back",
    "shoulders": "shoulders", "shoulder": "shoulders", "delts": "shoulders",
    "abs": "abdominals", "stomach": "abdominals", "core": "abdominals",
    "tummy": "abdominals", "belly": "abdominals",
    "legs": "quadriceps", "quads": "quadriceps", "thighs": "quadriceps", "thigh": "quadriceps",
    "glutes": "glutes", "buttocks": "glutes", "butt": "glutes", "hips": "glutes",
    "calves": "calves", "calf": "calves",
    "forearms": "forearms", "forearm": "forearms",
    "traps": "traps", "neck": "traps",
    "hamstrings": "hamstrings", "hamstring": "hamstrings",
}

TYPE_MAP = {
    "cardio": "cardio", "aerobic": "cardio",
    "strength": "strength", "weight": "strength", "weight training": "strength",
    "flexibility": "stretching", "stretching": "stretching",
    "plyometric": "plyometrics", "plyometrics": "plyometrics",
    "hiit": "cardio", "interval": "cardio",
    "yoga": "stretching", "pilates": "stretching",
    "calisthenics": "strength", "bodyweight": "strength",
}


def _risk(p: PredictionResult, key: str) -> float:
    """disease_risk_results se risk% (registry disease_key), na mile to flat-column fallback.

    WS-6 extension: rule-based branches bhi ab registry rows se padhte hain (flat columns
    sirf legacy rows ke liye).
    """
    for r in getattr(p, "disease_risk_results", None) or []:
        if r.disease_key == key:
            return float(r.risk_percent or 0)
    flat = {
        "diabetes": getattr(p, "diabetes_risk", None),
        "heart": getattr(p, "heart_risk", None),
        "hypertension": getattr(p, "hypertension_risk", None),
        "obesity": getattr(p, "obesity_risk", None),
    }.get(key)
    return float(flat) if flat is not None else 0.0


def build_risk_badge(p: PredictionResult) -> str:
    """ChatResponse.risk_context — sabse zyada 4 elevated risks (disease_risk_results se)."""
    rows = sorted(
        getattr(p, "disease_risk_results", None) or [],
        key=lambda r: float(r.risk_percent or 0), reverse=True,
    )
    elevated = [r for r in rows if float(r.risk_percent or 0) >= 40]
    if not rows:
        flat = [("Diabetes", _risk(p, "diabetes")), ("Heart", _risk(p, "heart")),
                ("Hypertension", _risk(p, "hypertension")), ("Obesity", _risk(p, "obesity"))]
        parts = [f"{label}: {val:.0f}%" for label, val in flat if val >= 40]
        return "Risk Profile Active - " + ", ".join(parts) if parts else "Risk Profile Active"
    if not elevated:
        return "Risk Profile Active"
    from ml.models.registry import DISEASE_REGISTRY
    parts = []
    for r in elevated[:4]:
        cfg = DISEASE_REGISTRY.get(r.disease_key)
        label = cfg.label if cfg else r.disease_key.replace("_", " ").title()
        parts.append(f"{label}: {float(r.risk_percent or 0):.0f}%")
    return "Risk Profile Active - " + ", ".join(parts)


def build_risk_summary(p: PredictionResult, profile: UserProfile) -> str:
    """Latest prediction ki poori risk summary — WS-6: `disease_risk_results` rows se
    (12-INTEGRATION §5: chat context isi table se aata hai, flat columns nahi).
    Purane rows na ho to flat columns se fallback.
    """
    lines = []
    rows = list(getattr(p, "disease_risk_results", None) or [])
    if rows:
        from ml.models.registry import DISEASE_REGISTRY
        order = {k: i for i, k in enumerate(DISEASE_REGISTRY.keys())}
        rows.sort(key=lambda r: order.get(r.disease_key, 999))
        for r in rows:
            risk = float(r.risk_percent or 0)
            icon = "🟢" if risk < 25 else "🟡" if risk < 50 else "🟠" if risk < 75 else "🔴"
            cfg = DISEASE_REGISTRY.get(r.disease_key)
            label = cfg.label if cfg else r.disease_key.replace("_", " ").title()
            lines.append(f"{icon} {label}: {risk:.0f}% ({r.risk_label})")
    else:
        # fallback (legacy prediction rows)
        if p.diabetes_risk is not None:
            icon = "🟢" if p.diabetes_risk < 25 else "🟡" if p.diabetes_risk < 50 else "🔴"
            lines.append(f"{icon} Diabetes Risk: {p.diabetes_risk}%")
        if p.heart_risk is not None:
            icon = "🟢" if p.heart_risk < 25 else "🟡" if p.heart_risk < 50 else "🔴"
            lines.append(f"{icon} Heart Disease Risk: {p.heart_risk}%")
        if p.hypertension_risk is not None:
            icon = "🟢" if p.hypertension_risk < 25 else "🟡" if p.hypertension_risk < 50 else "🔴"
            lines.append(f"{icon} Hypertension Risk: {p.hypertension_risk}%")
        if p.obesity_risk is not None:
            icon = "🟢" if p.obesity_risk < 25 else "🟡" if p.obesity_risk < 50 else "🔴"
            lines.append(f"{icon} Obesity Risk: {p.obesity_risk}%")
    if p.depression_level:
        lines.append(f"🧠 Depression Level: {p.depression_level}")
    if profile.bmi:
        bmi_cat = "Underweight" if profile.bmi < 18.5 else "Normal" if profile.bmi < 25 else "Overweight" if profile.bmi < 30 else "Obese"
        lines.append(f"📊 BMI: {profile.bmi:.1f} ({bmi_cat})")
    return "\n".join(lines)


def build_health_context(p: PredictionResult, profile: UserProfile) -> str:
    """Groq/Claude system prompt ke liye POORA DB-derived health assessment (12-INTEGRATION §5).

    Prediction + profile se: demographics, bio age, longevity, depression + 16 disease risks.
    Groq isi context ko padh kar diet + daily plan banata hai.
    """
    gender = {0: "Female", 1: "Male"}.get(profile.gender, "—")
    parts = [
        f"Age: {profile.age} | Gender: {gender} | BMI: {profile.bmi:.1f}" if profile.bmi
        else f"Age: {profile.age} | Gender: {gender}",
        f"Sleep: {profile.sleep_hours} h/night | Exercise level: {profile.exercise_level}/4 "
        f"| Smoking: {'Yes' if profile.smoking else 'No'} | Alcohol: {profile.alcohol}/week",
    ]
    if p.biological_age is not None:
        parts.append(f"Biological age: {p.biological_age:.1f} yrs")
    if p.longevity_score is not None:
        parts.append(f"Longevity score: {p.longevity_score:.0f}/100")
    if p.depression_level:
        parts.append(f"Depression screening: {p.depression_level}")
    parts.append("Disease risk assessment (from platform database):")
    parts.append(build_risk_summary(p, profile))
    return "\n".join(x for x in parts if x)


# ─── S15: disease-wise food swap guide ───
# A (specific "yeh khana, par aapko X hai to Y khayein") + B (concise, curated, low-error)
# ka mix: sirf user ke ELEVATED risks (>=40%) ke swaps prompt mein jaate hain, aur LLM inhe
# natural inline advice mein weave karta hai (har food pe forced swap nahi).
FOOD_SWAPS = {
    "diabetes": "white rice/white bread/potato -> brown rice, whole-wheat roti, quinoa, oats; "
                "sugary drinks/juice -> water, unsweetened green tea; ripe banana/mango/grapes -> "
                "apple, guava, berries",
    "heart": "red meat/fried food -> grilled fish (omega-3), skinless chicken, lentils; "
             "butter/ghee -> olive oil; full-fat dairy -> low-fat",
    "hypertension": "salt/pickles/papad/packaged & restaurant food -> herbs, lemon, garlic, "
                    "cumin; canned soup -> fresh low-sodium home food",
    "obesity": "fried snacks/sweets -> roasted chana, nuts, fruit; large portions -> half-plate "
               "vegetables + fist-size carbs",
    "metabolic_syndrome": "refined carbs/trans fat -> whole grains, fiber, lean protein",
    "ckd": "high potassium/phosphorus (banana, tomato, dairy, cola) -> apple, cabbage, white "
           "rice (doctor-guided)",
    "liver": "alcohol/fried/fatty food -> steamed/boiled, olive oil, more vegetables; added "
             "sugar -> whole fruit",
    "anemia": "tea/coffee WITH meals -> iron foods (spinach, lentils, red meat, pumpkin seeds) "
              "plus vitamin C (lemon, orange); tea 1h after meals",
    "thyroid": "excess raw cabbage/soy -> cooked and moderate; use iodised salt",
    "pcos": "refined carbs/sugar -> whole grains, lean protein, healthy fats; add fiber",
    "sleep_apnea": "late heavy meals/alcohol -> light early dinner, no alcohol at night",
    "gad7": "excess caffeine/sugar -> magnesium foods (nuts, greens), omega-3; no caffeine "
            "after noon",
    "colorectal": "processed/red meat -> fish, poultry, beans; more fiber (whole grains, veggies)",
    "lung_cancer_exposure": "smoking/processed food -> antioxidant foods (berries, tomatoes, "
                            "greens), no smoking",
    "burnout": "skipped meals/junk -> regular balanced meals, B-vitamins, hydration",
    "stroke": "high-salt/high-fat/fried -> DASH-style: vegetables, whole grains, fish, low salt",
}


def build_diet_swap_hints(p: PredictionResult) -> str:
    """User ke elevated (>=40%) diseases ke liye food-swap hints (prompt ke liye)."""
    rows = sorted(
        getattr(p, "disease_risk_results", None) or [],
        key=lambda r: float(r.risk_percent or 0), reverse=True,
    )
    lines = []
    for r in rows:
        if float(r.risk_percent or 0) < 40:
            continue
        swap = FOOD_SWAPS.get(r.disease_key)
        if not swap:
            continue
        from ml.models.registry import DISEASE_REGISTRY
        cfg = DISEASE_REGISTRY.get(r.disease_key)
        label = cfg.label if cfg else r.disease_key.replace("_", " ").title()
        lines.append(f"- {label} ({float(r.risk_percent or 0):.0f}%): {swap}")
    return "\n".join(lines)


def generate_response(msg: str, prediction: PredictionResult, profile: UserProfile) -> str:
    text = msg.lower().strip()
    p = prediction
    bmi = profile.bmi if profile.bmi else 0

    # ============ DIET PLAN / MEAL PLAN ============
    # NOTE: ye branch GREETINGS/branch se PEHLE chahiye — warna "diet"/"meal"/"eat"/"menu"
    # wale natural trigger phrases (line 248/193/162) isey shadow kar dete the ("generate my
    # diet plan" -> weight branch). Isliye yahan sabse pehle check hota hai.
    if re.search(r'\b(diet plan|meal plan|daily plan|full day|food plan|poora din|menu plan|planner|what should i eat today|sara din|pura din)\b', text):
        bmi_cat = "underweight" if bmi < 18.5 else "normal" if bmi < 25 else "overweight" if bmi < 30 else "obese"
        cal_range = "1500-1800" if profile.gender == 0 else "1800-2200"
        if bmi_cat in ("overweight", "obese"):
            cal_range = "1400-1700" if profile.gender == 0 else "1600-2000"

        plan = [f"🗓️ **Your Personalized Daily Diet Plan**\n",
                f"📊 Based on: BMI {bmi:.1f} ({bmi_cat}), Age {profile.age}, Gender {'Male' if profile.gender == 1 else 'Female'}",
                f"🎯 Target calories: **{cal_range} kcal/day**\n"]

        plan.append("🌅 **Early Morning (6-7 AM):**")
        plan.append("- 1 glass warm water + lemon")
        if _risk(p, "diabetes") > 40:
            plan.append("- Soaked fenugreek seeds (methi) — helps blood sugar")
        else:
            plan.append("- 5-6 soaked almonds")

        plan.append("\n🍳 **Breakfast (7-8 AM):**")
        if _risk(p, "diabetes") > 40:
            plan.append("- Moong dal chilla with paneer filling")
            plan.append("- 1 cup green tea (unsweetened)")
        elif _risk(p, "heart") > 40:
            plan.append("- Oatmeal with walnuts, chia seeds & berries")
            plan.append("- 1 cup green tea")
        else:
            plan.append("- 2 whole wheat roti + vegetable sabzi OR")
            plan.append("- Overnight oats with nuts & fruits")
            plan.append("- 1 cup milk or green tea")

        plan.append("\n🍎 **Mid-Morning Snack (10-10:30 AM):**")
        plan.append("- 1 fruit (apple/pear/guava)")
        plan.append("- OR handful of mixed nuts (almonds, walnuts)")

        plan.append("\n🍽️ **Lunch (12:30-1 PM):**")
        plan.append("- 2 roti (whole wheat) OR 1 cup brown rice")
        plan.append("- 1 bowl dal (lentils)")
        plan.append("- 1 bowl vegetable sabzi")
        plan.append("- 1 small bowl curd/raita")
        plan.append("- Salad: cucumber, tomato, carrot")
        if _risk(p, "hypertension") > 40:
            plan.append("⚠️ Use minimal salt — flavor with lemon, herbs, spices")

        plan.append("\n🫖 **Evening Snack (4-5 PM):**")
        plan.append("- Green tea / herbal tea")
        plan.append("- 1 small bowl roasted chana OR vegetable soup")

        plan.append("\n🌙 **Dinner (7-8 PM):**")
        plan.append("- 1-2 roti (light, whole wheat)")
        plan.append("- 1 bowl dal or grilled fish/chicken")
        plan.append("- 1 bowl vegetable (steamed/light cooked)")
        if _risk(p, "obesity") > 50:
            plan.append("⚠️ Keep dinner light — avoid rice at night")

        plan.append("\n🌜 **Bedtime (9-10 PM):**")
        plan.append("- 1 glass warm turmeric milk (haldi doodh)")
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            plan.append("- Chamomile tea for better sleep")

        plan.append("\n💧 **Hydration:** 8-10 glasses of water throughout the day")
        plan.append(f"\n🏋️ **Exercise:** 30 min walk after lunch & dinner")
        if _risk(p, "diabetes") > 40:
            plan.append("(Post-meal walks help control blood sugar!)")

        return "\n".join(plan) + "\n\n💡 **Tips:**\n- Eat at consistent times daily\n- Chew food slowly (20+ times)\n- Stop eating 2-3 hours before sleep\n- Control portions — use smaller plates" + DISCLAIMER

    # ============ GREETINGS ============
    if re.search(r'\b(hello|hi|hey|start|help|menu|salam|aoa|assalam)\b', text):
        risk_summary = build_risk_summary(p, profile)
        return (f"👋 Hello! I'm your **AI Diet Advisor**.\n\n"
                f"📋 **Your Health Profile:**\n{risk_summary}\n\n"
                f"I can help you with:\n"
                f"🍽️ Meal plans & recipes\n"
                f"🔍 Nutrition facts for any food\n"
                f"🏋️ Exercises for any muscle\n"
                f"📊 Calorie & macro calculator\n"
                f"⚖️ Weight management\n"
                f"🧠 Mental health nutrition\n\n"
                f"Ask me anything about diet, fitness, or nutrition!" + DISCLAIMER)

    # ============ RISKS ============
    if re.search(r'\b(risk|health|profile|assessment|result|diabetes|heart|hypertension|obesity|check)\b', text):
        return "📊 **Your Health Risk Profile:**\n\n" + build_risk_summary(p, profile) + "\n\nAsk me about specific foods or diets for any of these conditions!" + DISCLAIMER

    # ============ BREAKFAST ============
    if re.search(r'\b(breakfast|morning|subah|nashta)\b', text):
        tips = []
        if _risk(p, "diabetes") > 40:
            tips.append("🩸 **Diabetes-friendly:** Oatmeal with nuts & berries, eggs with avocado, Greek yogurt (unsweetened)")
        if _risk(p, "heart") > 40:
            tips.append("❤️ **Heart-healthy:** Oatmeal with walnuts, whole grain toast with olive oil, smoothie with flaxseed")
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            tips.append("🧠 **Mood-boosting:** Eggs (choline + B12), banana smoothie, oatmeal with dark chocolate chips")
        if not tips:
            tips.append("🥗 **Balanced options:**\n- Overnight oats with chia seeds & berries\n- Whole grain toast with avocado & egg\n- Greek yogurt parfait with granola & nuts\n- Green smoothie (spinach, banana, protein)")
        return ("🍳 **Healthy Breakfast Ideas:**\n\n" + "\n\n".join(tips) + "\n\n💡 **Tips:** Include protein + fiber for sustained energy. Avoid sugary cereals and pastries." + DISCLAIMER)

    # ============ LUNCH / DINNER / MEAL ============
    if re.search(r'\b(lunch|dopehar|dinner|shaam|meal|khana|eat|food|recipe|cook)\b', text):
        tips = []
        if _risk(p, "diabetes") > 40:
            tips.append("🩸 **For blood sugar control:**\n- Grilled chicken with quinoa & roasted veggies\n- Lentil soup with whole grain bread\n- Stir-fry with tofu, broccoli, brown rice")
        if _risk(p, "heart") > 40:
            tips.append("❤️ **Heart-healthy meals:**\n- Baked salmon with sweet potato & spinach\n- Mediterranean salad (olive oil, feta, olives)\n- Bean tacos with fresh salsa & avocado")
        if _risk(p, "hypertension") > 40:
            tips.append("🩺 **DASH diet:**\n- Low-sodium chicken with steamed veggies\n- Grilled fish with brown rice\n- Bean & vegetable stew")
        if not tips:
            tips.append("🥗 **Balanced meals:**\n- Grilled protein + whole grain + vegetables\n- Use herbs & spices instead of salt\n- Olive oil for cooking\n- Aim for colorful plates!")
        return ("🍽️ **Healthy Meal Ideas:**\n\n" + "\n\n".join(tips) + "\n\n📏 **Plate model:** ½ vegetables, ¼ lean protein, ¼ whole grains" + DISCLAIMER)

    # ============ SNACKS ============
    if re.search(r'\b(snack|hungry|craving|choti|light|bhook)\b', text):
        options = ["🥜 Mixed nuts (almonds, walnuts) — brain & heart healthy",
                   "🍎 Apple slices with almond butter",
                   "🥕 Carrot sticks with hummus",
                   "🫐 Berries with Greek yogurt",
                   "🥚 Boiled eggs — protein + choline",
                   "🥑 Half avocado with salt & lemon"]
        if _risk(p, "diabetes") > 40:
            options.append("🩸 Avoid: candy, cookies, juice. Choose: nuts, cheese, vegetables")
        if _risk(p, "heart") > 40:
            options.append("❤️ Avoid: fried snacks, chips. Choose: nuts, fruits, veggies")
        return ("🥜 **Healthy Snack Options:**\n\n" + "\n".join(f"- {o}" for o in options) + "\n\n⏰ Eat every 3-4 hours to maintain energy!" + DISCLAIMER)

    # ============ DRINKS / HYDRATION ============
    if re.search(r'\b(water|drink|hydration|chai|coffee|tea|pani|juice|soda)\b', text):
        tips = ["💧 **Hydration Guide:**",
                "- Aim for 8-10 glasses of water daily",
                "- Green tea: rich in antioxidants (2-3 cups/day)",
                "- Limit sugary drinks and sodas",
                "- Herbal teas (chamomile, peppermint) are great",
                "- Coffee: 1-3 cups/day is fine, avoid excess sugar"]
        if _risk(p, "diabetes") > 40:
            tips.append("🩸 **Avoid:** fruit juices, sodas, sweetened coffee. Choose: water, unsweetened tea")
        if _risk(p, "hypertension") > 40:
            tips.append("🩺 **Limit:** caffeine to 1-2 cups. Choose: hibiscus tea, water with lemon")
        return "\n".join(tips) + DISCLAIMER

    # ============ EXERCISE / FITNESS ============
    if re.search(r'\b(exercise|workout|gym|fitness|walk|run|yoga|activity)\b', text):
        tips = ["🏋️ **Exercise Recommendations:**",
                "- 150 min/week moderate activity (walking, cycling)",
                "- 2x/week strength training",
                "- 30 min daily walk after meals (helps blood sugar)",
                "- Yoga for stress relief & flexibility",
                "- Start slow and gradually increase"]
        if _risk(p, "diabetes") > 40:
            tips.append("🩸 Walking 30 min after meals can reduce blood sugar spikes by 30%!")
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            tips.append("🧠 Exercise releases endorphins — even a 15-min walk can improve mood!")
        return "\n".join(tips) + DISCLAIMER

    # ============ WEIGHT / DIET ============
    if re.search(r'\b(weight|diet|lose|calorie|fat|pet|motapa|wazan|kam)\b', text):
        tips = ["⚖️ **Healthy Weight Management:**",
                "- Focus on whole, unprocessed foods",
                "- Control portions (smaller plates help)",
                "- Protein with every meal (keeps you full)",
                "- Half plate vegetables always",
                "- No crash diets — sustainable changes only",
                "- Track what you eat for awareness"]
        if _risk(p, "obesity") > 50:
            tips.append("\n⚠️ Your obesity risk is elevated. Focus on:")
            tips.append("- Reducing portion sizes gradually")
            tips.append("- More vegetables, less refined carbs")
            tips.append("- Daily walking (30+ minutes)")
        tips.append("\n🎯 **Goal:** 0.5-1 kg/week is safe and sustainable!")
        return "\n".join(tips) + DISCLAIMER

    # ============ MENTAL HEALTH ============
    if re.search(r'\b(sad|depressed|anxious|stress|mood|tired|sleep|mental|energy|thakan|tension|pareshan)\b', text):
        tips = ["🧠 **Nutrition for Mental Health:**", "",
                "**Omega-3 fatty fish** (salmon, sardines) — 2x/week",
                "**Dark chocolate** (70%+ cocoa) — 1-2 squares/day",
                "**Leafy greens** (spinach, kale) — folate supports mood",
                "**Nuts & seeds** (walnuts, pumpkin seeds) — magnesium",
                "**Bananas** — tryptophan + B6 for serotonin",
                "**Eggs** — choline + B12 for brain function",
                "**Berries** — antioxidants reduce inflammation", "",
                "**Lifestyle tips:**",
                "- 7-9 hours sleep consistently",
                "- Daily sunlight (15-20 min)",
                "- Regular exercise (even walking)",
                "- Stay socially connected",
                "- Limit alcohol"]
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            tips.insert(1, f"⚠️ Your screening shows **{p.depression_level}** depression level.")
            tips.append("\n💚 **Please consider reaching out to a mental health professional.** You are not alone.")
            tips.append("📞 **Crisis helpline:** Call or text 988 (US) | Befrienders: +44 116 123 4567")
        return "\n".join(tips) + DISCLAIMER

    # ============ SPECIFIC FOODS ============
    if re.search(r'\b(chicken|paneer|egg|anday|meat|fish|mutton|beef)\b', text):
        if _risk(p, "heart") > 45:
            return ("🥩 **Protein sources for heart health:**\n\n"
                    "✅ **Best choices:**\n- Grilled/baked fish (salmon, mackerel) — omega-3\n- Chicken breast (skinless) — lean protein\n- Eggs (1-2/day) — protein + choline\n- Lentils & beans — plant protein + fiber\n\n"
                    "⚠️ **Limit:**\n- Red meat (beef, mutton) — 1x/week max\n- Fried meats\n- Processed meats (sausage, bacon)\n\n"
                    "🍳 **Cooking tips:** Bake, grill, or steam instead of frying. Use olive oil." + DISCLAIMER)
        return ("🥩 **Protein Guide:**\n\n"
                "- Chicken breast: lean protein, grill or bake\n- Fish: omega-3, 2x/week recommended\n- Eggs: complete protein, 1-2/day\n- Paneer/tofu: good for vegetarians\n- Lentils/beans: plant protein + fiber\n\n"
                "📏 **Portion:** Size of your palm per meal" + DISCLAIMER)

    if re.search(r'\b(rice|chawal|biryani|pulao)\b', text):
        if _risk(p, "diabetes") > 40:
            return ("🍚 **Rice advice for blood sugar:**\n\n"
                    "⚠️ White rice spikes blood sugar quickly.\n\n"
                    "✅ **Better alternatives:**\n- Brown rice (lower GI)\n- Quinoa (protein + fiber)\n- Cauliflower rice (very low carb)\n- Bulgur wheat\n\n"
                    "💡 **If eating white rice:**\n- Smaller portion (fist-sized)\n- Pair with protein and vegetables\n- Don't eat alone — combine with dal/curry" + DISCLAIMER)
        return ("🍚 **Rice Guide:**\n\n"
                "- Brown rice: more fiber, minerals\n- Quinoa: complete protein\n- Portion: fist-sized serving\n- Always pair with vegetables and protein\n\n"
                "💡 Mix white and brown rice if transitioning!" + DISCLAIMER)

    if re.search(r'\b(bread|roti|naan|chapati)\b', text):
        return ("🍞 **Bread/Roti Guide:**\n\n"
                "✅ **Best choices:**\n- Whole wheat roti/chapati\n- Multigrain bread\n- Oats-based bread\n\n"
                "⚠️ **Limit:**\n- White bread (refined flour)\n- Naan (high calorie, refined)\n- Maida-based products\n\n"
                "📏 **Portion:** 1-2 rotis per meal, pair with sabzi/dal" + DISCLAIMER)

    if re.search(r'\b(milk|doodh|dahi|yogurt|cheese|paneer)\b', text):
        return ("🥛 **Dairy Guide:**\n\n"
                "✅ **Best choices:**\n- Greek yogurt (high protein, probiotics)\n- Low-fat milk\n- Cottage cheese/paneer\n- Buttermilk (chaas) — great for digestion\n\n"
                "⚠️ **Limit:**\n- Full-fat cheese (high saturated fat)\n- Flavored yogurts (high sugar)\n- Cream\n\n"
                "📏 **Portion:** 1 glass milk or 1 cup yogurt daily" + DISCLAIMER)

    if re.search(r'\b(fruit|phal|apple|banana|orange|mango)\b', text):
        tips = ["🍎 **Fruit Guide:**\n"]
        if _risk(p, "diabetes") > 40:
            tips.append("🩸 **Choose low-GI fruits:**")
            tips.append("- Berries (strawberry, blueberry) — best for blood sugar\n- Apple with skin\n- Pear\n- Orange\n- Kiwi")
            tips.append("\n⚠️ **Limit high-sugar fruits:** Mango, grapes, banana (half only), dried fruits")
            tips.append("\n📏 **Portion:** 1-2 servings/day, eat whole not juice")
        else:
            tips.append("✅ **Great choices:**\n- Berries (antioxidants)\n- Apples (fiber)\n- Bananas (potassium)\n- Oranges (vitamin C)\n- Kiwi (vitamin C + fiber)")
            tips.append("\n📏 **Portion:** 2-3 servings/day, eat whole not juice")
        return "\n".join(tips) + DISCLAIMER

    # ============ SUGAR / SWEETS ============
    if re.search(r'\b(sugar|sweet|meetha|cake|cookie|chocolate|candy|mithai)\b', text):
        if _risk(p, "diabetes") > 40:
            return ("🍬 **Sugar & Diabetes:**\n\n"
                    "⚠️ Your diabetes risk is elevated — sugar management is critical!\n\n"
                    "❌ **Avoid:**\n- Candy, cookies, cakes\n- Sugary drinks (soda, juice)\n- White sugar in tea/coffee\n- Mithai (traditional sweets)\n- Ice cream\n\n"
                    "✅ **Healthy alternatives:**\n- Dark chocolate (70%+) — 1 small piece\n- Berries with a drizzle of honey\n- Cinnamon (helps blood sugar)\n- Dates (1-2 max)\n- Stevia or monk fruit sweetener\n\n"
                    "💡 Read labels — sugar hides in bread, sauce, yogurt!" + DISCLAIMER)
        return ("🍬 **Sugar Guide:**\n\n"
                "- Limit added sugar to 25g/day (women) or 36g/day (men)\n"
                "- Dark chocolate (70%+) is better than milk chocolate\n"
                "- Check labels — sugar hides in unexpected foods\n"
                "- Use fruits to satisfy sweet cravings\n"
                "- Cinnamon adds sweetness without sugar" + DISCLAIMER)

    # ============ SALT / SODIUM ============
    if re.search(r'\b(salt|sodium|noon|namak)\b', text):
        if _risk(p, "hypertension") > 40:
            return ("🧂 **Salt & Blood Pressure:**\n\n"
                    "⚠️ Your hypertension risk is elevated — reduce sodium!\n\n"
                    "❌ **High-sodium foods to avoid:**\n- Pickles, papad, chips\n- Canned soups\n- Processed/packaged foods\n- Soy sauce, ketchup\n- Restaurant/takeout food\n\n"
                    "✅ **Flavor without salt:**\n- Lemon juice\n- Garlic, ginger, turmeric\n- Herbs (basil, oregano, cilantro)\n- Black pepper, cumin, coriander\n- Vinegar\n\n"
                    "📏 **Limit:** Less than 2,300mg sodium/day (1 tsp salt)" + DISCLAIMER)
        return ("🧂 **Salt Guide:**\n\n"
                "- Aim for less than 1 tsp (6g) salt per day\n"
                "- Use herbs, spices, lemon for flavor\n"
                "- Limit processed and packaged foods\n"
                "- Taste before adding salt to food" + DISCLAIMER)

    # ============ SPECIFIC DIETS ============
    if re.search(r'\b(mediterranean|dash|keto|vegan|vegetarian|intermittent)\b', text):
        return ("🥗 **Popular Diet Overview:**\n\n"
                "**Mediterranean:** Olive oil, fish, nuts, vegetables, whole grains. Great for heart health! ✅\n\n"
                "**DASH:** Low sodium, high potassium (fruits, vegetables, whole grains). Best for blood pressure! ✅\n\n"
                "**Plant-based:** Rich in fiber, antioxidants. Good for overall health. ✅\n\n"
                "⚠️ **Keto:** Very low carb — not recommended with diabetes risk without medical supervision.\n\n"
                "💡 **My recommendation:** Mediterranean or DASH approach — balanced, sustainable, and evidence-based!" + DISCLAIMER)

    # ============ TEA / COFFEE ============
    if re.search(r'\b(tea|coffee|chai|green tea|kaawa)\b', text):
        tips = ["☕ **Tea & Coffee Guide:**\n",
                "✅ **Green tea:** 2-3 cups/day — rich in antioxidants, boosts metabolism",
                "✅ **Black coffee:** 1-2 cups/day — antioxidants, avoid excess sugar",
                "✅ **Herbal tea:** Chamomile (sleep), peppermint (digestion), ginger (nausea)",
                "✅ **Hibiscus tea:** May help lower blood pressure\n",
                "⚠️ **Limit:** Excess caffeine (>4 cups), sugar in tea/coffee, cream\n",
                "💡 **Best time:** Morning and early afternoon. Avoid after 4 PM for better sleep."]
        return "".join(tips) + DISCLAIMER

    # ============ VEGGIES ============
    if re.search(r'\b(vegetable|sabzi|salad|green|leafy)\b', text):
        tips = ["🥦 **Vegetable Guide:**\n",
                "✅ **Super vegetables:**\n- Spinach (iron, folate)\n- Broccoli (fiber, vitamins)\n- Kale (antioxidants)\n- Carrots (vitamin A)\n- Tomatoes (lycopene)\n- Bell peppers (vitamin C)\n- Sweet potato (fiber, beta-carotene)\n",
                "📏 **Goal:** 3-5 servings/day\n",
                "💡 **Tips:**\n- Half your plate should be vegetables\n- Eat a variety of colors\n- Raw or lightly cooked preserves nutrients\n- Add to every meal"]
        return "".join(tips) + DISCLAIMER

    # ============ GENERAL FOOD ============
    if re.search(r'\b(good food|best food|healthy|superfood|what to eat)\b', text):
        return ("🌟 **Top Superfoods for Your Health:**\n\n"
                "1. 🐟 **Fatty fish** — omega-3, heart & brain\n"
                "2. 🫐 **Berries** — antioxidants, blood sugar\n"
                "3. 🥬 **Leafy greens** — vitamins, minerals\n"
                "4. 🥜 **Nuts** — healthy fats, protein\n"
                "5. 🫘 **Beans/lentils** — fiber, plant protein\n"
                "6. 🫒 **Olive oil** — heart-healthy fat\n"
                "7. 🥑 **Avocado** — healthy fats, potassium\n"
                "8. 🌾 **Whole grains** — fiber, sustained energy\n"
                "9. 🥚 **Eggs** — complete protein, choline\n"
                "10. 🧄 **Garlic** — immune support, blood pressure\n\n"
                "Eat a rainbow of colors every day!" + DISCLAIMER)

    # ============ ALCOHOL ============
    if re.search(r'\b(alcohol|wine|beer|sharab|drink|whisky)\b', text):
        tips = ["🍷 **Alcohol & Health:**\n"]
        if _risk(p, "heart") > 45:
            tips.append("⚠️ Your heart risk is elevated — limit alcohol strictly.")
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            tips.append("⚠️ Alcohol worsens depression symptoms — avoid or minimize.")
        tips.extend([
            "**If you drink:**\n- Max 1 drink/day (women) or 2 drinks/day (men)",
            "- Red wine: resveratrol (1 small glass OK)\n- Avoid binge drinking",
            "**Healthier alternatives:**\n- Sparkling water with lemon\n- Herbal mocktails\n- Kombucha\n\n",
            "💡 Alcohol disrupts sleep, adds empty calories, and affects mood." + DISCLAIMER
        ])
        return "\n".join(tips)

    # ============ THANKS ============
    if re.search(r'\b(thank|shukriya|thanks|thnx)\b', text):
        return ("You're welcome! 😊\n\nRemember: small consistent changes lead to big results.\n"
                "Feel free to ask me anything about diet, nutrition, or your health risks!\n\n"
                "Stay healthy! 💪" + DISCLAIMER)

    # ============ BYE ============
    if re.search(r'\b(bye|alvida|goodbye|chalta hun)\b', text):
        return ("Goodbye! 👋\n\nRemember:\n"
                "- Eat a balanced diet with colorful vegetables\n"
                "- Stay hydrated (8+ glasses water)\n"
                "- Exercise regularly (30 min/day)\n"
                "- Prioritize sleep (7-9 hours)\n\n"
                "Take care of your health! See you next time. 💪" + DISCLAIMER)

    # ============ DEFAULT ============
    risk_context = ""
    if _risk(p, "diabetes") > 40:
        risk_context += "🩸 Your diabetes risk is elevated — focus on low-sugar, high-fiber foods.\n"
    if _risk(p, "heart") > 40:
        risk_context += "❤️ Your heart risk is elevated — choose omega-3 fish, olive oil, nuts.\n"
    if _risk(p, "hypertension") > 40:
        risk_context += "🩺 Your hypertension risk is elevated — reduce salt, eat potassium-rich foods.\n"
    if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
        risk_context += "🧠 Your depression level is elevated — omega-3, magnesium, B-vitamins help.\n"

    return (f"I can help with that! Here's some guidance:\n\n"
            f"🥗 **Healthy Eating Basics:**\n"
            f"- Half your plate: vegetables & fruits\n"
            f"- Quarter: lean protein (fish, chicken, beans)\n"
            f"- Quarter: whole grains (brown rice, roti)\n"
            f"- Add healthy fats (olive oil, nuts, avocado)\n\n"
            f"{risk_context}\n"
            f"💡 **Try asking:**\n"
            f"- 🔍 \"Calories in chicken breast\" — real nutrition data\n"
            f"- 🏋️ \"Exercise for chest\" — real exercises with instructions\n"
            f"- 📊 \"Calculate my macros\" — personalized calorie & protein targets\n"
            f"- ⚖️ \"Compare chicken vs rice\" — side-by-side nutrition\n"
            f"- 🗓️ \"Generate my diet plan\" — full day meal plan\n"
            f"- 💧 \"How much water should I drink\" — personalized hydration\n\n"
            f"What would you like to know?" + DISCLAIMER)


# ══════════════════════════════════════════════════════════════
#  Enhanced API-powered queries (nutrition, exercises, macros)
# ══════════════════════════════════════════════════════════════

async def _check_api_queries(text: str, prediction: PredictionResult, profile: UserProfile) -> str:
    """
    Broad pattern matching for API-powered queries:
    nutrition lookup, exercise search, fitness plans,
    macro calculator, food comparison, BMI, hydration.
    """
    clean = text.lower().strip()

    # ══════════════ 1. NUTRITION / CALORIE LOOKUP ══════════════
    nutri_match = re.search(
        r'(?:calories?|calorie|nutrition|nutrients?|kcal|macros?|protein|carbohydrates?|carbs?|'
        r'fats?|fiber|sugar|sodium)\s+(?:in|of|for)\s+(.+)',
        clean,
    )
    if not nutri_match:
        nutri_match = re.search(
            r'(?:how\s+(?:many|much)\s+)?(?:calories?|calorie|kcal)\s+(?:is\s+(?:there\s+)?(?:in\s+)?)?([\w\s]+)',
            clean,
        )
    if not nutri_match:
        nutri_match = re.search(
            r'(?:what\s+(?:are\s+)?(?:the\s+)?(?:calories?|macros?|nutrients?|nutrition|protein|carbs?))'
            r'\s+(?:in|of|for)\s+(.+)',
            clean,
        )
    if nutri_match:
        food = re.sub(r'[?!.,;:]+$', '', nutri_match.group(1)).strip()
        if food and len(food) > 1:
            data = await search_nutrition(food)
            if data:
                formatted = format_nutrition(data, food)
                if formatted:
                    return formatted
            # API data usable nahi (free-tier "premium" placeholder) → focused LLM jawab
            llm = _llm_chat(
                _nutrition_system_prompt(prediction),
                [{"role": "user", "content": text}],
                max_tokens=500,
            )
            if llm:
                return llm

    # ══════════════ 2. FOOD COMPARISON ══════════════
    comp_match = re.search(
        r'(?:compare|vs\.?|versus)\s+(\w[\w\s]*?)\s+(?:vs\.?|versus|and|or|with)\s+(\w[\w\s]*?)(?:\s*(?:which|better|healthier|comparison))?[?]?$',
        clean,
    )
    if not comp_match:
        comp_match = re.search(
            r'(\w[\w\s]*?)\s+(?:vs\.?|versus|or)\s+(\w[\w\s]*?)(?:\s*(?:which|better|healthier))?[?]?$',
            clean,
        )
    if comp_match:
        food1 = re.sub(r'[?!.,;:]+$', '', comp_match.group(1)).strip()
        food2 = re.sub(r'[?!.,;:]+$', '', comp_match.group(2)).strip()
        if food1 and food2 and len(food1) > 1 and len(food2) > 1:
            data1 = await search_nutrition(food1)
            data2 = await search_nutrition(food2)
            if data1 and data2:
                formatted = format_nutrition_comparison([data1, data2], [food1, food2])
                if formatted:
                    return formatted
            # API data usable nahi → focused LLM comparison
            llm = _llm_chat(
                _nutrition_system_prompt(prediction),
                [{"role": "user", "content": text}],
                max_tokens=500,
            )
            if llm:
                return llm

    # ══════════════ 3. EXERCISE / WORKOUT LOOKUP ══════════════
    ex_match = re.search(
        r'(?:exercises?|workouts?|training|exercise|workout)\s+(?:for|targeting|to\s+(?:build|work|train|strengthen))\s+(.+)',
        clean,
    )
    if not ex_match:
        ex_match = re.search(
            r'(?:show|give|suggest|list|find|what\s+(?:are|is))\s+(?:me\s+)?(?:some\s+)?(?:exercises?|workouts?)\s+(?:for|targeting|to\s+(?:build|work|train))\s+(.+)',
            clean,
        )
    if not ex_match:
        ex_match = re.search(
            r'(?:best|good|top)\s+(?:exercises?|workouts?)\s+(?:for|to\s+(?:build|work|train))\s+(.+)',
            clean,
        )
    if ex_match:
        muscle_raw = re.sub(r'[?!.,;:]+$', '', ex_match.group(1)).strip()
        muscle = MUSCLE_MAP.get(muscle_raw, muscle_raw)
        if muscle is None:  # full body
            data = await search_exercises()
            if data:
                return format_exercises(random.sample(data, min(5, len(data))), "full body")
        elif muscle:
            data = await search_exercises(muscle=muscle)
            if data:
                return format_exercises(data, muscle_raw)
            data = await search_exercises(muscle=muscle_raw)
            if data:
                return format_exercises(data, muscle_raw)

    # ══════════════ 4. EXERCISE TYPE QUERY ══════════════
    type_match = re.search(
        r'(cardio|strength|flexibility|stretching|plyometric(?:s)?|hiit|yoga|pilates|calisthenics|bodyweight)\s*(exercises?|workouts?|training)?',
        clean,
    )
    if type_match:
        ex_type = type_match.group(1)
        api_type = TYPE_MAP.get(ex_type, ex_type)
        data = await search_exercises(exercise_type=api_type)
        if data:
            return format_exercises(data, ex_type)

    # ══════════════ 5. FITNESS PLAN ══════════════
    if re.search(r'(?:create|make|generate|build|give|suggest)\s+(?:me\s+)?(?:a\s+)?(?:workout|fitness|exercise|training|gym)\s*(?:plan|routine|program|schedule)', clean):
        goal = "maintain"
        if re.search(r'(?:lose|loss|fat|cut|lean|slim|weight)', clean):
            goal = "lose"
        elif re.search(r'(?:gain|muscle|bulk|mass|strength|build)', clean):
            goal = "gain"
        exercises = await search_exercises()
        if exercises:
            return format_fitness_plan(exercises, goal, days=3)

    # ══════════════ 6. MACRO CALCULATOR ══════════════
    if re.search(r'(?:calculate|compute|what\s+(?:are|is)|my|tell\s+me)\s+(?:my\s+)?(?:macro|calorie|calories?|tdee|bmr|daily\s+(?:calories?|intake))', clean):
        goal = "maintain"
        if re.search(r'(?:lose|loss|fat|cut|lean|weight|deficit)', clean):
            goal = "lose"
        elif re.search(r'(?:gain|muscle|bulk|mass|build|surplus)', clean):
            goal = "gain"
        macros = calculate_macros(
            weight_kg=profile.weight or 70,
            height_cm=profile.height or 170,
            age=profile.age or 30,
            gender=profile.gender or 1,
            exercise_level=profile.exercise_level or 1,
            goal=goal,
        )
        profile_info = {
            "weight": profile.weight,
            "height": profile.height,
            "age": profile.age,
            "exercise_level": profile.exercise_level,
        }
        return format_macro_response(macros, profile_info)

    # ══════════════ 7. PROTEIN / SPECIFIC MACRO FOODS ══════════════
    macro_food_match = re.search(
        r'\b(?:high|rich|good|best)\s+(?:in\s+)?(protein|carbs?|fat|fiber|iron|calcium|vitamin|omega|potassium|zinc|magnesium)\b',
        clean,
    )
    if macro_food_match:
        nutrient = macro_food_match.group(1)
        query_map = {
            "protein": "chicken breast, eggs, Greek yogurt, lentils",
            "carbs": "oats, brown rice, sweet potato, quinoa",
            "carb": "oats, brown rice, sweet potato, quinoa",
            "fat": "avocado, olive oil, almonds, salmon",
            "fiber": "broccoli, lentils, chia seeds, oats",
            "iron": "spinach, red meat, lentils, pumpkin seeds",
            "calcium": "milk, yogurt, cheese, broccoli",
            "vitamin": "orange, spinach, carrot, bell pepper",
            "omega": "salmon, walnuts, flaxseed, sardines",
            "potassium": "banana, sweet potato, spinach, avocado",
            "zinc": "pumpkin seeds, chickpeas, cashews, lentils",
            "magnesium": "almonds, spinach, dark chocolate, avocado",
        }
        query = query_map.get(nutrient, nutrient)
        data = await search_nutrition(query)
        if data:
            result = f"🥗 **Top {nutrient.title()}-Rich Foods:**\n\n"
            for item in data[:5]:
                name = item.get("name", "")
                cal = item.get("calories", 0)
                pro = item.get("protein_g", 0)
                carb = item.get("carbohydrates_total_g", 0)
                fat = item.get("fat_total_g", 0)
                result += f"- **{name}**: {cal} kcal | P: {pro}g | C: {carb}g | F: {fat}g\n"
            result += f"\n💡 **Tip:** Include these in your daily meals for balanced nutrition!"
            return result + DISCLAIMER

    # ══════════════ 8. BMI Calculator ══════════════
    if re.search(r'\b(bmi|body mass index)\b', clean):
        bmi_val = profile.bmi if profile.bmi else 0
        if bmi_val > 0:
            bmi_cat = "Underweight" if bmi_val < 18.5 else "Normal" if bmi_val < 25 else "Overweight" if bmi_val < 30 else "Obese"
            emoji = "🟢" if bmi_val < 25 else "🟡" if bmi_val < 30 else "🔴"
            result = (f"📊 **Your BMI:**\n\n"
                      f"{emoji} **BMI: {bmi_val:.1f}** ({bmi_cat})\n\n"
                      f"📏 **Height:** {profile.height} cm | ⚖️ **Weight:** {profile.weight} kg\n\n")
            if bmi_val >= 25:
                result += "💡 **Healthy BMI range:** 18.5 - 24.9\nAim for gradual weight loss (0.5-1 kg/week) through balanced diet and exercise.\n"
            elif bmi_val < 18.5:
                result += "💡 **Healthy BMI range:** 18.5 - 24.9\nFocus on nutrient-dense foods to gain healthy weight.\n"
            else:
                result += "✅ You're in a healthy BMI range. Keep it up!\n"
            return result + DISCLAIMER

    # ══════════════ 9. WATER / HYDRATION ══════════════
    if re.search(r'\b(how much water|water intake|water should i drink|hydration goal|pani kitna|drink water)\b', clean):
        weight = profile.weight if profile.weight else 70
        exercise = profile.exercise_level if profile.exercise_level else 1
        base_water = weight * 0.033
        exercise_add = 0.3 if exercise >= 2 else 0.1 if exercise >= 1 else 0
        total = base_water + exercise_add
        glasses = int(total * 1000 / 250)
        result = (f"💧 **Your Daily Water Target:**\n\n"
                  f"🎯 **{total:.1f} liters** (~{glasses} glasses)\n\n"
                  f"📏 **Based on:** Weight: {weight} kg | Exercise level: {exercise}/4\n\n"
                  f"⏰ **Schedule:**\n"
                  f"- 🌅 2 glasses on waking\n"
                  f"- 🍽️ 1 glass before each meal\n"
                  f"- 🏋️ 1-2 glasses during exercise\n"
                  f"- 🌙 1 glass before bed\n\n")
        if _risk(prediction, "diabetes") > 40:
            result += "🩸 **Tip:** Drinking water before meals helps control blood sugar!\n"
        if _risk(prediction, "hypertension") > 40:
            result += "🩺 **Tip:** Adequate water helps regulate blood pressure.\n"
        return result + DISCLAIMER

    # ══════════════ 10. SPECIFIC EXERCISE NAME ══════════════
    ex_name_match = re.search(
        r'(?:how\s+to\s+do|tell\s+me\s+about|what\s+is|explain)\s+(.+)',
        clean,
    )
    if ex_name_match:
        ex_name = re.sub(r'[?!.,;:]+$', '', ex_name_match.group(1)).strip()
        data = await search_exercises(name=ex_name)
        if data:
            return format_exercises(data, ex_name)

    return ""


# ══════════════════════════════════════════════════════════════
#  LLM integration — Groq preferred, Claude fallback, "" on no key
# ══════════════════════════════════════════════════════════════

def _env_key(name: str) -> str:
    """os.getenv se API key — empty ya 'your-...' placeholder ho to "" (missing)."""
    val = (os.getenv(name, "") or "").strip()
    if not val or val.startswith("your-") or val in ("your-api-key-here",):
        return ""
    return val


# Agar OpenAI key out-of-credits/invalid nikli to is process mein dobara try na karein
# (warna har message pe ek fail call se latency badhti hai). Env se override ho sakta hai.
_OPENAI_DISABLED = False


def _llm_openai(system_prompt: str, history: list, max_tokens: int) -> str:
    """OpenAI chat completion. Key missing / no credits / invalid nikle to is process
    mein OpenAI ko disable kar dete hain aur Groq pe chale jaate hain."""
    global _OPENAI_DISABLED
    if _OPENAI_DISABLED:
        return ""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN-AI") or ""
    if not key:
        _OPENAI_DISABLED = True
        return ""
    import httpx
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}] + (history or [])[-10:],
    }
    # naye models (gpt-5* / o-series) max_completion_tokens maangte hain
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
    try:
        with httpx.Client(timeout=40.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=body,
            )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            return content if content and content.strip() else ""
        if resp.status_code in (401, 402, 403, 429):
            # no credits / invalid key → process ke liye disable
            _OPENAI_DISABLED = True
    except Exception:
        pass
    return ""


def _llm_chat(system_prompt: str, history: list, max_tokens: int = 600) -> str:
    """Shared LLM call: OpenAI (if credits) → Groq (free) → Anthropic Claude → "".

    NOTE: Groq ka gpt-oss ek REASONING model hai — hidden reasoning tokens bhi
    `max_tokens` mein count hote hain, is liye chhota budget do to `content` khaali
    aa jaata hai (finish_reason="length"). `reasoning_effort="low"` + thoda bada
    budget rakhte hain.
    """
    # 1) OpenAI
    out = _llm_openai(system_prompt, history, max_tokens)
    if out:
        return out

    # 2) Groq (free)
    import httpx
    groq_key = _env_key("GROQ_API_KEY")
    if groq_key:
        try:
            groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            groq_body = {
                "model": groq_model,
                "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system_prompt}] + (history or [])[-10:],
            }
            if "gpt-oss" in groq_model:
                groq_body["reasoning_effort"] = "low"
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json=groq_body,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                if content and content.strip():
                    return content
        except Exception:
            pass  # Groq fail → Claude try

    # 3) Anthropic Claude
    claude_key = _env_key("ANTHROPIC_API_KEY")
    if claude_key:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": claude_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": (history or [])[-10:],
                    },
                )
                resp.raise_for_status()
                return resp.json()["content"][0]["text"]
        except Exception:
            pass
    return ""


def _nutrition_system_prompt(prediction: PredictionResult) -> str:
    """Factual nutrition lookup ke liye FOCUSED prompt — seedha numbers, koi gyaan nahi.

    Bada risk-advice prompt model ko generic diet advice dene pe laga deta tha, is liye
    "calories in chicken breast" jaise sawaal ka asli jawab (kcal/protein) miss ho jaata tha.
    """
    top_risks = build_risk_badge(prediction)
    return (
        "You are a concise nutrition assistant for a health platform.\n"
        "Answer the user's nutrition question with ACCURATE standard values (per 100g, and per a "
        "common serving if useful).\n"
        "Rules:\n"
        "- Your FIRST line MUST contain the calorie number (kcal). Never omit it.\n"
        "- Include the key macros (protein / carbs / fat).\n"
        "- 2-4 short lines MAX. Do NOT give a generic diet lecture or list unrelated swaps.\n"
        "- If clearly relevant, add ONE short tip using the user's top risks (below).\n"
        "- End with a one-line medical disclaimer.\n"
        f"- User's top risks (only for the optional tip): {top_risks or 'none'}\n"
    )


# Plan request detection — English + Roman Urdu variants. Pehle sirf 4-5 English phrases
# match hote the, is liye "diet chart do" / "aaj kya khaun" jaise sawaal plan nahi banate the.
_PLAN_REQUEST_RE = re.compile(
    r"(diet\s*plan|meal\s*plan|daily\s*plan|full[\s-]*day|food\s*plan|diet\s*chart|meal\s*chart|"
    r"diet\s*schedule|week\s*plan|weekly\s*plan|menu\s*plan|planner|"
    r"what\s+should\s+i\s+eat|aaj\s+kya\s+kha|kya\s+khaun|kya\s+khaon|khana\s+batao|diet\s+bata|"
    r"poora\s+din|pura\s+din|sara\s+din|din\s+bhar)",
    re.IGNORECASE,
)


def _plan_system_prompt(health_context: str, swap_hints: str) -> str:
    """Exact, clean one-day diet plan — food + portion per line, koi swap-explanation nahi.

    Pehle plan line mein "— white rice → but your diabetes risk is high..." ghusa deta tha,
    jis se plan 200+ words ka messy paragraph ban jaata tha (user: "exact diet plan nahi de raha").
    Yahan swap SILENTLY apply hote hain — sirf final best option likhna hai.
    """
    return (
        "You are the AI Diet & Longevity Advisor of this platform.\n"
        "=== USER HEALTH ASSESSMENT ===\n"
        f"{health_context}\n"
        "=== END ASSESSMENT ===\n\n"
        + ("=== ALLOWED SWAPS (apply these SILENTLY — do NOT write them out) ===\n"
           f"{swap_hints}\n=== END ===\n\n" if swap_hints else "")
        + "The user asked for a DIET PLAN. Give a clean, EXACT one-day plan:\n"
        "- Output EXACTLY these labelled lines, in this order: 'Breakfast:', 'Mid-morning:', "
        "'Lunch:', 'Evening snack:', 'Dinner:', 'Hydration:', 'Lifestyle:'.\n"
        "- Each food line = the food + a portion, e.g. '1 bowl oats with 1 apple', "
        "'100g grilled chicken + 1 cup salad', '2 rotis'.\n"
        "- Pick the better option for the user's risks (apply the swaps silently). Do NOT write "
        "'but your X risk is high', arrows, or any explanation.\n"
        "- Total under ~120 words. No preamble, no repetition.\n"
        "- End with one short disclaimer line."
    )


def _llm_response(message: str, prediction: PredictionResult, profile: UserProfile, history: list) -> str:
    """Risk-aware diet/plan advice: Groq (free) → Claude → "" (caller rule-based fallback).

    POST /chat: health summary risk_summary se server-side attach hoti hai (12-INTEGRATION §5).
    Dono keys missing ho to "" return karta hai.

    Factual nutrition lookups (calories/macros of a food) yahan nahi aate — unhe
    `_check_api_queries` focused nutrition prompt se handle karta hai.
    """
    # Poora DB health assessment system prompt mein — LLM isi ko padh kar diet + plan deta hai.
    health_context = build_health_context(prediction, profile)
    swap_hints = build_diet_swap_hints(prediction)

    # Intent-based length (short-by-default): explicit plan request pe clean exact plan,
    # warna smart + short + to-the-point. (User: "meaningful ho or smart but short reply".)
    is_plan_request = bool(_PLAN_REQUEST_RE.search(message))

    if is_plan_request:
        # Clean exact plan — swap-explanation ke bina (warna plan messy ho jaata hai).
        return _llm_chat(_plan_system_prompt(health_context, swap_hints), history, max_tokens=1200)

    system_prompt = (
        "You are the AI Diet & Longevity Advisor of this platform. "
        "Below is the user's complete health assessment fetched from the platform database.\n\n"
        "=== USER HEALTH ASSESSMENT ===\n"
        f"{health_context}\n"
        "=== END ASSESSMENT ===\n\n"
        + ("=== DISEASE FOOD-SWAP GUIDE (use these exact swaps) ===\n"
           f"{swap_hints}\n=== END GUIDE ===\n\n" if swap_hints else "")
        + "Give PERSONALISED, PRACTICAL advice. Be smart, meaningful and to-the-point:\n"
        "- Anchor advice to the user's HIGHEST disease risks and their actual numbers.\n"
        "- DISEASE-SWAP RULE: whenever you suggest a food/meal that one of the user's elevated "
        "conditions would restrict, in the SAME line give its better alternative — e.g. \"White "
        "rice — but your diabetes risk is high, so have brown rice or quinoa instead\". Apply this "
        "only for the user's actual elevated risks; do NOT invent swaps for conditions the user "
        "does not have.\n"
        "- DEFAULT = SHORT & SMART: reply in 2-3 tight bullets, under ~70 words TOTAL. "
        "One line per bullet. Answer the user's specific question first, then personalise.\n"
        "- Never diagnose a condition. Always end with a one-line medical disclaimer."
    )

    return _llm_chat(system_prompt, history, max_tokens=600)


# ══════════════════════════════════════════════════════════════
#  Route handler
# ══════════════════════════════════════════════════════════════

@router.post("/{user_id}/message")
async def send_message(
    user_id: int,
    data: ChatMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the diet chatbot."""
    prediction = (
        db.query(PredictionResult)
        .join(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .order_by(PredictionResult.created_at.desc())
        .first()
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="No prediction found. Complete a health assessment first.")

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).order_by(UserProfile.created_at.desc()).first()

    # S15: STATELESS chat — DB mein kuch SAVE NAHI hota (user: "chat DB mein na ho, session-based,
    # refresh pe fresh"). Client apne current page ke pichhle messages `history` mein bhejta hai →
    # multi-turn context milta hai; refresh pe client state khali → chat fresh. `session_id` sirf
    # echo/reference ke liye (koi ChatSession row ban/update nahi hoti).
    session_id = (data.session_id or "").strip() or uuid.uuid4().hex
    history = [
        {"role": m.get("role"), "content": m.get("content")}
        for m in (data.history or [])
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    ][-10:]

    # Step 1: Try API-powered queries first
    api_response = await _check_api_queries(data.message, prediction, profile)

    if api_response:
        assistant_message = api_response
    else:
        # Step 2: Groq (free) → Claude → rule-based fallback
        llm_history = history + [{"role": "user", "content": data.message}]
        assistant_message = _llm_response(data.message, prediction, profile, llm_history)
        if not assistant_message:
            assistant_message = generate_response(data.message, prediction, profile)

    return ChatResponse(
        response=assistant_message,
        risk_context=build_risk_badge(prediction),
        session_id=session_id,
    )


@router.get("/{user_id}/history")
def get_chat_history(
    user_id: int,
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """S15: chat DB mein save nahi hota → history HAMESHA khaali.

    (Purani `chat_sessions` table ab use nahi hoti; chat sirf client-side session state mein
    rehti hai — refresh pe fresh. Endpoint frontend compat ke liye rakha hai.)
    """
    return {"messages": [], "risk_context": None}
