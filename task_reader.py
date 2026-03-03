from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Iterable
import csv


@dataclass
class Task:
    id: str
    course: str
    title: str
    assignment_type: str
    due: datetime
    status: str  # "Open" or "Completed"
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    minutes_spent: Optional[int] = None


def _parse_dt(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None

    # Handles ISO 8601 like "2026-02-05T18:20:00" or with timezone
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass

    # fallback formats (if you ever change CSV format)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M %p", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    return None


def find_grades_base_dir() -> Path:
    """Find Documents/Grades or OneDrive/Documents/Grades on Windows."""
    home = Path.home()
    candidates = [
        home / "Documents" / "Grades",
        home / "OneDrive" / "Documents" / "Grades",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    raise FileNotFoundError("Could not find Grades folder in Documents or OneDrive/Documents.")


def tasks_dir_for_semester(semester: str, base_dir: Optional[Path] = None) -> Path:
    base = base_dir or find_grades_base_dir()
    return base / semester / "Tasks"


def task_csv_path(semester: str, course: str, base_dir: Optional[Path] = None) -> Path:
    return tasks_dir_for_semester(semester, base_dir) / f"{course}_tasks.csv"


def read_tasks_for_course(
    semester: str,
    course: str,
    base_dir: Optional[Path] = None,
    include_completed: bool = True,
) -> list[Task]:
    """
    Read tasks for one course from the Tasks folder.
    Returns open tasks by default; include_completed=True returns all.
    """
    path = task_csv_path(semester, course, base_dir)
    if not path.exists():
        return []

    out: list[Task] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = (row.get("Status") or "").strip() or "Open"
            if (not include_completed) and status.lower() == "completed":
                continue

            due = _parse_dt(row.get("Due", ""))
            if due is None:
                # skip malformed rows
                continue

            minutes = row.get("MinutesSpent", "")
            minutes_spent = int(minutes) if (minutes and minutes.strip().isdigit()) else None

            out.append(
                Task(
                    id=(row.get("Id") or "").strip(),
                    course=course,
                    title=(row.get("Title") or "").strip(),
                    assignment_type=(row.get("AssignmentType") or "").strip(),
                    due=due,
                    status=status,
                    created_at=_parse_dt(row.get("CreatedAt", "")),
                    completed_at=_parse_dt(row.get("CompletedAt", "")),
                    minutes_spent=minutes_spent,
                )
            )
    # Sort by due date
    out.sort(key=lambda t: t.due)
    return out


def read_all_tasks(
    semester: str,
    base_dir: Optional[Path] = None,
) -> dict[str, list[Task]]:
    """
    Read all  tasks in a semester.
    Returns {course: [Task,...]}.
    """
    tdir = tasks_dir_for_semester(semester, base_dir)
    if not tdir.exists():
        return {}

    tasks_by_course: dict[str, list[Task]] = {}
    for csv_file in tdir.glob("*_tasks.csv"):
        course = csv_file.stem.replace("_tasks", "")
        tasks_by_course[course] = read_tasks_for_course(semester, course, base_dir)

    # Remove empty courses
    tasks_by_course = {c: ts for c, ts in tasks_by_course.items() if ts}
    return tasks_by_course


def summarize_minutes_by_type(
    semester: str,
    course: str,
    base_dir: Optional[Path] = None,
) -> dict[str, float]:
    """
    Agent feature: average minutes spent per assignment type (from completed tasks).
    Returns {assignment_type: avg_minutes}.
    """
    tasks = read_tasks_for_course(semester, course, base_dir, include_completed=True)
    completed = [t for t in tasks if t.status.lower() == "completed" and t.minutes_spent is not None]

    buckets: dict[str, list[int]] = {}
    for t in completed:
        key = t.assignment_type or "Unknown"
        buckets.setdefault(key, []).append(int(t.minutes_spent))

    return {k: sum(v) / len(v) for k, v in buckets.items() if v}
