"""
Health & Fitness API Service — Enhanced
- Nutrition lookup: CaloriNinjas API (free tier: 10k req/day)
- Exercise lookup: API Ninjas Exercise API (free tier: 10k req/month)
- Macro calculator (TDEE, BMR, protein/carbs/fat targets)
- Fitness plan generator
- Food comparison

API: https://api-ninjas.com/  (single free key for all endpoints)
Env: APININJAS_KEY
"""
import os
import httpx
from typing import Optional

APININJAS_KEY = os.getenv("APININJAS_KEY", "")
HEADERS = {"X-Api-Key": APININJAS_KEY} if APININJAS_KEY else {}
TIMEOUT = 10.0


# ──────────────────────── Nutrition API ────────────────────────

async def search_nutrition(food_query: str) -> list[dict]:
    """Search nutrition info. Returns list of food dicts with calories, macros, etc."""
    if not APININJAS_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                "https://api.api-ninjas.com/v1/nutrition",
                headers=HEADERS,
                params={"query": food_query},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


# ──────────────────────── Exercise API ────────────────────────

async def search_exercises(
    muscle: str = None,
    exercise_type: str = None,
    difficulty: str = None,
    name: str = None,
) -> list[dict]:
    """Search exercises by muscle, type, difficulty, or name."""
    if not APININJAS_KEY:
        return []
    try:
        params = {}
        if muscle:
            params["muscle"] = muscle
        if exercise_type:
            params["type"] = exercise_type
        if difficulty:
            params["difficulty"] = difficulty
        if name:
            params["name"] = name
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                "https://api.api-ninjas.com/v1/exercises",
                headers=HEADERS,
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


# ──────────────────────── Macro Calculator ────────────────────────

def calculate_macros(weight_kg: float, height_cm: float, age: int, gender: int, exercise_level: int, goal: str = "maintain") -> dict:
    """
    Calculate TDEE and macro targets.
    gender: 0=female, 1=male
    exercise_level: 0-4 (sedentary to very active)
    goal: maintain, lose, gain
    """
    # BMR (Mifflin-St Jeor)
    if gender == 1:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    # Activity multiplier
    multipliers = {0: 1.2, 1: 1.375, 2: 1.55, 3: 1.725, 4: 1.9}
    tdee = bmr * multipliers.get(exercise_level, 1.55)

    # Adjust for goal
    if goal == "lose":
        tdee_target = tdee - 500  # ~0.5 kg/week loss
    elif goal == "gain":
        tdee_target = tdee + 300  # ~0.25 kg/week gain
    else:
        tdee_target = tdee

    # Protein: 1.6-2.2g per kg
    protein_g = weight_kg * 2.0
    protein_cal = protein_g * 4

    # Fat: 25-30% of calories
    fat_cal = tdee_target * 0.28
    fat_g = fat_cal / 9

    # Carbs: remaining calories
    carb_cal = tdee_target - protein_cal - fat_cal
    carb_g = max(carb_cal / 4, 0)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": round(tdee_target),
        "protein_g": round(protein_g),
        "carbs_g": round(carb_g),
        "fat_g": round(fat_g),
        "goal": goal,
    }


# ──────────────────────── Formatters ────────────────────────

