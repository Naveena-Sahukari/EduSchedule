# seed_data_all_years.py
# Generated from VCE CSE Dept Timetables, AY 2026-2027 — ALL 9 SECTIONS

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
# sem5 = Semester.objects.create(number=5, department=cse_dept)   # III Year I Sem
# sem7 = Semester.objects.create(number=7, department=cse_dept)   # IV Year I Sem

# ----------------------------------------------------
# SECTIONS
# ----------------------------------------------------
ii_a = Section.objects.create(name="CSE-A", semester=sem3)
ii_b = Section.objects.create(name="CSE-B", semester=sem3)
ii_c = Section.objects.create(name="CSE-C", semester=sem3)

# iii_a = Section.objects.create(name="CSE-A", semester=sem5)
# iii_b = Section.objects.create(name="CSE-B", semester=sem5)
# iii_c = Section.objects.create(name="CSE-C", semester=sem5)

# iv_a = Section.objects.create(name="CSE-A", semester=sem7)
# iv_b = Section.objects.create(name="CSE-B", semester=sem7)
# iv_c = Section.objects.create(name="CSE-C", semester=sem7)

ALL_SECTIONS = [ii_a, ii_b, ii_c]

# ----------------------------------------------------
# BATCHES (2 per section, for lab sessions)
# ----------------------------------------------------
for section in ALL_SECTIONS:
    Batch.objects.create(name="Batch-1", section=section)
    Batch.objects.create(name="Batch-2", section=section)

# ----------------------------------------------------
# ROOMS
# ----------------------------------------------------
room_1210 = Room.objects.create(name="1210", is_lab=False)
room_1211 = Room.objects.create(name="1211", is_lab=False)
room_1212 = Room.objects.create(name="1212", is_lab=False)
room_1213 = Room.objects.create(name="1213", is_lab=False)

room_1119 = Room.objects.create(name="1119", is_lab=False)
room_1120 = Room.objects.create(name="1120", is_lab=False)
room_1121 = Room.objects.create(name="1121", is_lab=False)
room_1122 = Room.objects.create(name="1122", is_lab=False)

room_1002 = Room.objects.create(name="1002", is_lab=False)
room_1003 = Room.objects.create(name="1003", is_lab=False)
room_1103 = Room.objects.create(name="1103", is_lab=False)
room_1004 = Room.objects.create(name="1004", is_lab=False)
room_1005 = Room.objects.create(name="1005", is_lab=False)
room_1104 = Room.objects.create(name="1104", is_lab=False)

lab_1208 = Room.objects.create(name="1208", is_lab=True)
lab_1102 = Room.objects.create(name="1102", is_lab=True)
lab_1204 = Room.objects.create(name="1204", is_lab=True)

lab_1201 = Room.objects.create(name="1201", is_lab=True)
lab_1101 = Room.objects.create(name="1101", is_lab=True)
lab_5105 = Room.objects.create(name="5105", is_lab=True)

lab_1202 = Room.objects.create(name="1202", is_lab=True)
lab_1203 = Room.objects.create(name="1203", is_lab=True)

# ----------------------------------------------------
# TIMESLOTS — 7 periods per day, 6 days = 42 slots/week
# ----------------------------------------------------
days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
for day in days:
    for slot in range(1, 8):
        TimeSlot.objects.create(day=day, slot_number=slot)

# ----------------------------------------------------
# FACULTY ROSTER
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
    F[name] = Faculty.objects.create(name=name, email=email, workload_limit=12)

def link(fac_name, subject):
    FacultySubject.objects.get_or_create(faculty=F[fac_name], subject=subject)

# ======================================================================
# CREATE UNIQUE SUBJECTS ONCE PER SEMESTER
# ======================================================================

# --- SEMESTER 3 (II Year) ---
bef_3 = Subject.objects.create(name="Business Economics and Financial Analysis", semester=sem3, weekly_hours=4)
dms_3 = Subject.objects.create(name="Discrete Mathematical Structures", semester=sem3, weekly_hours=4)
oss_3 = Subject.objects.create(name="Operating Systems", semester=sem3, weekly_hours=4)
dbm_3 = Subject.objects.create(name="Data Base Management System", semester=sem3, weekly_hours=4)
oop_3 = Subject.objects.create(name="Object Oriented Programming through JAVA", semester=sem3, weekly_hours=4)
dav_3 = Subject.objects.create(name="Data Analysis and Visualization using Power BI", semester=sem3, weekly_hours=2)
tep_3 = Subject.objects.create(name="Technology Entrepreneurship", semester=sem3, weekly_hours=2)
vas_3 = Subject.objects.create(name="Verbal Ability & Soft Skills", semester=sem3, weekly_hours=2)
ars_3 = Subject.objects.create(name="Aptitude and Reasoning Skills", semester=sem3, weekly_hours=2)
vac3_3 = Subject.objects.create(name="GitHub Copilot (Value Added Course)", semester=sem3, weekly_hours=2)

