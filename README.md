# 🎓 EduSchedule — Automated Academic Timetable Generation & Management

> A Django web platform with a custom constraint-satisfaction scheduling engine that automatically generates clash-free weekly timetables for sections, lab batches and paired electives, with role-based dashboards for Admins, Faculty and Students.

---

## 📌 Overview

Every semester, someone in the department sits down with a spreadsheet and manually decides which teacher takes which subject, in which room, at which hour, for every section. It is tedious and error-prone. Labs, elective subjects and faculty leave make it messier, and a double-booked teacher or room is often only noticed when students show up.

Most scheduling tools stop at storing a timetable. Department admins need answers to practical questions:

- Can a complete, clash-free timetable be generated automatically?
- Why did a subject fail to get all its hours placed?
- Who can cover a class when a teacher is on leave?

**EduSchedule** addresses this by acting as an **academic scheduling system** that:

- **Generates** a full weekly timetable for every section with one click
- **Validates** the result and rolls back automatically if any rule is broken
- **Guides** admins with a readable generation log and automatic leave substitution

---

## ✨ Key Features

- 🤖 **Auto-Generated Timetables** — three-pass scheduling engine for labs, electives and theory
- 🧪 **Self-Validating** — every generation is checked and rolled back inside a database transaction on any violation
- 🔬 **Lab Batch Support** — 2-hour lab blocks with both batches scheduled simultaneously in different rooms
- 🔀 **Paired Electives** — electives in the same group run at the same time and display as one merged cell (e.g. `Cloud Security / NLP`)
- 🔄 **Automatic Leave Substitution** — approved leave triggers least-loaded qualified substitute assignment per affected class
- 🔐 **Role-Based Access** — one login page, separate Admin / Faculty / Student dashboards
- 📄 **PDF Export** — print-ready timetables with breaks and lunch marked, built with ReportLab
- 📋 **Visible Generation Log** — colour-coded success/failure log on the admin dashboard, with "X/Y hours placed" per subject

### 👥 Dashboards by Role

| Role | What they can do |
|------|------------------|
| **Admin** | Live counts (faculty, subjects, sections, rooms), one-click generation with expandable log, leave approval queue, full timetable browser, PDF export |
| **Faculty** | Live "Currently Teaching" card, today's schedule, weekly timetable, availability badge, leave requests with status history |
| **Student** | Current/next class card, "Coming Up Today" list, batch-aware weekly grid, searchable faculty directory, PDF export |

---

## 🏗️ System Architecture

```
Login Page
    ↓
Role-based redirect (Admin / Faculty / Student)
    ↓
Admin clicks "Generate Timetable"
    ↓
Django view calls the scheduling engine
    ↓
Pass 1: Labs  →  Pass 2: Electives  →  Pass 3: Theory
(in-memory ConflictTracker checks every placement)
    ↓
validate_timetable() re-checks every generated row
    ↓
Valid → commit    |    Violation → full rollback
    ↓
Dashboard shows timetable + generation log
```

---

## 🧰 Technology Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python 3, Django 6 |
| Database | MySQL (Django ORM) |
| Authentication | Django auth with custom `AbstractUser` (role: ADMIN / FACULTY / STUDENT) |
| Scheduling Logic | Pure Python, in-memory conflict tracking, `transaction.atomic()` |
| PDF Export | ReportLab |
| Excel Export | openpyxl *(scaffolded)* |
| Frontend | Django Templates, HTML, CSS, vanilla JavaScript |
| Deployment Prep | Gunicorn, WhiteNoise |

---

## 📂 Project Structure

```
EduSchedule/
│
├── backend/                  # Django project settings & root URLs
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── schedular/                # Core app: models, engine, views
│   ├── models.py             # 12 models (User, Faculty, Subject, Schedule, ...)
│   ├── engine.py             # Scheduling engine + validator
│   ├── views.py              # Auth, dashboards, leave workflow, PDF export
│   ├── urls.py
│   ├── admin.py
│   ├── seed_demo.py          # Small demo dataset
│   └── migrations/
│
├── templates/schedular/      # HTML templates
│   ├── login.html
│   ├── base.html
│   ├── admin.html
│   ├── faculty.html
│   ├── student.html
│   ├── faculty_timetable.html
│   ├── all_faculty_timetables.html
│   └── faculty_schedule_by_day.html
│
├── static/
│   └── css/shared.css        # Shared design system
│
├── seed_data.py              # Seeder modelled on a real CSE department timetable
├── manage.py
├── requirements.txt
└── README.md
```

---

## 📊 Data & Seeding

The project ships with two seed datasets so it runs with no manual data entry:

| Seeder | Purpose |
|--------|---------|
| `schedular/seed_demo.py` | Small demo dataset: departments, sections, faculty, subjects, rooms, time slots and demo login users |
| `seed_data.py` | Realistic dataset modelled on a real CSE department timetable (two sections, real subject and elective structure) used to stress-test the engine |

**Core entities:**