def format_nutrition(data: list[dict], food_name: str) -> str:
    """Format nutrition data into a rich chat response.

    NOTE: API Ninjas **free tier** calories/protein ke liye placeholder bhejta hai
    ("Only available for premium subscribers.") — `_sf` usay 0 kar deta hai. Aise
    rows skip karte hain; agar kisi bhi row mein usable calories na ho to "" return
    karte hain taake caller LLM pe fall back kar sake (pehle user ko galat
    "0 kcal" dikhta tha aur LLM path chhut jaata tha).
    """
    if not data:
        return ""

    def _sf(x):
        try:
            if isinstance(x, str):
                s = x.strip().lower()
                if any(k in s for k in ("premium", "subscriber", "available", "n/a", "na", "not available")):
                    return 0
                try:
                    return float(s)
                except Exception:
                    return 0
            if isinstance(x, (int, float)):
                return float(x)
        except Exception:
            return 0
        return 0

    blocks = []
    for item in data[:3]:
        calories = _sf(item.get("calories", 0))
        if calories <= 0:
            continue  # free-tier/premium placeholder ya missing calories → skip
        name = item.get("name", food_name.title())
        serving = _sf(item.get("serving_size_g", 100))
        protein = _sf(item.get("protein_g", 0))
        carbs = _sf(item.get("carbohydrates_total_g", 0))
        fat = _sf(item.get("fat_total_g", 0))
        fiber = _sf(item.get("fiber_g", 0))
        sugar = _sf(item.get("sugar_g", 0))
        sodium = _sf(item.get("sodium_mg", 0))
        cholesterol = _sf(item.get("cholesterol_mg", 0))
        sat_fat = _sf(item.get("fat_saturated_g", 0))

        # Quality rating
        protein_pct = (protein * 4 / calories * 100) if calories else 0
        if protein_pct > 30:
            quality = "🟢 High Protein"
        elif fiber > 3:
            quality = "🟢 High Fiber"
        elif sugar > 15:
            quality = "🔴 High Sugar"
        elif sodium > 500:
            quality = "🟡 High Sodium"
        else:
            quality = "🟢 Balanced"

        block = [
            f"**{name}** ({serving}g)",
            f"  🔥 **{calories} kcal** | {quality}",
            f"  💪 Protein: **{protein}g** | 🍞 Carbs: **{carbs}g** | 🧈 Fat: **{fat}g**",
        ]
        if fiber or sugar:
            block.append(f"  🌾 Fiber: {fiber}g | 🍬 Sugar: {sugar}g")
        if sat_fat or sodium:
            block.append(f"  🫀 Sat. Fat: {sat_fat}g | 🧂 Sodium: {sodium}mg | Cholesterol: {cholesterol}mg")
        blocks.append("\n".join(block))

    if not blocks:
        return ""
    return f"🔍 **Nutrition Facts: \"{food_name}\"**\n\n" + "\n\n".join(blocks) + "\n"


def format_nutrition_comparison(foods: list[list[dict]], names: list[str]) -> str:
    """Compare nutrition of multiple foods side by side.

    Free-tier placeholder (calories unavailable) wale foods skip; agar kisi bhi
    food ka usable data na ho to "" return (caller LLM pe fall back kare).
    """
    if not foods or not any(foods):
        return ""

    def _sf(x):
        try:
            if isinstance(x, str):
                s = x.strip().lower()
                if any(k in s for k in ("premium", "subscriber", "available", "n/a", "na", "not available")):
                    return 0
                return float(s)
            if isinstance(x, (int, float)):
                return float(x)
        except Exception:
            return 0
        return 0

    lines = ["⚖️ **Food Comparison:**\n"]
    shown = 0
    for data, name in zip(foods, names):
        if not data:
            continue
        item = data[0]  # top result
        cal = _sf(item.get("calories", 0))
        if cal <= 0:
            continue  # premium placeholder → skip (0 kcal dikhane se behtar LLM)
        pro = _sf(item.get("protein_g", 0))
        carb = _sf(item.get("carbohydrates_total_g", 0))
        fat = _sf(item.get("fat_total_g", 0))
        fiber = _sf(item.get("fiber_g", 0))
        serv = _sf(item.get("serving_size_g", 100))
        lines.append(f"**{item.get('name', name.title())}** (per {serv}g)")
        lines.append(f"  🔥 {int(cal)} kcal | 💪 {pro}g P | 🍞 {carb}g C | 🧈 {fat}g F | 🌾 {fiber}g Fiber")
        lines.append("")
        shown += 1

    if shown == 0:
        return ""
    return "\n".join(lines)


def format_exercises(data: list[dict], query: str) -> str:
    """Format exercise data with rich details."""
    if not data:
        return ""

    lines = [f"🏋️ **Exercises for \"{query}\":**\n"]

    for i, ex in enumerate(data[:5], 1):
        name = ex.get("name", "Unknown")
        muscle = ex.get("muscle", "")
        equipment = ex.get("equipment", "None")
        difficulty = ex.get("difficulty", "unknown")
        instructions = ex.get("instructions", "")
        type_ = ex.get("type", "")

        diff_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(difficulty, "⚪")
        type_emoji = {"strength": "💪", "cardio": "❤️", "stretching": "🧘", "plyometrics": "⚡", "powerlifting": "🏋️"}.get(type_, "🏃")

        lines.append(f"**{i}. {name}**")
        lines.append(f"   {type_emoji} {type_.title()} | 💪 {muscle} | {diff_emoji} {difficulty.title()} | 🏗️ {equipment}")
        if instructions:
            short = instructions[:250] + ("..." if len(instructions) > 250 else "")
            lines.append(f"   📝 {short}")
        lines.append("")

    return "\n".join(lines)


