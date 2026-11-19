# seed_data_all_years.py
# Generated from VCE CSE Dept Timetables, AY 2026-2027 — ALL 9 SECTIONS:
#   B.Tech II Year I Sem  (Semester 3): CSE-A, CSE-B, CSE-C
#   B.Tech III Year I Sem (Semester 5): CSE-A, CSE-B, CSE-C
#   B.Tech IV Year I Sem  (Semester 7): CSE-A, CSE-B, CSE-C
#
# NOTES / assumptions worth knowing before you run this:
#
# 1. weekly_hours for LAB subjects is cosmetic. engine.py's schedule_labs()
#    pairs up a section's lab subjects two-at-a-time in DB-insertion order
#    and gives each pair exactly one 2-hour block per week, regardless of
#    weekly_hours. The real timetables rotate which two labs are paired
#    across the week (e.g. OSL/DBL one day, DBL/OOL another) — the engine's
#    simpler one-fixed-pair-per-week model can't fully reproduce that, so
#    don't expect a byte-for-byte match to the PDF for lab placement.
#
# 2. schedule_electives() only runs for semester.number >= 5, and only pairs
#    exactly 2 subjects per elective_group (extra subjects in a group are
#    ignored). Semester 5's real timetable shows THREE simultaneous PE-I
#    options in some sections (UML / EHG / DSE). Since the engine can't pair
#    three-way, UML is seeded as a normal theory subject (like Fundamentals
#    of Robotics in Sem 7) and EHG+DSE are the paired elective_group.
#
# 3. Subject.weekly_hours values below are calibrated to fill each section's
#    week (6 days x 7 slots = 42) without exceeding the engine's 2-sessions/
#    day cap — they are NOT literal grid-cell counts from the PDF (the PDF's
#    batch-rotating lab cells don't map 1:1 onto a single weekly_hours field
#    anyway). Adjust in /admin if you see gaps after generating.
#
# Run using:
#   python manage.py shell -c "exec(open('seed_data_all_years.py').read())"
# or (PowerShell):
#   Get-Content seed_data_all_years.py | python manage.py shell

from schedular.models import *

# ----------------------------------------------------
# CLEAR OLD DATA
# ----------------------------------------------------
Schedule.objects.all().delete()
FacultySubject.objects.all().delete()
FacultyLeave.objects.all().delete()
Batch.objects.all().delete()
Subject.objects.all().delete()
Faculty.objects.all().delete()
Section.objects.all().delete()
Semester.objects.all().delete()
Room.objects.all().delete()
TimeSlot.objects.all().delete()
Department.objects.all().delete()

# ----------------------------------------------------
# DEPARTMENT
# ----------------------------------------------------
cse_dept = Department.objects.create(name="Computer Science and Engineering")

# ----------------------------------------------------
# SEMESTERS
# ----------------------------------------------------
sem3 = Semester.objects.create(number=3, department=cse_dept)   # II Year I Sem
sem5 = Semester.objects.create(number=5, department=cse_dept)   # III Year I Sem
sem7 = Semester.objects.create(number=7, department=cse_dept)   # IV Year I Sem

# ----------------------------------------------------
# SECTIONS
# ----------------------------------------------------
ii_a = Section.objects.create(name="CSE-A", semester=sem3)
ii_b = Section.objects.create(name="CSE-B", semester=sem3)
ii_c = Section.objects.create(name="CSE-C", semester=sem3)

iii_a = Section.objects.create(name="CSE-A", semester=sem5)
iii_b = Section.objects.create(name="CSE-B", semester=sem5)
iii_c = Section.objects.create(name="CSE-C", semester=sem5)

iv_a = Section.objects.create(name="CSE-A", semester=sem7)
iv_b = Section.objects.create(name="CSE-B", semester=sem7)
iv_c = Section.objects.create(name="CSE-C", semester=sem7)

ALL_SECTIONS = [ii_a, ii_b, ii_c, iii_a, iii_b, iii_c, iv_a, iv_b, iv_c]

# ----------------------------------------------------
# BATCHES (2 per section, for lab sessions)
# ----------------------------------------------------
for section in ALL_SECTIONS:
    Batch.objects.create(name="Batch-1", section=section)
    Batch.objects.create(name="Batch-2", section=section)

