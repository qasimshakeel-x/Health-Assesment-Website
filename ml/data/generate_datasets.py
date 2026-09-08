"""Generate synthetic training datasets that match public dataset schemas."""
import csv
import random
import os

random.seed(42)


def generate_pima_diabetes(n=768):
    """Generate PIMA Indians Diabetes-like dataset."""
    rows = []
    for _ in range(n):
        pregnancies = random.randint(0, 17)
        glucose = random.gauss(121, 32)
        glucose = max(44, min(199, glucose))
        bp = random.gauss(72, 12)
        bp = max(24, min(122, bp))
        skin = random.gauss(27, 8)
        skin = max(7, min(99, skin))
        insulin = random.gauss(121, 80)
        insulin = max(14, min(846, insulin))
        bmi = random.gauss(32, 8)
        bmi = max(18, min(67, bmi))
        dpf = random.gauss(0.47, 0.33)
        dpf = max(0.078, min(2.42, dpf))
        age = random.randint(21, 81)

        # Realistic outcome probability
        risk = (
            0.001 * glucose + 0.002 * bmi + 0.003 * age
            + 0.02 * pregnancies + 0.1 * dpf - 0.08 * bp
        )
        outcome = 1 if random.random() < 1 / (1 + max(-risk, -10)) else 0

        rows.append([
            pregnancies, round(glucose, 1), round(bp, 1),
            round(skin, 1), round(insulin, 1), round(bmi, 1),
            round(dpf, 3), age, outcome
        ])
    return rows


def generate_heart_disease(n=918):
    """Generate UCI Heart Disease-like dataset."""
    rows = []
    for _ in range(n):
        age = random.randint(28, 77)
        sex = random.randint(0, 1)
        cp = random.randint(0, 3)  # chest pain type
        trestbps = random.gauss(132, 18)
        trestbps = max(94, min(200, trestbps))
        chol = random.gauss(246, 51)
        chol = max(126, min(564, chol))
        fbs = 1 if random.random() < 0.15 else 0
        restecg = random.randint(0, 2)
        thalach = random.gauss(137, 26)
        thalach = max(71, min(202, thalach))
        exang = 1 if random.random() < 0.33 else 0
        oldpeak = random.gauss(1.04, 1.2)
        oldpeak = max(0, min(6.2, oldpeak))
        slope = random.randint(0, 2)
        ca = random.randint(0, 4)
        thal = random.randint(0, 3)

        # Risk factors
        risk = (
            0.01 * age - 0.005 * thalach + 0.1 * cp
            + 0.02 * oldpeak + 0.15 * exang + 0.1 * thal
            + 0.05 * ca - 0.08 * restecg
        )
        target = 1 if random.random() < 1 / (1 + max(-risk, -10)) else 0

        rows.append([
            age, sex, cp, round(trestbps, 1), round(chol, 1),
            fbs, restecg, round(thalach, 1), exang,
            round(oldpeak, 2), slope, ca, thal, target
        ])
    return rows


def write_csv(path, headers, rows):
    """Write rows to a CSV file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  Wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    print("Generating synthetic training datasets...\n")

    # PIMA Diabetes
    pima_headers = [
        "Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
        "Insulin", "BMI", "DiabetesPedigreeFunction", "Age", "Outcome"
    ]
    write_csv(
        os.path.join(os.path.dirname(__file__), "pima_diabetes.csv"),
        pima_headers,
        generate_pima_diabetes(768)
    )

    # Heart Disease
    heart_headers = [
        "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
        "thalach", "exang", "oldpeak", "slope", "ca", "thal", "target"
    ]
    write_csv(
        os.path.join(os.path.dirname(__file__), "heart_disease.csv"),
        heart_headers,
        generate_heart_disease(918)
    )

    print("\nDatasets generated successfully!")