| Model | Purpose |
|-------|---------|
| `Department`, `Semester`, `Section`, `Batch` | Academic hierarchy; batches are lab sub-groups |
| `Faculty` | Name, email, weekly `workload_limit` |
| `Subject` | `weekly_hours`, `is_lab`, `is_elective`, `elective_group` |
| `FacultySubject` | Which faculty can teach which subjects |
| `FacultyLeave` | Leave requests (date, reason, approved / rejected) |
| `Room`, `TimeSlot` | Rooms (lab or classroom) and day + slot combinations |
| `Schedule` | The generated timetable rows. `date = NULL` is the recurring template; a set date is a one-off substitution |

---

## ⚙️ Scheduling Engine

The engine (`schedular/engine.py`) is a **greedy, multi-pass heuristic** with a strict validation safety net.

**Why three ordered passes?**
- **Labs first** — the most constrained (consecutive slots, lab rooms, two-batch handling)
- **Electives second** — need paired placement in the same slot across different rooms and faculty
- **Theory last** — the most flexible, fills the remaining slots

**In-memory `ConflictTracker`**
- Sets of `(id, day, slot)` tuples for faculty, rooms, sections and batches give **O(1)** clash checks
- Avoids a database round-trip for every candidate slot
- Also tracks per-day subject counts and per-faculty workload

**Validate and roll back**
- `validate_timetable()` checks faculty, room and batch clashes, subjects repeated more than twice a day, and illegitimate section overlaps
- Any violation raises an exception inside `transaction.atomic()`, undoing the entire run

---

## 📋 Scheduling Rules Enforced

| Rule | How it is enforced |
|------|--------------------|
| No faculty / room / section / batch double-booking | `ConflictTracker` sets, re-verified by `validate_timetable()` |
| Labs run as 2 consecutive slots | Lab pass places paired slots only |
| Two-batch labs run simultaneously | Both batches' room, faculty and batch constraints must pass together before commit |
| Electives in a group run together | Same `(day, slot)`, different rooms and faculty, linked by `elective_pair` |
| Max 2 sessions of a subject per day | Daily cap re-checked on every slot iteration |
| Weekly faculty workload limit | Per-faculty counter against `workload_limit` |
| Approved leave dates respected | Dated substitution rows created without touching the weekly template |

---

## 🔑 Running Locally

**Prerequisites:** Python 3.10+, MySQL server, Git

```bash
# 1. Clone the repository
git clone https://github.com/Naveena-Sahukari/EduSchedule.git
cd EduSchedule

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt
```

```sql
-- 4. Create the MySQL database
CREATE DATABASE intellisched CHARACTER SET utf8mb4;
```

```powershell
# 5. Set environment variables (Windows PowerShell)
$env:DB_PASSWORD="your-mysql-password"
$env:SECRET_KEY="your-secret-key"
# macOS / Linux: export DB_PASSWORD="..." and export SECRET_KEY="..."
```

```bash
# 6. Apply migrations
python manage.py migrate

# 7. Load demo data (creates sections, faculty, subjects, rooms, slots, demo users)
python seed_data.py

# 8. Start the server
python manage.py runserver
```

Open http://127.0.0.1:8000/, log in with a demo user from the seed script, and click **Generate Timetable** on the admin dashboard.

### 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-only-insecure-key` | Django secret key. Set your own in production |
| `DEBUG` | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated host list |
| `DB_NAME` | `intellisched` | MySQL database name |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | *(empty)* | MySQL password |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |

---

## 💡 Key Engineering Highlights

- **Ordering matters** — scheduling the most constrained subjects first greatly reduces failed placements
- **Validation needs intent** — the validator treats two overlapping rows as legitimate only if they are different subjects, different faculty and linked as an elective pair
- **Check placement inside loops** — the daily-cap rule had to be re-evaluated on every slot iteration, not once per day
- **Resource supply matters** — a placement failure can be a data problem (too few rooms), not an algorithm bug
- **Failures should be visible** — surfacing the generation log in the UI makes the system self-explanatory to non-technical staff

---

## ⚠️ Limitations

- The engine is a **greedy heuristic**, not an optimal solver. If room or faculty supply runs out, some sessions may not be placed (the log reports exactly how many hours were placed)
- No automated test suite yet; `tests.py` is the Django stub
- Excel export is scaffolded but not enabled
- Seeded data only; not currently deployed for real departmental use

---

## 🔮 Future Improvements

- Automated unit tests for the scheduling engine
- Finish the Excel export
- Constraint-solver based scheduling (e.g. Google OR-Tools CP-SAT) for feasibility guarantees
- Production deployment with Gunicorn, WhiteNoise and hosted MySQL
- Timetable change requests and notifications for faculty and students

---

## 👩‍💻 Author

**Naveena Sahukari**
Full-Stack Development | Machine Learning
GitHub: [@Naveena-Sahukari](https://github.com/Naveena-Sahukari)

---

## 📢 Disclaimer

This project was built for academic and educational purposes using seeded data modelled on a real department timetable. It is a prototype scheduling system and is not intended as a production institutional system.