# ----------------------------------------------------
# ROOMS
# Home classroom per section (per the PDF's "Room No:" header), one overflow
# classroom per year (for elective pairs / general slack), and shared lab
# rooms named after their actual lab room numbers.
# ----------------------------------------------------
room_1210 = Room.objects.create(name="1210", is_lab=False)   # II-A classroom
room_1211 = Room.objects.create(name="1211", is_lab=False)   # II-B classroom
room_1212 = Room.objects.create(name="1212", is_lab=False)   # II-C classroom
room_1213 = Room.objects.create(name="1213", is_lab=False)   # II-year overflow

room_1119 = Room.objects.create(name="1119", is_lab=False)   # III-A classroom
room_1120 = Room.objects.create(name="1120", is_lab=False)   # III-B classroom
room_1121 = Room.objects.create(name="1121", is_lab=False)   # III-C classroom
room_1122 = Room.objects.create(name="1122", is_lab=False)   # III-year overflow

room_1002 = Room.objects.create(name="1002", is_lab=False)   # IV-A classroom
room_1003 = Room.objects.create(name="1003", is_lab=False)   # IV-B classroom
room_1103 = Room.objects.create(name="1103", is_lab=False)   # IV-C classroom
room_1004 = Room.objects.create(name="1004", is_lab=False)   # IV-year overflow
room_1005 = Room.objects.create(name="1005", is_lab=False)   # IV-year overflow
room_1104 = Room.objects.create(name="1104", is_lab=False)   # IV-year overflow

lab_1208 = Room.objects.create(name="1208", is_lab=True)     # II-year OSL/PPL
lab_1102 = Room.objects.create(name="1102", is_lab=True)     # II-year DBL
lab_1204 = Room.objects.create(name="1204", is_lab=True)     # II-year OOL

lab_1201 = Room.objects.create(name="1201", is_lab=True)     # III-year WTL
lab_1101 = Room.objects.create(name="1101", is_lab=True)     # III-year MAD
lab_5105 = Room.objects.create(name="5105", is_lab=True)     # III-year ACS language lab

lab_1202 = Room.objects.create(name="1202", is_lab=True)     # III MLL / IV DML
lab_1203 = Room.objects.create(name="1203", is_lab=True)     # III MLL / IV BDL

# ----------------------------------------------------
# TIMESLOTS — 7 periods per day, 6 days = 42 slots/week (shared by all years)
# ----------------------------------------------------
days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
for day in days:
    for slot in range(1, 8):
        TimeSlot.objects.create(day=day, slot_number=slot)

