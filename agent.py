from datetime import datetime, timedelta
from typing import List, Tuple
import task_reader
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, time as dtime
from task_reader import Task
import uuid

"""
agent input schema:
semester: <class 'str'>
course_grades: <class 'dict'>
course_risk_weights: <class 'dict'>
busy_intervals: <class 'list'>
open_tasks_by_course: <class 'dict'>
"""

MAX_STUDY_BLOCK = 100
MIN_STUDY_BLOCK = 25

def coerce_dt_to_tz(dt: datetime, tz) -> datetime:
    """
    Return dt as timezone-aware in tz.
    - If dt is naive: attach tz (assume dt was intended to be local)
    - If dt is aware: convert to tz
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)

def validate_agent_input(state:dict):

    required_keys = {
        "semester",
        "course_grades",
        "course_risk_weights",
        "busy_intervals",
        "tasks_by_course",
    }

    assert required_keys.issubset(state.keys()), "Missing required top-level keys"

    # ---- Types of top-level values ----
    assert isinstance(state["semester"], str)
    assert isinstance(state["course_grades"], dict)
    assert isinstance(state["course_risk_weights"], dict)
    assert isinstance(state["busy_intervals"], list)
    assert isinstance(state["tasks_by_course"], dict)

    # ---- Course grades ----
    for course, grade in state["course_grades"].items():
        assert isinstance(course, str)
        assert isinstance(grade, (int, float))

    # ---- Risk weights ----
    for course, weight in state["course_risk_weights"].items():
        assert isinstance(course, str)
        assert isinstance(weight, (int, float))

    # ---- Busy intervals ----
    for interval in state["busy_intervals"]:
        assert isinstance(interval, tuple), "Busy interval must be a tuple"
        assert len(interval) == 2, "Busy interval must be (start, end)"

        start, end = interval
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert start < end, "Busy interval start must be before end"

    # ---- Tasks ----
    for course, tasks in state["tasks_by_course"].items():
        assert isinstance(course, str)
        assert isinstance(tasks, list)

        for task in tasks:
            assert isinstance(task, task_reader.Task)

            # Required task fields
            for field in ("course", "title", "assignment_type", "due", "status"):
                assert hasattr(task, field), f"Task missing field: {field}"

            assert isinstance(task.course, str)
            assert isinstance(task.title, str)
            assert isinstance(task.assignment_type, str)
            assert isinstance(task.due, datetime)
            assert isinstance(task.status, str)

    print("agent_input schema is valid")
    
def flatten_tasks(open_tasks_by_course):
    Tasks = []
    for course, tasks in open_tasks_by_course.items():
        for task in tasks:
            Tasks.append(task)
    return Tasks

def score_task(task, course_risk, now, due, threshold):
    """
    Returns a numeric priority score
    Higher = more urgent/important
    """
    tz = now.tzinfo

    if due.tzinfo is None:
        due = due.replace(tzinfo=tz)
    else:
        due = due.astimezone(tz)

    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    score = 0

    if task.status == "Completed":
        return score
    

    delta = due - now
    min_remaning = delta.total_seconds() / 60
    urgency = max(0, threshold - min_remaning)
    score += urgency

    return score
    
def avg_time_spent_on_previous (closed_tasks_by_course,in_course, assignment_type):
    time_spent = 0
    count = 0
    for course, tasks in closed_tasks_by_course.items():
        if course == in_course:
            for task in tasks:
                if assignment_type in task.assignment_type:
                    if task.minutes_spent is not None:
                        count += 1
                        if task.minutes_spent != 0:
                            time_spent += task.minutes_spent

    if count == 0:
        return 0

    return time_spent/count
    
def return_open_tasks_by_course(tasks_by_course):
    open_tasks = {}
    for course, tasks in tasks_by_course.items():
        for task in tasks:
            if course not in open_tasks:
                open_tasks[course] = []
            if task.status == "Open":
                open_tasks[course].append(task)
    return open_tasks

def return_closed_tasks_by_course(tasks_by_course):
    closed_tasks = {}
    for course, tasks in tasks_by_course.items():
        for task in tasks:
            if course not in closed_tasks:
                closed_tasks[course] = []
            if task.status == "Completed" or task.status == "Scheduled":
                closed_tasks[course].append(task)
    return closed_tasks

def generate_study_tasks (agent, start, end):
    study_tasks = []
    courses = list(agent.get("tasks_by_course", {}).keys())

    if not courses:
        courses = list(agent.get("course_risk_weights", {}).keys())

    for course in courses:
        study_task = Task(
            id=str(uuid.uuid4()),
            course=course,
            title=f"Study {course}",
            assignment_type="Study",
            due=end,
            status="Open",
            created_at=start,
            completed_at=None,
            minutes_spent=None
        )
        study_tasks.append(study_task)
    return study_tasks

def find_free_blocks(busy_intervals, start, end):
    """
    Returns a list of (start, end) free intervals
    """
    tz_ref = start.tzinfo

    if start >= end:
        return []

    # 1) Clip to window and drop invalid/outside intervals
    clipped = []
    for b0, b1 in busy_intervals:

        b0 = b0.astimezone(tz_ref) if b0.tzinfo else b0.replace(tzinfo = tz_ref)
        b1 = b1.astimezone(tz_ref) if b1.tzinfo else b1.replace(tzinfo = tz_ref)

        if b0 is None or b1 is None:
            continue

        if b1 <= start or b0>= end:
            continue

        s = max(b0, start)
        e = min(b1, end)
        if s < e:
            clipped.append((s, e))

    if not clipped:
        return [(start, end)]

    # 2) Sort
    clipped.sort(key=lambda x: x[0])

    # 3) Merge overlaps/adjacent
    merged = []
    cur_s, cur_e = clipped[0]
    for s, e in clipped[1:]:
        if s <= cur_e:  # overlap or touch
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))

    # 4) Complement to get free blocks
    free = []
    cursor = start
    for s, e in merged:
        if cursor < s:
            free.append((cursor, s))
        cursor = max(cursor, e)

    # 5) Tail free block
    if cursor < end:
        free.append((cursor, end))

    return free

def ensure_aware(dt: datetime, tz_ref) -> datetime:
    """
    Make a datetime timezone-aware using tz_ref.
    If dt is naive, attach tz_ref. If aware, convert to tz_ref.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz_ref)
    return dt.astimezone(tz_ref)