osl_3 = Subject.objects.create(name="Operating Systems Laboratory", semester=sem3, weekly_hours=2, is_lab=True)
dbl_3 = Subject.objects.create(name="Data Base Management System Laboratory", semester=sem3, weekly_hours=2, is_lab=True)
ool_3 = Subject.objects.create(name="OOP through JAVA Laboratory", semester=sem3, weekly_hours=2, is_lab=True)
ppl_3 = Subject.objects.create(name="Python Programming Laboratory", semester=sem3, weekly_hours=2, is_lab=True)

# Map Sem 3 Faculty mappings cleanly
for fac in ["Mrs. S. Archana"]: link(fac, bef_3)
for fac in ["Ms. D. Dhana Lakshmi", "Mr. V N S Vijay Kumar"]: link(fac, dms_3)
for fac in ["Ms. C. Kavitha", "Ms. C. Bhavana"]: link(fac, oss_3)
for fac in ["Ms. Shaik Shahanaz", "Mr. G S Prasada Reddy", "Dr. J. Naga Padmaja"]: link(fac, dbm_3)
for fac in ["Mr. K. Hari Babu", "Dr. J. Naga Padmaja", "Ms. B. Anjali"]: link(fac, oop_3)
for fac in ["Ms. C. Kavitha", "Ms. C. Bhavana", "Dr. V. Lokeshwari Vinya", "Mr. K Akshay Kumar"]: link(fac, osl_3)
for fac in ["Ms. Shaik Shahanaz", "Mr. V N S Vijay Kumar", "Mr. G S Prasada Reddy", "Mr. C. Satya Kumar", "Dr. J. Naga Padmaja"]: link(fac, dbl_3)
for fac in ["Mr. K. Hari Babu", "Mrs. P S Madhavi", "Dr. J. Naga Padmaja", "Ms. M. Radhika", "Ms. B. Anjali"]: link(fac, ool_3)
for fac in ["Dr. V. Lokeshwari Vinya", "Mrs. D Suguna Devi", "Mrs. P S Madhavi", "Mr. K Akshay Kumar"]: link(fac, ppl_3)
for fac in ["Mr. K Akshay Kumar"]: link(fac, dav_3)
for fac in ["Ms. M. Sowmya", "Ms. AD Rani Sirisha"]: link(fac, tep_3)
for fac in ["Ms. Julia Devaradhi", "Mr. B. Vivekananda"]: link(fac, vas_3)
for fac in ["Mr. M. Sambaraj"]: link(fac,   ars_3)
for fac in ["Mrs. D Suguna Devi", "Ms. Shaik Shahanaz"]: link(fac, vac3_3)

# # --- SEMESTER 5 (III Year) ---
# cns_5 = Subject.objects.create(name="Computer Networks", semester=sem5, weekly_hours=4)
# seg_5 = Subject.objects.create(name="Software Engineering", semester=sem5, weekly_hours=4)
# wts_5 = Subject.objects.create(name="Web Technologies", semester=sem5, weekly_hours=4)
# mlg_5 = Subject.objects.create(name="Machine Learning", semester=sem5, weekly_hours=4)
# rmy_5 = Subject.objects.create(name="Research Methodology", semester=sem5, weekly_hours=3)
# fwe_5 = Subject.objects.create(name="Full Stack Web Engineering (Value Added Course)", semester=sem5, weekly_hours=2)
# lsm5_5 = Subject.objects.create(name="Library/Sports/Mentoring", semester=sem5, weekly_hours=4)
# uml_5 = Subject.objects.create(name="Unified Modeling Language", semester=sem5, weekly_hours=3)

# ehg_5 = Subject.objects.create(name="Ethical Hacking", semester=sem5, weekly_hours=3, is_elective=True, elective_group=1)
# dse_5 = Subject.objects.create(name="Data Science for Engineers", semester=sem5, weekly_hours=3, is_elective=True, elective_group=1)

# wtl_5 = Subject.objects.create(name="Web Technologies Laboratory", semester=sem5, weekly_hours=2, is_lab=True)
# mll_5 = Subject.objects.create(name="Machine Learning Laboratory", semester=sem5, weekly_hours=2, is_lab=True)
# mad_5 = Subject.objects.create(name="Mobile Application Development", semester=sem5, weekly_hours=2, is_lab=True)
# acs_5 = Subject.objects.create(name="Advanced English Communication Skills Laboratory", semester=sem5, weekly_hours=2, is_lab=True)

