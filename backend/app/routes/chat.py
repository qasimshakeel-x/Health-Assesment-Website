"""Diet Chat route — rule-based health diet chatbot with risk-aware context + live API integrations."""
import os
import re
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.models.database import get_db, User, PredictionResult, UserProfile, ChatSession
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


def build_risk_summary(p: PredictionResult, profile: UserProfile) -> str:
    lines = []
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


def generate_response(msg: str, prediction: PredictionResult, profile: UserProfile) -> str:
    text = msg.lower().strip()
    p = prediction
    bmi = profile.bmi if profile.bmi else 0

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
        if p.diabetes_risk and p.diabetes_risk > 40:
            tips.append("🩸 **Diabetes-friendly:** Oatmeal with nuts & berries, eggs with avocado, Greek yogurt (unsweetened)")
        if p.heart_risk and p.heart_risk > 40:
            tips.append("❤️ **Heart-healthy:** Oatmeal with walnuts, whole grain toast with olive oil, smoothie with flaxseed")
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            tips.append("🧠 **Mood-boosting:** Eggs (choline + B12), banana smoothie, oatmeal with dark chocolate chips")
        if not tips:
            tips.append("🥗 **Balanced options:**\n- Overnight oats with chia seeds & berries\n- Whole grain toast with avocado & egg\n- Greek yogurt parfait with granola & nuts\n- Green smoothie (spinach, banana, protein)")
        return ("🍳 **Healthy Breakfast Ideas:**\n\n" + "\n\n".join(tips) + "\n\n💡 **Tips:** Include protein + fiber for sustained energy. Avoid sugary cereals and pastries." + DISCLAIMER)

    # ============ LUNCH / DINNER / MEAL ============
    if re.search(r'\b(lunch|dopehar|dinner|shaam|meal|khana|eat|food|recipe|cook)\b', text):
        tips = []
        if p.diabetes_risk and p.diabetes_risk > 40:
            tips.append("🩸 **For blood sugar control:**\n- Grilled chicken with quinoa & roasted veggies\n- Lentil soup with whole grain bread\n- Stir-fry with tofu, broccoli, brown rice")
        if p.heart_risk and p.heart_risk > 40:
            tips.append("❤️ **Heart-healthy meals:**\n- Baked salmon with sweet potato & spinach\n- Mediterranean salad (olive oil, feta, olives)\n- Bean tacos with fresh salsa & avocado")
        if p.hypertension_risk and p.hypertension_risk > 40:
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
        if p.diabetes_risk and p.diabetes_risk > 40:
            options.append("🩸 Avoid: candy, cookies, juice. Choose: nuts, cheese, vegetables")
        if p.heart_risk and p.heart_risk > 40:
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
        if p.diabetes_risk and p.diabetes_risk > 40:
            tips.append("🩸 **Avoid:** fruit juices, sodas, sweetened coffee. Choose: water, unsweetened tea")
        if p.hypertension_risk and p.hypertension_risk > 40:
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
        if p.diabetes_risk and p.diabetes_risk > 40:
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
        if p.obesity_risk and p.obesity_risk > 50:
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
        if p.heart_risk and p.heart_risk > 45:
            return ("🥩 **Protein sources for heart health:**\n\n"
                    "✅ **Best choices:**\n- Grilled/baked fish (salmon, mackerel) — omega-3\n- Chicken breast (skinless) — lean protein\n- Eggs (1-2/day) — protein + choline\n- Lentils & beans — plant protein + fiber\n\n"
                    "⚠️ **Limit:**\n- Red meat (beef, mutton) — 1x/week max\n- Fried meats\n- Processed meats (sausage, bacon)\n\n"
                    "🍳 **Cooking tips:** Bake, grill, or steam instead of frying. Use olive oil." + DISCLAIMER)
        return ("🥩 **Protein Guide:**\n\n"
                "- Chicken breast: lean protein, grill or bake\n- Fish: omega-3, 2x/week recommended\n- Eggs: complete protein, 1-2/day\n- Paneer/tofu: good for vegetarians\n- Lentils/beans: plant protein + fiber\n\n"
                "📏 **Portion:** Size of your palm per meal" + DISCLAIMER)

    if re.search(r'\b(rice|chawal|biryani|pulao)\b', text):
        if p.diabetes_risk and p.diabetes_risk > 40:
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
        if p.diabetes_risk and p.diabetes_risk > 40:
            tips.append("🩸 **Choose low-GI fruits:**")
            tips.append("- Berries (strawberry, blueberry) — best for blood sugar\n- Apple with skin\n- Pear\n- Orange\n- Kiwi")
            tips.append("\n⚠️ **Limit high-sugar fruits:** Mango, grapes, banana (half only), dried fruits")
            tips.append("\n📏 **Portion:** 1-2 servings/day, eat whole not juice")
        else:
            tips.append("✅ **Great choices:**\n- Berries (antioxidants)\n- Apples (fiber)\n- Bananas (potassium)\n- Oranges (vitamin C)\n- Kiwi (vitamin C + fiber)")
            tips.append("\n📏 **Portion:** 2-3 servings/day, eat whole not juice")
        return "\n".join(tips) + DISCLAIMER

    # ============ DIET PLAN / MEAL PLAN ============
    if re.search(r'\b(diet plan|meal plan|daily plan|full day|poora din|menu plan|planner|what should i eat today|sara din|pura din)\b', text):
        bmi_cat = "underweight" if bmi < 18.5 else "normal" if bmi < 25 else "overweight" if bmi < 30 else "obese"
        cal_range = "1500-1800" if profile.gender == 0 else "1800-2200"
        if bmi_cat in ("overweight", "obese"):
            cal_range = "1400-1700" if profile.gender == 0 else "1600-2000"

        plan = [f"🗓️ **Your Personalized Daily Diet Plan**\n",
                f"📊 Based on: BMI {bmi:.1f} ({bmi_cat}), Age {profile.age}, Gender {'Male' if profile.gender == 1 else 'Female'}",
                f"🎯 Target calories: **{cal_range} kcal/day**\n"]

        plan.append("🌅 **Early Morning (6-7 AM):**")
        plan.append("- 1 glass warm water + lemon")
        if p.diabetes_risk and p.diabetes_risk > 40:
            plan.append("- Soaked fenugreek seeds (methi) — helps blood sugar")
        else:
            plan.append("- 5-6 soaked almonds")

        plan.append("\n🍳 **Breakfast (7-8 AM):**")
        if p.diabetes_risk and p.diabetes_risk > 40:
            plan.append("- Moong dal chilla with paneer filling")
            plan.append("- 1 cup green tea (unsweetened)")
        elif p.heart_risk and p.heart_risk > 40:
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
        if p.hypertension_risk and p.hypertension_risk > 40:
            plan.append("⚠️ Use minimal salt — flavor with lemon, herbs, spices")

        plan.append("\n🫖 **Evening Snack (4-5 PM):**")
        plan.append("- Green tea / herbal tea")
        plan.append("- 1 small bowl roasted chana OR vegetable soup")

        plan.append("\n🌙 **Dinner (7-8 PM):**")
        plan.append("- 1-2 roti (light, whole wheat)")
        plan.append("- 1 bowl dal or grilled fish/chicken")
        plan.append("- 1 bowl vegetable (steamed/light cooked)")
        if p.obesity_risk and p.obesity_risk > 50:
            plan.append("⚠️ Keep dinner light — avoid rice at night")

        plan.append("\n🌜 **Bedtime (9-10 PM):**")
        plan.append("- 1 glass warm turmeric milk (haldi doodh)")
        if p.depression_level in ["Moderate", "Moderately Severe", "Severe"]:
            plan.append("- Chamomile tea for better sleep")

        plan.append("\n💧 **Hydration:** 8-10 glasses of water throughout the day")
        plan.append(f"\n🏋️ **Exercise:** 30 min walk after lunch & dinner")
        if p.diabetes_risk and p.diabetes_risk > 40:
            plan.append("(Post-meal walks help control blood sugar!)")

        return "\n".join(plan) + "\n\n💡 **Tips:**\n- Eat at consistent times daily\n- Chew food slowly (20+ times)\n- Stop eating 2-3 hours before sleep\n- Control portions — use smaller plates" + DISCLAIMER

    # ============ SUGAR / SWEETS ============
    if re.search(r'\b(sugar|sweet|meetha|cake|cookie|chocolate|candy|mithai)\b', text):
        if p.diabetes_risk and p.diabetes_risk > 40:
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
        if p.hypertension_risk and p.hypertension_risk > 40:
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
        if p.heart_risk and p.heart_risk > 45:
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
    if p.diabetes_risk and p.diabetes_risk > 40:
        risk_context += "🩸 Your diabetes risk is elevated — focus on low-sugar, high-fiber foods.\n"
    if p.heart_risk and p.heart_risk > 40:
        risk_context += "❤️ Your heart risk is elevated — choose omega-3 fish, olive oil, nuts.\n"
    if p.hypertension_risk and p.hypertension_risk > 40:
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
        r'(?:calories?|calorie|nutrition|nutrients?|kcal|macros?)\s+(?:in|of|for)\s+(.+)',
        clean,
    )
    if not nutri_match:
        nutri_match = re.search(
            r'(?:how\s+(?:many|much)\s+)?(?:calories?|calorie|kcal)\s+(?:is\s+(?:there\s+)?(?:in\s+)?)?([\w\s]+)',
            clean,
        )
    if not nutri_match:
        nutri_match = re.search(
            r'(?:what\s+(?:are\s+)?(?:the\s+)?(?:calories?|macros?|nutrients?|nutrition))\s+(?:in|of|for)\s+(.+)',
            clean,
        )
    if nutri_match:
        food = re.sub(r'[?!.,;:]+$', '', nutri_match.group(1)).strip()
        if food and len(food) > 1:
            data = await search_nutrition(food)
            if data:
                return format_nutrition(data, food)

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
                return format_nutrition_comparison([data1, data2], [food1, food2])

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
        if prediction.diabetes_risk and prediction.diabetes_risk > 40:
            result += "🩸 **Tip:** Drinking water before meals helps control blood sugar!\n"
        if prediction.hypertension_risk and prediction.hypertension_risk > 40:
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

    session = db.query(ChatSession).filter(ChatSession.prediction_id == prediction.id).first()
    if not session:
        session = ChatSession(prediction_id=prediction.id, system_prompt="diet_chat", messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)

    messages = session.messages or []
    messages.append({"role": "user", "content": data.message})

    # Step 1: Try API-powered queries first
    api_response = await _check_api_queries(data.message, prediction, profile)

    if api_response:
        assistant_message = api_response
    else:
        # Step 2: Try Claude API, fall back to rule-based
        ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        assistant_message = ""

        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY not in ("", "your-api-key-here"):
            try:
                import httpx as httpx_sync
                risk_summary = build_risk_summary(prediction, profile)
                system_prompt = (
                    f"You are a health-focused AI diet advisor. "
                    f"The user has this health profile:\n{risk_summary}\n\n"
                    f"Provide personalized, evidence-based nutrition advice. "
                    f"Always end with a medical disclaimer. Never diagnose conditions."
                )
                with httpx_sync.Client(timeout=30.0) as client:
                    response = client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": ANTHROPIC_API_KEY,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": "claude-sonnet-4-20250514",
                            "max_tokens": 1024,
                            "system": system_prompt,
                            "messages": messages[-10:]
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    assistant_message = result["content"][0]["text"]
            except Exception:
                assistant_message = generate_response(data.message, prediction, profile)
        else:
            assistant_message = generate_response(data.message, prediction, profile)

    messages.append({"role": "assistant", "content": assistant_message})
    session.messages = messages
    session.last_message_at = datetime.utcnow()
    db.commit()

    return ChatResponse(
        response=assistant_message,
        risk_context=f"Risk Profile Active - Diabetes: {prediction.diabetes_risk}%, Heart: {prediction.heart_risk}%"
    )


@router.get("/{user_id}/history")
def get_chat_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history for a user."""
    session = (
        db.query(ChatSession)
        .join(PredictionResult)
        .join(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .order_by(ChatSession.last_message_at.desc())
        .first()
    )
    if not session:
        return {"messages": [], "risk_context": None}

    return {
        "messages": session.messages or [],
        "risk_context": f"Risk Profile Active"
    }
