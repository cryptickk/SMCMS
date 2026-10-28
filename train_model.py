from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent

# Change this to your actual dataset filename.
DATA_PATH = ROOT / "dataset" / "municipal_complaints_500.csv"

ARTIFACT_DIR = ROOT / "artifacts"
DEPARTMENT_MODEL_PATH = ARTIFACT_DIR / "department_classifier.joblib"
PRIORITY_MODEL_PATH = ARTIFACT_DIR / "priority_classifier.joblib"
METRICS_PATH = ARTIFACT_DIR / "evaluation_metrics.json"

VALID_PRIORITIES = {"High", "Medium", "Low"}


def make_pipeline():
    return Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                sublinear_tf=True,
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])


def evaluate_model(name, model, X_test, y_test):
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test, predictions, average="macro", zero_division=0
    )

    print(f"\n===== {name.upper()} RESULTS =====")
    print(f"Accuracy: {accuracy:.3f}")
    print(f"Macro-F1: {macro_f1:.3f}")
    print(classification_report(
        y_test, predictions, zero_division=0
    ))

    return {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "classification_report": classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
    }


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}\n"
            "Check DATA_PATH and place your CSV in the data folder."
        )

    data = pd.read_csv(DATA_PATH)

    required = {"complaint", "department", "priority"}
    missing = required - set(data.columns)

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}"
        )

    data = data.dropna(
        subset=["complaint", "department", "priority"]
    ).copy()

    for column in ["complaint", "department", "priority"]:
        data[column] = data[column].astype(str).str.strip()

    data["priority"] = data["priority"].str.title()

    data = data[
        (data["complaint"] != "")
        & (data["department"] != "")
        & (data["priority"].isin(VALID_PRIORITIES))
    ].copy()

    if data["department"].nunique() < 2:
        raise ValueError("At least two department classes are required.")

    if data["priority"].nunique() < 2:
        raise ValueError("At least two priority classes are required.")

    print(f"Usable dataset rows: {len(data)}")
    print("\nDepartment counts:")
    print(data["department"].value_counts().to_string())

    print("\nPriority counts:")
    print(data["priority"].value_counts().to_string())

    # Use the same split for both prediction tasks.
    # Stratification by department preserves department representation.
    X_train, X_test, dept_train, dept_test, pri_train, pri_test = (
        train_test_split(
            data["complaint"],
            data["department"],
            data["priority"],
            test_size=0.20,
            random_state=42,
            stratify=data["department"],
        )
    )

    department_model = make_pipeline()
    priority_model = make_pipeline()

    print("\nTraining department classifier...")
    department_model.fit(X_train, dept_train)

    print("Training priority classifier...")
    priority_model.fit(X_train, pri_train)

    department_metrics = evaluate_model(
        "Department classification",
        department_model,
        X_test,
        dept_test,
    )

    priority_metrics = evaluate_model(
        "Priority classification",
        priority_model,
        X_test,
        pri_test,
    )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(department_model, DEPARTMENT_MODEL_PATH)
    joblib.dump(priority_model, PRIORITY_MODEL_PATH)

    metrics = {
        "usable_rows": int(len(data)),
        "training_rows": int(len(X_train)),
        "testing_rows": int(len(X_test)),
        "random_state": 42,
        "department_model": department_metrics,
        "priority_model": priority_metrics,
        "note": (
            "Results are based on the held-out portion of this dataset. "
            "They do not guarantee real-world performance."
        ),
    }

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print("\nSaved department model:", DEPARTMENT_MODEL_PATH)
    print("Saved priority model:", PRIORITY_MODEL_PATH)
    print("Saved metrics:", METRICS_PATH)

    # Test a new complaint using both trained models.
    examples = [
        "There is a deep pothole near the school.",
        "An exposed electrical wire is sparking beside the road.",
        "The grass in the public garden needs mowing.",
    ]

    print("\n===== SAMPLE PREDICTIONS =====")

    for complaint in examples:
        dept_probs = department_model.predict_proba([complaint])[0]
        dept_index = int(dept_probs.argmax())
        department = department_model.classes_[dept_index]
        dept_confidence = float(dept_probs[dept_index])

        pri_probs = priority_model.predict_proba([complaint])[0]
        pri_index = int(pri_probs.argmax())
        priority = priority_model.classes_[pri_index]
        pri_confidence = float(pri_probs[pri_index])

        print(f"\nComplaint: {complaint}")
        print(
            f"Department: {department} "
            f"(model score: {dept_confidence:.3f})"
        )
        print(
            f"Priority: {priority} "
            f"(model score: {pri_confidence:.3f})"
        )


if __name__ == "__main__":
    main()