# # Map Sem 5 Faculty mappings cleanly (Added Mrs. A Ashwini for UML across all)
# for fac in ["Ms. C. Bhavana", "Dr. V. Lokeshwari Vinya", "Dr. R Srikanth"]: link(fac, cns_5)
# for fac in ["Dr. S. Venu Gopal", "Mrs. D Suguna Devi"]: link(fac, seg_5)
# for fac in ["Ms. K. Shalini", "Mr. G S Prasada Reddy"]: link(fac, wts_5)
# for fac in ["Dr. Raghavendra Gouda", "Mr. S. Surendhar", "Mr. A. Bhanu Prasad"]: link(fac, mlg_5)
# for fac in ["Dr. R Srikanth", "Dr. J. Naga Padmaja", "Dr. Raghavendra Gouda"]: link(fac, rmy_5)
# for fac in ["Ms. B. Anjali", "Ms. C. Kavitha", "Mr. M. Manohar Samson"]: link(fac, fwe_5)
# for fac in ["Ms. K. Shalini", "Mr. S. Surendhar", "Mr. G S Prasada Reddy"]: link(fac, lsm5_5)
# for fac in ["Mrs. A Ashwini"]: link(fac, uml_5)
# for fac in ["Mr. Gireesh K Agarwal"]: link(fac, ehg_5)
# for fac in ["Ms. Shaik Shahanaz", "Ms. M. Radhika", "Mr. S. Surendhar"]: link(fac, dse_5)
# for fac in ["Ms. K. Shalini", "Mrs. P S Madhavi", "Mr. K. Hari Babu", "Mr. G S Prasada Reddy"]: link(fac, wtl_5)
# for fac in ["Dr. Raghavendra Gouda", "Mr. S. Surendhar", "Mr. A. Bhanu Prasad", "Mrs. D Suguna Devi"]: link(fac, mll_5)
# for fac in ["Mr. B J V Varma", "Mr. K. Hari Babu", "Ms. B. Anjali", "Ms. D. Dhana Lakshmi"]: link(fac, mad_5)
# for fac in ["Dr. V Parvathi", "Ms. Antara Ghosh", "Dr. Bhakti Shrinivas Natoo", "Ms. Syeda Fatima Farheen", "Ms. Anaswara Ramachandran"]: link(fac, acs_5)

# # --- SEMESTER 7 (IV Year) ---
# dmg_7 = Subject.objects.create(name="Data Mining", semester=sem7, weekly_hours=6)
# bda_7 = Subject.objects.create(name="Big Data Analytics", semester=sem7, weekly_hours=5)
# fora_7 = Subject.objects.create(name="Fundamentals of Robotics", semester=sem7, weekly_hours=2)
# pwp_7 = Subject.objects.create(name="Project Work Phase-I", semester=sem7, weekly_hours=12)
# dtt_7 = Subject.objects.create(name="Devops Tools and Techniques", semester=sem7, weekly_hours=3)
# lsm7_7 = Subject.objects.create(name="Library/Sports/Mentoring", semester=sem7, weekly_hours=6)

# csy_7 = Subject.objects.create(name="Cloud Security", semester=sem7, weekly_hours=3, is_elective=True, elective_group=1)
# nlp_7 = Subject.objects.create(name="Natural Language Processing", semester=sem7, weekly_hours=3, is_elective=True, elective_group=1)
# isy_7 = Subject.objects.create(name="IoT Security", semester=sem7, weekly_hours=3, is_elective=True, elective_group=2)
# wsa_7 = Subject.objects.create(name="Web and Social Media Analytics", semester=sem7, weekly_hours=3, is_elective=True, elective_group=2)

# dml_7 = Subject.objects.create(name="Data Mining Laboratory", semester=sem7, weekly_hours=2, is_lab=True)
# bdl_7 = Subject.objects.create(name="Big Data Analytics Laboratory", semester=sem7, weekly_hours=2, is_lab=True)

# # Map Sem 7 Faculty mappings cleanly
# for fac in ["Dr. R Srikanth", "Ms. M. Radhika", "Mr. A. Bhanu Prasad"]: link(fac, dmg_7)
# for fac in ["Ms. D. Dhana Lakshmi", "Mr. B J V Varma"]: link(fac, bda_7)
# for fac in ["Dr. P. Venkateshwar Reddy", "Dr. K. Deepak", "Dr. S. Thirupati"]: link(fac, fora_7)
# for fac in ["Dr. R Srikanth", "Dr. Raghavendra Gouda", "Mr. B J V Varma"]: link(fac, pwp_7)
# for fac in ["Mr. K. Hari Babu", "Ms. D. Dhana Lakshmi"]: link(fac, dtt_7)
# for fac in ["Dr. R Srikanth", "Dr. Raghavendra Gouda", "Mr. B J V Varma"]: link(fac, lsm7_7)
# for fac in ["Ms. B. Vaishnavi"]: link(fac, csy_7)
# for fac in ["Mr. S. Surendhar", "Dr. Raghavendra Gouda"]: link(fac, nlp_7)
# for fac in ["Dr. Gouse Baig Mohammad"]: link(fac, isy_7)
# for fac in ["Dr. Ramesh Karnati", "Mrs. P S Madhavi"]: link(fac, wsa_7)
# for fac in ["Dr. R Srikanth", "Mr. A. Bhanu Prasad", "Ms. M. Radhika", "Mr. C. Satya Kumar"]: link(fac, dml_7)
# for fac in ["Ms. D. Dhana Lakshmi", "Mr. K Akshay Kumar", "Mr. B J V Varma", "Ms. M. Radhika", "Ms. C. Kavitha"]: link(fac, bdl_7)

print(f"Database Seeded Successfully — Corrected total hours to 330 session limits.")