def format_fitness_plan(exercises: list[dict], goal: str, days: int = 3) -> str:
    """Generate a fitness plan from exercise API data."""
    if not exercises:
        return ""

    # Split exercises by muscle group
    by_muscle = {}
    for ex in exercises:
        m = ex.get("muscle", "other")
        by_muscle.setdefault(m, []).append(ex)

    # Create day-wise split
    muscle_groups = list(by_muscle.keys())
    lines = [f"🏋️ **Your {days}-Day Fitness Plan** ({goal.title()} Goal)\n"]

    exercises_per_day = max(len(exercises) // days, 3)
    idx = 0

    for day in range(1, days + 1):
        day_exercises = exercises[idx:idx + exercises_per_day] or exercises[:3]
        idx += exercises_per_day

        # Determine muscle focus
        day_muscles = list(set(e.get("muscle", "") for e in day_exercises))
        focus = " & ".join(m.title() for m in day_muscles if m) or "Full Body"

        lines.append(f"📅 **Day {day}: {focus}**")
        for j, ex in enumerate(day_exercises, 1):
            name = ex.get("name", "Exercise")
            diff = ex.get("difficulty", "")
            eq = ex.get("equipment", "None")
            lines.append(f"   {j}. **{name}** ({diff}) — Equipment: {eq}")
        lines.append("")

    lines.append("💡 **Tips:**")
    lines.append("- Warm up 5-10 min before each session")
    lines.append("- Rest 60-90 seconds between sets")
    lines.append("- Stay hydrated throughout")
    lines.append("- Progressive overload: increase weight/reps weekly")

    return "\n".join(lines)


def format_macro_response(macros: dict, profile_info: dict) -> str:
    """Format macro calculator response."""
    goal_emoji = {"lose": "📉", "gain": "📈", "maintain": "⚖️"}.get(macros["goal"], "⚖️")
    goal_text = {"lose": "Weight Loss", "gain": "Muscle Gain", "maintain": "Maintenance"}.get(macros["goal"], "Maintenance")

    lines = [
        f"📊 **Your Daily Macro Targets** ({goal_text})\n",
        f"🎯 **Calories: {macros['target_calories']} kcal/day**",
        f"💪 **Protein: {macros['protein_g']}g** ({macros['protein_g']*4} kcal)",
        f"🍞 **Carbs: {macros['carbs_g']}g** ({macros['carbs_g']*4} kcal)",
        f"🧈 **Fat: {macros['fat_g']}g** ({macros['fat_g']*9} kcal)\n",
        f"📏 **Stats:**",
        f"- BMR (basal metabolic rate): {macros['bmr']} kcal",
        f"- TDEE (total daily expenditure): {macros['tdee']} kcal",
        f"- Activity level: {profile_info.get('exercise_level', '?')}/4",
        f"- Goal: {goal_emoji} {goal_text}\n",
    ]

    if macros["goal"] == "lose":
        lines.append("💡 **Tips for fat loss:**")
        lines.append("- Eat protein with every meal (keeps you full)")
        lines.append("- Prioritize whole foods over processed")
        lines.append("- Don't go below 1200 kcal (women) / 1500 kcal (men)")
        lines.append("- Combine with strength training to preserve muscle")
    elif macros["goal"] == "gain":
        lines.append("💡 **Tips for muscle gain:**")
        lines.append("- Eat protein within 2 hours post-workout")
        lines.append("- Don't skip meals — aim for 4-5 meals/day")
        lines.append("- Focus on compound lifts (squat, bench, deadlift)")
        lines.append("- Sleep 7-9 hours for recovery")
    else:
        lines.append("💡 **Tips for maintenance:**")
        lines.append("- Stay consistent with meal timing")
        lines.append("- Monitor weight weekly (same time, same conditions)")
        lines.append("- Adjust calories if weight changes unexpectedly")

    return "\n".join(lines)
