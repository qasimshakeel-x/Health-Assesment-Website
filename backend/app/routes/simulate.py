"""Future health simulation route."""
from fastapi import APIRouter, Depends
from backend.app.middleware.auth import get_current_user
from backend.app.models.database import User
from backend.app.schemas.user import SimulationInput
from ml.models.future_simulator import FutureSimulator

router = APIRouter()
simulator = FutureSimulator()


@router.post("")
def simulate_future(
    data: SimulationInput,
    current_user: User = Depends(get_current_user)
):
    """Run future health simulation with lifestyle changes."""
    # Use cached profile data (would come from user's latest prediction in production)
    current_profile = {
        "bmi": 28.0,
        "biological_age": 45.0,
        "diabetes_risk": 35.0,
        "heart_risk": 28.0,
        "age": 40
    }

    changes = {
        "sleep_hours": data.sleep_hours_delta,
        "exercise_level": data.exercise_level_delta,
        "smoking_quit": data.smoking_quit,
        "bmi_improvement": data.bmi_improvement,
        "diet_improvement": data.diet_improvement
    }

    return simulator.simulate(current_profile, data.years, changes)