# ----------------------------------------------------
# FACULTY (every instructor + mentor appearing across all 9 timetables,
# deduplicated by person — many teach the same subject across sections,
# or across different years).
# ----------------------------------------------------
FACULTY_ROSTER = [
    ("Mrs. S. Archana", "sarchana@vardhaman.org"),
    ("Ms. D. Dhana Lakshmi", "ddhanalakshmi@vardhaman.org"),
    ("Ms. C. Kavitha", "ckavitha@vardhaman.org"),
    ("Ms. Shaik Shahanaz", "sshahanaz@vardhaman.org"),
    ("Mr. K. Hari Babu", "khbabu@vardhaman.org"),
    ("Ms. C. Bhavana", "cbhavana@vardhaman.org"),
    ("Mr. V N S Vijay Kumar", "vvijaykumar@vardhaman.org"),
    ("Mrs. P S Madhavi", "psmadhavi@vardhaman.org"),
    ("Dr. V. Lokeshwari Vinya", "vlokeshwarivinya@vardhaman.org"),
    ("Mrs. D Suguna Devi", "dsugunadevi@vardhaman.org"),
    ("Mr. K Akshay Kumar", "kakshaykumar@vardhaman.org"),
    ("Ms. M. Sowmya", "msowmya@vardhaman.org"),
    ("Ms. Julia Devaradhi", "jdevaradhi@vardhaman.org"),
    ("Mr. M. Sambaraj", "msambaraj@vardhaman.org"),
    ("Dr. J. Naga Padmaja", "jnagapadmaja@vardhaman.org"),
    ("Ms. K. Shalini", "kshalini@vardhaman.org"),
    ("Ms. M. Radhika", "mradhika@vardhaman.org"),
    ("Mr. G S Prasada Reddy", "gsprasadareddy@vardhaman.org"),
    ("Mr. C. Satya Kumar", "csatyakumar@vardhaman.org"),
    ("Mr. B. Vivekananda", "bvivekananda@vardhaman.org"),
    ("Mr. M. Raghavendra", "mraghavendra@vardhaman.org"),
    ("Dr. Bhakti Shrinivas Natoo", "bnatoo@vardhaman.org"),
    ("Mr. Tamal Sau", "tsau@vardhaman.org"),
    ("Ms. B. Anjali", "banjali@vardhaman.org"),
    ("Ms. AD Rani Sirisha", "adranisirisha@vardhaman.org"),
    ("Dr. Sailaja Pennabadi", "spennabadi@vardhaman.org"),
    ("Mr. M. Manohar Samson", "mmanoharsamson@vardhaman.org"),
    ("Dr. S. Venu Gopal", "svenugopal@vardhaman.org"),
    ("Dr. Raghavendra Gouda", "rgouda@vardhaman.org"),
    ("Mr. Gireesh K Agarwal", "gagarwal@vardhaman.org"),
    ("Mr. S. Surendhar", "ssurendhar@vardhaman.org"),
    ("Mr. B J V Varma", "bjvvarma@vardhaman.org"),
    ("Dr. V Parvathi", "vparvathi@vardhaman.org"),
    ("Ms. Antara Ghosh", "aghosh@vardhaman.org"),
    ("Dr. R Srikanth", "rsrikanth@vardhaman.org"),
    ("Mr. A. Bhanu Prasad", "abhanuprasad@vardhaman.org"),
    ("Mrs. A Ashwini", "aashwini@vardhaman.org"),
    ("Ms. Syeda Fatima Farheen", "sfarheen@vardhaman.org"),
    ("Mr. D. Ganesh", "dganesh@vardhaman.org"),
    ("Dr. Ramesh Karnati", "rkarnati@vardhaman.org"),
    ("Ms. Anaswara Ramachandran", "aramachandran@vardhaman.org"),
    ("Dr. Reddy Saisindhu Teja", "rsaisindhuteja@vardhaman.org"),
    ("Dr. Gouse Baig Mohammad", "gbaigmohammad@vardhaman.org"),
    ("Dr. P. Venkateshwar Reddy", "pvenkateshwarreddy@vardhaman.org"),
    ("Dr. K. Deepak", "kdeepak@vardhaman.org"),
    ("Dr. S. Thirupati", "sthirupati@vardhaman.org"),
    ("Ms. B. Vaishnavi", "bvaishnavi@vardhaman.org"),
    ("Mr. K. Santhosh Reddy", "ksanthoshreddy@vardhaman.org"),
    ("Dr. Ramesh Gade", "rgade@vardhaman.org"),
    ("Ms. K. Saritha", "ksaritha@vardhaman.org"),
    ("Ms. P. Keerthi", "pkeerthi@vardhaman.org"),
    ("Mr. V. Narender", "vnarender@vardhaman.org"),
    ("Dr. S. Sashi Devi", "ssashidevi@vardhaman.org"),
    ("Mr. G. Rajashekhar", "grajashekhar@vardhaman.org"),
]

F = {}
for name, email in FACULTY_ROSTER:
    F[name] = Faculty.objects.create(name=name, email=email, workload_limit=24)


def link(fac_name, subject):
    """Shorthand to create a FacultySubject mapping by faculty full name."""
    FacultySubject.objects.get_or_create(faculty=F[fac_name], subject=subject)


# ----------------------------------------------------
# SUBJECTS — SEMESTER 3 (II Year I Sem)
# No electives at this level (engine only runs schedule_electives() for
# semester.number >= 5), so all subjects here are plain theory or lab.
# ----------------------------------------------------
bef = Subject.objects.create(name="Business Economics and Financial Analysis", semester=sem3, weekly_hours=4)
dms = Subject.objects.create(name="Discrete Mathematical Structures", semester=sem3, weekly_hours=4)
oss = Subject.objects.create(name="Operating Systems", semester=sem3, weekly_hours=4)
dbm = Subject.objects.create(name="Data Base Management System", semester=sem3, weekly_hours=4)
oop = Subject.objects.create(name="Object Oriented Programming through JAVA", semester=sem3, weekly_hours=4)
dav = Subject.objects.create(name="Data Analysis and Visualization using Power BI", semester=sem3, weekly_hours=2)
tep = Subject.objects.create(name="Technology Entrepreneurship", semester=sem3, weekly_hours=2)
vas = Subject.objects.create(name="Verbal Ability & Soft Skills", semester=sem3, weekly_hours=2)
ars = Subject.objects.create(name="Aptitude and Reasoning Skills", semester=sem3, weekly_hours=2)
vac3 = Subject.objects.create(name="GitHub Copilot (Value Added Course)", semester=sem3, weekly_hours=2)