def recommend_study_plan(state,start,end):
    """
    Input: agent_input
    Output: structured recommendations
    """
    "start and end must be datetime.datetime"
    tz_ref = start.tzinfo
    start = ensure_aware(start, tz_ref)
    end = ensure_aware(end, tz_ref)

    rec = {}
    rec["window"] = {"start" : start, "end": end}
    rec["free_blocks"] = find_free_blocks(state["busy_intervals"],start,end)

    open_tasks = return_open_tasks_by_course(state["tasks_by_course"])
    closed_tasks= return_closed_tasks_by_course(state["tasks_by_course"])
    open_tasks_flattened = flatten_tasks(open_tasks)

    study_tasks = generate_study_tasks(state, start, end)
    open_tasks_flattened.extend(study_tasks)

    scored_tasks = []
    for task in open_tasks_flattened:

        due = ensure_aware(task.due, tz_ref)

        if not(start <= due <= end):
            continue

        risk = state["course_risk_weights"].get(task.course, 0.0)
        s = score_task(task, risk, start, due, (end-start).days)

        if avg_time_spent_on_previous(closed_tasks,task.course,task.assignment_type)!= 0:
            est_min = avg_time_spent_on_previous(closed_tasks,task.course,task.assignment_type)
        elif "Project" in task.assignment_type or "Lab" in task.assignment_type:
            est_min = 150
        elif "Study" in task.assignment_type:
            if risk == 0:
                est_min = 25
                continue
            elif 1 <= risk <=10:
                est_min = 75
            elif 11 <= risk <= 20:
                est_min = 100
            elif 21 <= risk <= 30:
                est_min = 150
            elif risk >= 31:
                est_min = 200
        else:
            est_min = 60
        
        scored_tasks.append((s,est_min, due, task))

    ranked_tasks = sorted(scored_tasks, key=lambda x: (-x[0], x[2]))

    rec["ranked_tasks"] = ranked_tasks

    schedule = []
    explenations = []
    warnings = []
    free_blocks = find_free_blocks(state["busy_intervals"],start,end)
    remaining_mins = 0
    i=0

    for score, est_min, due, task in ranked_tasks:
        remaining_mins = est_min
        while(remaining_mins > 0) and i < len(free_blocks):
                start_time, end_time = free_blocks[i]

                reason = [] 

                risk = state["course_risk_weights"].get(task.course, 0.0)

                if risk > 0:
                    reason.append("High course risk")

                if (due - start).days <= 3:
                    reason.append("Due soon")

                if est_min > 120:
                    reason.append("Large workload")

                explanation_text = ", ".join(reason)

                block_mins = (end_time - start_time).total_seconds() /60

                if block_mins < MIN_STUDY_BLOCK:
                    i+=1
                    continue

                alloc = min(remaining_mins, block_mins, MAX_STUDY_BLOCK)
                if alloc < MIN_STUDY_BLOCK:
                    i+=1
                    continue

                session_end = start_time + timedelta(minutes=alloc)

                schedule.append({
                    "task_id": task.id,
                    "course": task.course,
                    "title": task.title,
                    "due": due,
                    "start": start_time,
                    "end": session_end,
                    "block_minutes": alloc,
                    "total_minutes": est_min,
                    "score": score
                    })
                
                explenations.append({
                    "task_id": task.id,
                    "reason": explanation_text,
                    "risk_weight": risk,
                    "score": score,
                    "estimated_minutes": est_min,
                    "allocated_minutes": alloc
                })  
                
                remaining_mins -= alloc

                if session_end < end_time:
                    free_blocks[i] = (session_end, end_time)  # leftover remains in same slot
                else:
                    i += 1

    rec["schedule"] = schedule
    rec["explenations"] = explenations

    if remaining_mins > 0:
        warnings.append({
            "code": "INSUFFICIENT_TIME",
            "severity": "high",
            "task_id": task.id,
            "course": task.course,
            "message": f"Could not fully schedule {task.title}",
            "details": {
                "unscheduled_minutes": remaining_mins
            }
        })

    minutes_until_due = int((due - start).total_seconds() / 60)

    if minutes_until_due < 24 * 60:
        warnings.append({
            "code": "DUE_SOON",
            "severity": "medium",
            "task_id": task.id,
            "course": task.course,
            "message": f"{task.title} is due within 24 hours.",
        })

    for course, risk in state["course_risk_weights"].items():
        if risk > 15:
            warnings.append({
                "code": "LOW_GRADE",
                "severity": "high",
                "course": course,
                "message": f"{course} grade is significantly below target."
            })

    if len(schedule) == 0:
        warnings.append({
            "code": "NO_STUDY_TIME",
            "severity": "high",
            "message": "No study time could be scheduled in this window."
        })

    rec["warnings"] = warnings

    return rec

