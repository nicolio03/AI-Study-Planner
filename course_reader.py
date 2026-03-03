from pathlib import Path
import os
import ipywidgets as widgets
from IPython.display import display


def select_semester():
    semesters = []
    candidates = [
        Path.home() / "Documents" / "Grades",
        Path.home() / "OneDrive" / "Documents" / "Grades",
    ]

    base_dir = None
    for c in candidates:
        if c.exists():
            base_dir = c
            break

    if base_dir is None:
        raise FileNotFoundError(
            "Could not find a Grades folder in Documents or OneDrive/Documents."
        )

    for entry in base_dir.iterdir():
        if entry.is_dir():
            semesters.append(entry.name)

    dropdown = widgets.Dropdown(
    options=semesters,
    description="Semester:",
    layout=widgets.Layout(width="300px")
    )

    finalize_btn = widgets.Button(
    description="Select",
    button_style="success"
    )

    out = widgets.Output()

    state = {"semester": None, "base_dir": base_dir}

    finalize_btn.disabled = (dropdown.value is None)

    def on_change(change):
        finalize_btn.disabled = (change["new"] is None)

    dropdown.observe(on_change, names="value")

    display(widgets.VBox([dropdown, finalize_btn, out])) 

    def on_finalize(_):
        with out:
            out.clear_output()
            semester = dropdown.value
            semester_path = base_dir / semester

            state["semester"] = semester
            state["semester_path"] = semester_path

            course_grades = compute_semester_course_grades(semester_path)
            state["course_grades"] = course_grades

            if not course_grades:
                print("No .csv course files found in this semester folder.")
                return

            print("Semester set!")

    finalize_btn.on_click(on_finalize)

    return state

def compute_current_grade(course_csv: str | Path) -> float:
    course_csv = Path(course_csv)

    current_weighted_score = 0.0
    current_weight = 0.0

    lines = course_csv.read_text(encoding="utf-8").splitlines()

    for line in lines:
        parts = line.split(",")
        if len(parts) < 1:
            continue

        category = parts[0]

        lp = category.find("(")
        rp = category.find(")", lp + 1) if lp != -1 else -1
        semi = category.find(";", lp + 1) if lp != -1 else -1

        if lp == -1 or rp == -1:
            continue

        weight_end = semi if (semi != -1 and semi < rp) else rp
        weight_part = category[lp + 1:weight_end].replace("%", "").strip()

        try:
            weight = float(weight_part)
        except ValueError:
            continue

        drop = False
        if semi != -1 and semi < rp:
            drop_str = category[semi + 1:rp].strip()
            drop = drop_str.lower() == "yes"

        grades = []
        for tok in parts[1:]:
            tok = tok.strip()
            if not tok:
                continue
            try:
                grades.append(float(tok))
            except ValueError:
                pass

        if drop and grades:
            grades.remove(min(grades))

        if grades:  # only count toward CURRENT if there are grades
            category_avg = sum(grades) / len(grades)
            current_weighted_score += category_avg * (weight / 100.0)
            current_weight += weight

    return current_weighted_score / (current_weight / 100.0) if current_weight > 0 else 0.0

def normalize_course_name(filename: str) -> str:
    # "AI(3).csv" -> "AI"
    return Path(filename).stem.split("(")[0].strip()

def compute_semester_course_grades(semester_dir: str | Path) -> dict[str, float]:
    semester_dir = Path(semester_dir)

    course_grades: dict[str, float] = {}

    for csv_file in semester_dir.glob("*.csv"):
        course_name = normalize_course_name(csv_file.name)
        course_grades[course_name] = compute_current_grade(csv_file)

    return course_grades

def course_risk_weights(course_grades: dict[str, float], target=90.0) -> dict[str, float]:
    # lower grade => higher risk
    weights = {c: max(0.0, target - g) for c, g in course_grades.items()}
    
    # if all zero (everyone >= target), use equal weights
    if weights and all(w == 0.0 for w in weights.values()):
        weights = {c: 1.0 for c in weights}
    
    return weights

def normalize_course_grades(course_grades: dict[str, float], zero_means_missing=True) -> dict[str, float]:
    out = {}
    for course, g in course_grades.items():
        g = float(g)
        if zero_means_missing and g == 0.0:
            continue
        out[course.strip().upper()] = g
    return out