osl = Subject.objects.create(name="Operating Systems Laboratory", semester=sem3, weekly_hours=2, is_lab=True)
dbl = Subject.objects.create(name="Data Base Management System Laboratory", semester=sem3, weekly_hours=2, is_lab=True)
ool = Subject.objects.create(name="OOP through JAVA Laboratory", semester=sem3, weekly_hours=2, is_lab=True)
ppl = Subject.objects.create(name="Python Programming Laboratory", semester=sem3, weekly_hours=2, is_lab=True)

# ----------------------------------------------------
# SUBJECTS — SEMESTER 5 (III Year I Sem)
# ----------------------------------------------------
cns = Subject.objects.create(name="Computer Networks", semester=sem5, weekly_hours=4)
seg = Subject.objects.create(name="Software Engineering", semester=sem5, weekly_hours=4)
wts = Subject.objects.create(name="Web Technologies", semester=sem5, weekly_hours=4)
mlg = Subject.objects.create(name="Machine Learning", semester=sem5, weekly_hours=4)
rmy = Subject.objects.create(name="Research Methodology", semester=sem5, weekly_hours=3)
fwe = Subject.objects.create(name="Full Stack Web Engineering (Value Added Course)", semester=sem5, weekly_hours=2)
lsm5 = Subject.objects.create(name="Library/Sports/Mentoring", semester=sem5, weekly_hours=4)

# UML has no elective partner in the real timetable's 3-way PE-I slot, so it
# is seeded as normal theory (same treatment as Fundamentals of Robotics
# in Sem 7) rather than left as an unpairable elective.
uml = Subject.objects.create(name="Unified Modeling Language", semester=sem5, weekly_hours=3)

# Elective pair PE-I -> group 1: Ethical Hacking / Data Science for Engineers
ehg = Subject.objects.create(
    name="Ethical Hacking", semester=sem5, weekly_hours=3, is_elective=True, elective_group=1
)
dse = Subject.objects.create(
    name="Data Science for Engineers", semester=sem5, weekly_hours=3, is_elective=True, elective_group=1
)

wtl = Subject.objects.create(name="Web Technologies Laboratory", semester=sem5, weekly_hours=2, is_lab=True)
mll = Subject.objects.create(name="Machine Learning Laboratory", semester=sem5, weekly_hours=2, is_lab=True)
mad = Subject.objects.create(name="Mobile Application Development", semester=sem5, weekly_hours=2, is_lab=True)
acs = Subject.objects.create(name="Advanced English Communication Skills Laboratory", semester=sem5, weekly_hours=2, is_lab=True)

# ----------------------------------------------------
# SUBJECTS — SEMESTER 7 (IV Year I Sem)
# ----------------------------------------------------
dmg = Subject.objects.create(name="Data Mining", semester=sem7, weekly_hours=6)
bda = Subject.objects.create(name="Big Data Analytics", semester=sem7, weekly_hours=5)

csy = Subject.objects.create(
    name="Cloud Security", semester=sem7, weekly_hours=3, is_elective=True, elective_group=1
)
nlp = Subject.objects.create(
    name="Natural Language Processing", semester=sem7, weekly_hours=3, is_elective=True, elective_group=1
)
isy = Subject.objects.create(
    name="IoT Security", semester=sem7, weekly_hours=3, is_elective=True, elective_group=2
)
wsa = Subject.objects.create(
    name="Web and Social Media Analytics", semester=sem7, weekly_hours=3, is_elective=True, elective_group=2
)

fora = Subject.objects.create(name="Fundamentals of Robotics", semester=sem7, weekly_hours=2)

dml = Subject.objects.create(name="Data Mining Laboratory", semester=sem7, weekly_hours=2, is_lab=True)
bdl = Subject.objects.create(name="Big Data Analytics Laboratory", semester=sem7, weekly_hours=2, is_lab=True)

pwp = Subject.objects.create(name="Project Work Phase-I", semester=sem7, weekly_hours=12)
dtt = Subject.objects.create(name="Devops Tools and Techniques", semester=sem7, weekly_hours=3)
lsm7 = Subject.objects.create(name="Library/Sports/Mentoring", semester=sem7, weekly_hours=6)

# ======================================================================
# FACULTY MAPPINGS
# ======================================================================

