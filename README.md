# AI Study Planner Agent

An intelligent academic planning system that dynamically generates prioritized study schedules using grade-based risk modeling, deadline urgency scoring, and real-time calendar availability.

This project automates study planning by combining academic performance analytics with constraint-based scheduling.

---

## Overview

The AI Study Planner Agent:

- Analyzes current course grades  
- Computes risk weights per course  
- Ingests assignment tasks from CSV  
- Integrates iCloud calendar events  
- Identifies available study time  
- Scores tasks by urgency and academic risk  
- Allocates structured study blocks  
- Generates schedule recommendations and warnings  

The result is a dynamically generated, prioritized study plan within a user-defined time window.

---

## System Architecture

### agent.py
Core scheduling engine:
- Validates agent input schema  
- Scores tasks using urgency and course risk  
- Estimates workload using historical data  
- Merges busy intervals  
- Allocates study blocks using minimum and maximum constraints  
- Produces structured schedule output  

### task_reader.py
- Reads task data from CSV files  
- Parses ISO and formatted datetimes  
- Tracks minutes spent  
- Computes historical averages by assignment type  

### course_reader.py
- Computes weighted course grades from CSV category data  
- Derives risk weights based on target grade threshold  
- Normalizes grade representations  

### calendar_reader.py
- Pulls calendar events via iCloud  
- Converts date arrays into timezone-aware datetimes  
- Builds busy intervals  
- Generates sleep intervals  
- Merges overlapping time blocks  

### icloud_auth.py
- Secure Apple ID login  
- Handles 2FA validation  
- Establishes trusted session  

### main.ipynb
Interactive orchestration layer:
- Loads semester data  
- Authenticates iCloud  
- Builds agent state  
- Runs recommendation engine  
- Displays structured output  

---

## Task Scoring Logic

Each task is scored using:

```
Score = Urgency + Risk Influence
```

Where:

- Urgency is derived from time remaining until due date  
- Risk is computed from how far current course grade is below target  
- Tasks outside the scheduling window are excluded  
- Completed tasks are ignored  

Higher score indicates higher scheduling priority.

---

## Risk Weighting Model

Course risk is computed as:

```
Risk Weight = max(0, TargetGrade - CurrentGrade)
```

If all courses meet or exceed target, equal weights are assigned.

This ensures:
- Lower-performing courses receive more study allocation  
- Academic weaknesses drive prioritization  

---

## Scheduling Engine

The scheduler:

1. Collects busy intervals (calendar and sleep).  
2. Computes free time blocks.  
3. Sorts tasks by priority.  
4. Allocates study sessions using:
   - Minimum block size  
   - Maximum block size  
   - Estimated workload  
5. Generates warnings if:
   - Insufficient time  
   - Due soon (less than 24 hours)  
   - High-risk courses  
   - No available study time  

The engine guarantees timezone-safe datetime handling.

---

## Key Technical Features

- Timezone-aware datetime normalization  
- Interval merging and complement computation  
- Constraint-based allocation  
- Historical workload estimation  
- CSV-based persistent storage  
- Modular agent architecture  
- Defensive input validation  

---


## Requirements

```
pyicloud
ipywidgets
python-dateutil
```

Install with:

```
pip install -r requirements.txt
```

---

## Security Note

This project does not store credentials.  
Apple ID authentication is handled securely via pyicloud with two-factor authentication validation.

Sensitive environment files should not be committed.

---

## Purpose

This project demonstrates:

- Applied AI decision modeling  
- Heuristic prioritization systems  
- Constraint-based scheduling  
- Academic analytics integration  
- Real-world calendar API usage  
- Production-style modular design  

It is intended as both a functional tool and a portfolio-level software engineering artifact.

---

## Future Improvements

- Reinforcement-based time estimation  
- Adaptive risk thresholding  
- Web interface  
- Calendar write-back integration  
- Machine-learned task duration prediction  