# ---------------- II Year CSE-A (Room 1210) ----------------
link("Mrs. S. Archana", bef)
link("Ms. D. Dhana Lakshmi", dms)
link("Ms. C. Kavitha", oss)
link("Ms. Shaik Shahanaz", dbm)
link("Mr. K. Hari Babu", oop)
link("Ms. C. Kavitha", osl); link("Ms. C. Bhavana", osl)
link("Ms. Shaik Shahanaz", dbl); link("Mr. V N S Vijay Kumar", dbl)
link("Mr. K. Hari Babu", ool); link("Mrs. P S Madhavi", ool)
link("Dr. V. Lokeshwari Vinya", ppl); link("Mrs. D Suguna Devi", ppl)
link("Mr. K Akshay Kumar", dav)
link("Ms. M. Sowmya", tep)
link("Ms. Julia Devaradhi", vas)
link("Mr. M. Sambaraj", ars)
link("Mrs. D Suguna Devi", vac3)

# ---------------- II Year CSE-B (Room 1211) ----------------
link("Mrs. S. Archana", bef)
link("Mr. V N S Vijay Kumar", dms)
link("Ms. C. Kavitha", oss)
link("Mr. G S Prasada Reddy", dbm)
link("Dr. J. Naga Padmaja", oop)
link("Ms. C. Kavitha", osl); link("Dr. V. Lokeshwari Vinya", osl)
link("Mr. G S Prasada Reddy", dbl); link("Mr. C. Satya Kumar", dbl)
link("Dr. J. Naga Padmaja", ool); link("Ms. M. Radhika", ool)
link("Mrs. P S Madhavi", ppl); link("Mrs. D Suguna Devi", ppl)
link("Mr. K Akshay Kumar", dav)
link("Ms. M. Sowmya", tep)
link("Mr. B. Vivekananda", vas)
link("Mr. M. Sambaraj", ars)
link("Ms. Shaik Shahanaz", vac3)

# ---------------- II Year CSE-C (Room 1212) ----------------
link("Mrs. S. Archana", bef)
link("Mr. V N S Vijay Kumar", dms)
link("Ms. C. Bhavana", oss)
link("Dr. J. Naga Padmaja", dbm)
link("Ms. B. Anjali", oop)
link("Ms. C. Bhavana", osl); link("Mr. K Akshay Kumar", osl)
link("Dr. J. Naga Padmaja", dbl); link("Mr. V N S Vijay Kumar", dbl)
link("Ms. B. Anjali", ool); link("Mrs. P S Madhavi", ool)
link("Dr. V. Lokeshwari Vinya", ppl); link("Mr. K Akshay Kumar", ppl)
link("Mr. K Akshay Kumar", dav)
link("Ms. AD Rani Sirisha", tep)
link("Ms. Julia Devaradhi", vas)
link("Mr. M. Sambaraj", ars)
link("Ms. Shaik Shahanaz", vac3)

# ---------------- III Year CSE-A (Room 1119) ----------------
link("Ms. C. Bhavana", cns)
link("Dr. S. Venu Gopal", seg)
link("Ms. K. Shalini", wts)
link("Dr. Raghavendra Gouda", mlg)
link("Mr. Gireesh K Agarwal", ehg)
link("Ms. Shaik Shahanaz", dse)
link("Ms. K. Shalini", wtl); link("Mrs. P S Madhavi", wtl)
link("Dr. Raghavendra Gouda", mll); link("Mr. S. Surendhar", mll)
link("Mr. B J V Varma", mad); link("Mr. K. Hari Babu", mad)
link("Dr. V Parvathi", acs); link("Ms. Antara Ghosh", acs)
link("Dr. R Srikanth", rmy)
link("Ms. B. Anjali", fwe)
link("Ms. K. Shalini", lsm5)

# ---------------- III Year CSE-B (Room 1120) ----------------
link("Dr. V. Lokeshwari Vinya", cns)
link("Dr. S. Venu Gopal", seg)
link("Ms. K. Shalini", wts)
link("Mr. S. Surendhar", mlg)
link("Mrs. A Ashwini", uml)
link("Mr. Gireesh K Agarwal", ehg)
link("Ms. M. Radhika", dse)
link("Ms. K. Shalini", wtl); link("Mr. K. Hari Babu", wtl)
link("Mr. S. Surendhar", mll); link("Dr. Raghavendra Gouda", mll)
link("Mr. K. Hari Babu", mad); link("Ms. K. Shalini", mad)
link("Dr. Bhakti Shrinivas Natoo", acs); link("Ms. Syeda Fatima Farheen", acs)
link("Dr. J. Naga Padmaja", rmy)
link("Ms. C. Kavitha", fwe)
link("Mr. S. Surendhar", lsm5)

# ---------------- III Year CSE-C (Room 1121) ----------------
link("Dr. R Srikanth", cns)
link("Mrs. D Suguna Devi", seg)
link("Mr. G S Prasada Reddy", wts)
link("Mr. A. Bhanu Prasad", mlg)
link("Mrs. A Ashwini", uml)
link("Mr. Gireesh K Agarwal", ehg)
link("Mr. S. Surendhar", dse)
link("Mr. G S Prasada Reddy", wtl); link("Ms. K. Shalini", wtl)
link("Mr. A. Bhanu Prasad", mll); link("Mrs. D Suguna Devi", mll)
link("Ms. B. Anjali", mad); link("Ms. D. Dhana Lakshmi", mad)
link("Ms. Syeda Fatima Farheen", acs); link("Ms. Anaswara Ramachandran", acs)
link("Dr. Raghavendra Gouda", rmy)
link("Mr. M. Manohar Samson", fwe)
link("Mr. G S Prasada Reddy", lsm5)

# ---------------- IV Year CSE-A (Room 1002) ----------------
link("Dr. R Srikanth", dmg)
link("Ms. D. Dhana Lakshmi", bda)
link("Ms. B. Vaishnavi", csy)
link("Mr. S. Surendhar", nlp)
link("Dr. Gouse Baig Mohammad", isy)
link("Dr. Ramesh Karnati", wsa)
link("Dr. P. Venkateshwar Reddy", fora)
link("Dr. R Srikanth", dml); link("Mr. A. Bhanu Prasad", dml)
link("Ms. D. Dhana Lakshmi", bdl); link("Mr. K Akshay Kumar", bdl)
link("Dr. R Srikanth", pwp)
link("Mr. K. Hari Babu", dtt)
link("Dr. R Srikanth", lsm7)

# ---------------- IV Year CSE-B (Room 1003) ----------------
link("Ms. M. Radhika", dmg)
link("Mr. B J V Varma", bda)
link("Ms. B. Vaishnavi", csy)
link("Mr. S. Surendhar", nlp)
link("Dr. Gouse Baig Mohammad", isy)
link("Dr. Ramesh Karnati", wsa)
link("Dr. K. Deepak", fora)
link("Ms. M. Radhika", dml); link("Mr. C. Satya Kumar", dml)
link("Mr. B J V Varma", bdl); link("Ms. M. Radhika", bdl)
link("Dr. Raghavendra Gouda", pwp)
link("Mr. K. Hari Babu", dtt)
link("Dr. Raghavendra Gouda", lsm7)

# ---------------- IV Year CSE-C (Room 1103) ----------------
link("Mr. A. Bhanu Prasad", dmg)
link("Mr. B J V Varma", bda)
link("Ms. B. Vaishnavi", csy)
link("Dr. Raghavendra Gouda", nlp)
link("Dr. Gouse Baig Mohammad", isy)
link("Mrs. P S Madhavi", wsa)
link("Dr. S. Thirupati", fora)
link("Mr. A. Bhanu Prasad", dml); link("Dr. R Srikanth", dml)
link("Mr. B J V Varma", bdl); link("Ms. C. Kavitha", bdl)
link("Mr. B J V Varma", pwp)
link("Ms. D. Dhana Lakshmi", dtt)
link("Mr. B J V Varma", lsm7)

# ----------------------------------------------------
# MENTOR-ONLY FACULTY (appear on timetables as class mentors, not tied to
# a subject — added so they exist in the Faculty table for reference/leave
# tracking even though they have no FacultySubject rows).
# ----------------------------------------------------
MENTOR_ONLY_NAMES = [
    "Mr. M. Raghavendra", "Dr. Bhakti Shrinivas Natoo", "Mr. Tamal Sau",
    "Dr. Sailaja Pennabadi", "Mr. M. Manohar Samson",
    "Mr. D. Ganesh", "Dr. Reddy Saisindhu Teja",
    "Mr. K. Santhosh Reddy", "Dr. Ramesh Gade", "Ms. K. Saritha",
    "Ms. P. Keerthi", "Mr. V. Narender",
    "Dr. S. Sashi Devi", "Mr. G. Rajashekhar",
]
# (already created above via FACULTY_ROSTER — this list is just documentation
# of who they are / why they're in the table)

print("Database Seeded Successfully — 9 sections (II/III/IV Year, CSE A/B/C), "
      f"{len(FACULTY_ROSTER)} faculty, AY 2026-2027 real timetable data")