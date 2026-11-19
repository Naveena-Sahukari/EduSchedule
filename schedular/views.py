from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models  # Add this to your imports

# Excel and PDF exporting tools
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter, landscape
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from .models import (
    Faculty, Section, Subject, FacultyLeave, Schedule, Room, TimeSlot, Department, Semester
)
from .engine import generate_timetable

# Global Configuration Parameters
SLOT_START_HOURS = {1: 9, 2: 10, 3: 11, 4: 12, 5: 14, 6: 15}

ROLE_DASHBOARD_MAP = {
    "ADMIN": "admin_dashboard",
    "FACULTY": "faculty_dashboard",
    "STUDENT": "student_dashboard",
}

# Day choices and slot numbers shared across views
DAY_CHOICES = [
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
    ('SAT', 'Saturday'),
]
SLOT_NUMBERS = [1, 2, 3, 4, 5, 6]


# =====================================================
# ROLE-BASED PERMISSION HELPERS & ROUTERS
# =====================================================
def admin_required(view_func):
    actual_decorator = user_passes_test(
        lambda u: u.is_active and (u.is_staff or u.is_superuser or getattr(u, 'role', None) == "ADMIN"),
        login_url='login'
    )
    return actual_decorator(view_func)


def redirect_dashboard_by_role(request, user):
    target_route = ROLE_DASHBOARD_MAP.get(getattr(user, 'role', None))
    if target_route or user.is_superuser:
        return redirect(target_route if target_route else "admin_dashboard")
    logout(request)
    messages.error(request, "Invalid account role configuration. Please contact your system administrator.")
    return redirect("login")


# =====================================================
# AUTHENTICATION MANAGEMENT
# =====================================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect_dashboard_by_role(request, request.user)

    if request.method == "POST":
        username_input = request.POST.get("username", "").strip()
        password_input = request.POST.get("password", "")

        if not username_input or not password_input:
            messages.error(request, "Please fill in all required login fields.")
            return render(request, "schedular/login.html")

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect_dashboard_by_role(request, user)
            else:
                messages.error(request, "This account has been deactivated.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "schedular/login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    return redirect_dashboard_by_role(request, request.user)


# =====================================================
# DASHBOARD VIEWS
# =====================================================
@admin_required
def admin_dashboard(request):
    all_leaves = FacultyLeave.objects.select_related('faculty').order_by('-date')
    pending_leaves = all_leaves.filter(approved=False, rejected=False) if hasattr(FacultyLeave, 'rejected') else all_leaves.filter(approved=False)
    
    # Handle leaves without rejected field
    try:
        pending_count = all_leaves.filter(approved=False, rejected=False).count()
        approved_count = all_leaves.filter(approved=True).count()
        rejected_count = all_leaves.filter(rejected=True).count()
    except Exception:
        pending_count = all_leaves.filter(approved=False).count()
        approved_count = all_leaves.filter(approved=True).count()
        rejected_count = 0

    schedules = Schedule.objects.filter(date__isnull=True).select_related(
        'section', 'subject', 'faculty', 'room', 'timeslot'
    )

    # FIX: surface the timetable-generation log to the admin UI.
    # generate_timetable_view() stashes it in the session; we pop it here
    # so it only shows once (right after a generation attempt) and clears
    # itself on the next page load.
    generation_log = request.session.pop('timetable_generation_log', None)
    generation_success = request.session.pop('timetable_generation_success', None)

    context = {
        "faculty": Faculty.objects.count(),
        "faculty_list": Faculty.objects.prefetch_related('facultysubject_set__subject').all(),
        "subjects": Subject.objects.count(),
        "sections": Section.objects.count(),
        "rooms": Room.objects.count(),
        "room_list": Room.objects.all(),
        "section_list": Section.objects.select_related('semester__department').all(),
        "pending_leaves": pending_leaves[:5],  # dashboard preview
        "all_leaves": all_leaves,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "schedules": schedules,
        "day_choices": DAY_CHOICES,
        "slot_numbers": SLOT_NUMBERS,
        "generation_log": generation_log,
        "generation_success": generation_success,
    }
    return render(request, "schedular/admin.html", context)


@login_required
def faculty_dashboard(request):
    if getattr(request.user, 'role', None) != "FACULTY":
        return redirect("dashboard")

    faculty_profile = getattr(request.user, 'faculty', None)
    if not faculty_profile:
        messages.error(request, "No faculty profile linked to this user account.")
        return render(request, "schedular/faculty.html", {"error_message": "Faculty configuration missing."})

    now = timezone.localtime()
    day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
    today_day = day_map.get(now.weekday(), 'MON')
    current_hour = now.hour

    schedule_query = Schedule.objects.filter(
        faculty=faculty_profile,
        date__isnull=True
    ).select_related('section', 'subject', 'room', 'timeslot')

    all_schedules = list(schedule_query)

    today_schedules = sorted(
        [s for s in all_schedules if s.timeslot.day == today_day],
        key=lambda s: s.timeslot.slot_number
    )

    current_slot_num = None
    for slot, start_hour in SLOT_START_HOURS.items():
        if start_hour <= current_hour < (start_hour + 1):
            current_slot_num = slot
            break

    current_class = None
    if current_slot_num:
        current_class = next((s for s in today_schedules if s.timeslot.slot_number == current_slot_num), None)

    is_busy = "Busy" if current_class else "Available"
    if current_hour < 9 or current_hour >= 17 or today_day == 'SUN':
        is_busy = "Outside Working Hours"

    unique_subjects = {s.subject.id for s in all_schedules}
    unique_sections = {s.section.id for s in all_schedules}

    days_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
    grouped_schedule_dict = {day: [] for day in days_order}
    for s in all_schedules:
        if s.timeslot.day in grouped_schedule_dict:
            grouped_schedule_dict[s.timeslot.day].append(s)
    for day in grouped_schedule_dict:
        grouped_schedule_dict[day].sort(key=lambda s: s.timeslot.slot_number)

    # Fetch leave history for the faculty
    my_leaves = FacultyLeave.objects.filter(faculty=faculty_profile).order_by('-date')[:10]

    context = {
        "today_schedules": today_schedules,
        "current_class": current_class,
        "grouped_schedule": grouped_schedule_dict,
        "unique_subjects_count": len(unique_subjects),
        "unique_sections_count": len(unique_sections),
        "is_busy": is_busy,
        "availability_status": is_busy,
        "my_leaves": my_leaves,
    }
    return render(request, "schedular/faculty.html", context)


@login_required
def student_dashboard(request):
    if getattr(request.user, 'role', None) != "STUDENT":
        return redirect("dashboard")

    section = getattr(request.user, 'section', None)
    if not section:
        messages.error(request, "No section assigned to your student profile.")
        return render(request, "schedular/student.html", {"error_message": "No section assigned."})

    now = timezone.localtime()
    day_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
    today_day = day_map.get(now.weekday(), 'MON')
    current_hour = now.hour

    schedule_query = Schedule.objects.filter(
        section=section,
        date__isnull=True
    ).select_related('subject', 'room', 'faculty', 'timeslot')

    all_schedules = list(schedule_query)

    today_schedules = sorted(
        [s for s in all_schedules if s.timeslot.day == today_day],
        key=lambda s: s.timeslot.slot_number
    )

    current_slot_num = None
    for slot, start_hour in SLOT_START_HOURS.items():
        if start_hour <= current_hour < (start_hour + 1):
            current_slot_num = slot
            break

    current_class = None
    next_class = None
    if current_slot_num:
        current_class = next((s for s in today_schedules if s.timeslot.slot_number == current_slot_num), None)

    if not current_class:
        next_class = next(
            (s for s in today_schedules if SLOT_START_HOURS.get(s.timeslot.slot_number, 0) > current_hour),
            None
        )

    raw_faculty_map = {}
    for s in all_schedules:
        f_name = s.faculty.name
        if f_name not in raw_faculty_map:
            raw_faculty_map[f_name] = set()
        raw_faculty_map[f_name].add(s.subject.name)

    faculty_list = [
        {"name": name, "subjects": ", ".join(sorted(subs))}
        for name, subs in raw_faculty_map.items()
    ]

    days_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    today_index = days_order.index(today_day) if today_day in days_order else 0
    upcoming_classes = []
    for s in all_schedules:
        s_day_idx = days_order.index(s.timeslot.day) if s.timeslot.day in days_order else 0
        if s_day_idx > today_index:
            upcoming_classes.append(s)
        elif s_day_idx == today_index:
            slot_start = SLOT_START_HOURS.get(s.timeslot.slot_number, 0)
            if slot_start > current_hour:
                upcoming_classes.append(s)

    upcoming_classes.sort(key=lambda s: (
        days_order.index(s.timeslot.day) if s.timeslot.day in days_order else 0,
        s.timeslot.slot_number
    ))

    # Count unique subjects
    unique_subjects = len({s.subject.id for s in all_schedules})

    # Build grid: list of (day_name, [slot_data, ...]) for template rendering
    timetable_grid = []
    for day_abbr, day_name in DAY_CHOICES:
        row = []
        for slot_num in SLOT_NUMBERS:
            cell = next(
                (s for s in all_schedules
                 if s.timeslot.day == day_abbr and s.timeslot.slot_number == slot_num),
                None
            )
            row.append(cell)
        timetable_grid.append((day_name, row))

    context = {
        "current_class": current_class,
        "next_class": next_class,
        "today_classes_count": len(today_schedules),
        "total_classes": len(all_schedules),
        "weekly_classes": len(all_schedules),
        "total_subjects": unique_subjects,
        "today_schedules": today_schedules,
        "all_schedules": all_schedules,
        "timetable_grid": timetable_grid,
        "upcoming_classes": upcoming_classes[:6],
        "faculty_list": faculty_list,
        "day_choices": DAY_CHOICES,
        "slot_numbers": SLOT_NUMBERS,
    }
    return render(request, "schedular/student.html", context)


# =====================================================
# LEAVE MANAGEMENT
# =====================================================
@login_required
def apply_leave(request):
    if getattr(request.user, 'role', None) != "FACULTY":
        return redirect("dashboard")

    faculty_profile = getattr(request.user, 'faculty', None)
    if not faculty_profile:
        messages.error(request, "No faculty profile linked to submit leave.")
        return redirect("dashboard")

    if request.method == "POST":
        leave_date = request.POST.get("leave_date")
        leave_reason = request.POST.get("reason", "").strip()

        if not leave_date or not leave_reason:
            messages.error(request, "All form fields must be completed.")
            return redirect("faculty_dashboard")

        FacultyLeave.objects.create(
            faculty=faculty_profile,
            date=leave_date,
            reason=leave_reason
        )
        messages.success(request, "Leave request submitted successfully. Awaiting admin approval.")
        return redirect("faculty_dashboard")

    return redirect("faculty_dashboard")


@admin_required
def approve_leave(request, leave_id):
    leave = get_object_or_404(FacultyLeave, id=leave_id)
    if request.method == "POST":
        leave.approved = True
        leave.save()
        messages.success(request, f"Leave for {leave.faculty.name} on {leave.date} approved.")
    return redirect("admin_dashboard")


@admin_required
def reject_leave(request, leave_id):
    leave = get_object_or_404(FacultyLeave, id=leave_id)
    if request.method == "POST":
        # Set approved to False explicitly (it already is, but mark as reviewed)
        # If your model has a rejected field, use that. Otherwise use a convention.
        leave.approved = False
        # If model has rejected field:
        if hasattr(leave, 'rejected'):
            leave.rejected = True
        leave.save()
        messages.success(request, f"Leave for {leave.faculty.name} on {leave.date} rejected.")
    return redirect("admin_dashboard")


# =====================================================
# TIMETABLE GENERATION
# =====================================================
@admin_required
@require_http_methods(["POST"])
def generate_timetable_view(request):

    success, log_text = generate_timetable()

    # FIX: previously log_text was only sent to the server logger and
    # never reached the user — meaning failures (e.g. "No faculty for
    # lab X", "Elective group has only 1 subject") were invisible in
    # the UI. Now we stash it in the session so admin_dashboard() can
    # render it directly on the page after redirect.
    request.session['timetable_generation_log'] = log_text
    request.session['timetable_generation_success'] = success

    if success:
        messages.success(request, "Timetable generated successfully! See the log below for details.")
    else:
        messages.warning(request, "Timetable generation failed or encountered errors. See the log below for details.")

    return redirect("admin_dashboard")


from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import PageBreak, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors

#from datetime import date
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import PageBreak, SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from .models import Section, Schedule

# Timetable Configuration
TIMETABLE_SLOTS = {
    1: {"time": "09:10 - 10:10", "type": "class"},
    2: {"time": "10:10 - 11:00", "type": "class"},
    "BREAK": {"label": "BREAK", "type": "interval"},
    3: {"time": "11:10 - 12:00", "type": "class"},
    4: {"time": "12:00 - 12:50", "type": "class"},
    "LUNCH": {"label": "LUNCH", "type": "interval"},
    5: {"time": "01:400 - 02:40", "type": "class"},
    6: {"time": "02:40 - 03:30", "type": "class"},
    7: {"time": "03:30 - 04:10", "type": "class"},
}

# Helper Functions
def get_academic_year():
    today = date.today()
    return f"{today.year}-{today.year + 1}"

def get_year_from_semester(semester):
    mapping = {1: "I", 2: "I", 3: "II", 4: "II", 5: "III", 6: "III", 7: "IV", 8: "IV"}
    return mapping.get(semester, "")

def get_faculty_initials(name):
    return "".join(word[0].upper() for word in name.split()) if name else ""

# PDF Export View
@login_required
@require_http_methods(["GET"])
def export_timetable_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="timetable.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("CollegeTitle", parent=styles["Title"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=18, leading=24)
    heading_style = ParagraphStyle("HeadingStyle", parent=styles["Heading2"], alignment=TA_CENTER)
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, leading=10)

    # Efficiency: List conversion to avoid repeated DB queries
    sections = list(Section.objects.all().select_related("semester").order_by("semester__number", "name"))
    total_sections = len(sections)

    for index, section in enumerate(sections):
        schedules = Schedule.objects.filter(section=section, date__isnull=True).select_related('subject', 'faculty', 'timeslot', 'room')
        if not schedules.exists(): continue

        sem_num = getattr(section.semester, 'number', 0)
        
        # Header Info
        elements.append(Paragraph("<b>VARDHAMAN COLLEGE OF ENGINEERING</b>", title_style))
        elements.append(Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING", heading_style))
        elements.append(Paragraph("<b>TIMETABLE</b>", heading_style))
        elements.append(Paragraph(f"Academic Year: {get_academic_year()}", styles['Normal']))
        elements.append(Paragraph(f"Year: {get_year_from_semester(sem_num)} B.Tech    Semester: {sem_num}", styles['Normal']))
        elements.append(Paragraph(f"<b>Section: {section.name}</b>", styles['Normal']))
        elements.append(Spacer(1, 10))

        # Build headers
        row_headers = [Paragraph("<b>Day</b>", cell_style)]
        for slot in TIMETABLE_SLOTS.values():
            label = slot['label'] if slot['type'] == 'interval' else slot['time']
            row_headers.append(Paragraph(f"<b>{label}</b>", cell_style))
        data = [row_headers]

        # Matrix population
        matrix = {day: {sk: "" for sk in TIMETABLE_SLOTS} for day in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]}
        for s in schedules:
            if (s.timeslot and s.timeslot.day in matrix and s.timeslot.slot_number in matrix[s.timeslot.day]):
                # Uses short_name if defined in Subject model, otherwise full name
                name = getattr(s.subject, 'short_name', s.subject.name)
                room = getattr(s.room, 'name', '')
                matrix[s.timeslot.day][s.timeslot.slot_number] = f"<b>{name}</b><br/>({get_faculty_initials(s.faculty.name)})<br/>{room}"

        # Table rows
        for day in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]:
            row = [Paragraph(f"<b>{day}</b>", cell_style)]
            for sk, slot in TIMETABLE_SLOTS.items():
                content = slot['label'] if slot['type'] == 'interval' else matrix[day].get(sk, "-")
                row.append(Paragraph(content, cell_style))
            data.append(row)

        table = Table(data, colWidths=[40] + [75]*8, rowHeights=[28] + [55]*6)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D9EAD3")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (3, 1), (3, -1), colors.lightgrey), # Break
            ('BACKGROUND', (6, 1), (6, -1), colors.lightgrey), # Lunch
        ]))
        elements.append(table)
        
        if index < total_sections - 1: elements.append(PageBreak())

    if not elements: elements.append(Paragraph("No timetable data found.", styles["Normal"]))
    doc.build(elements)
    return response




# Add these views to your existing views.py file
# These handle individual faculty timetable display and export
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.enums import TA_CENTER

from .models import Faculty, Schedule, TimeSlot, Section
from datetime import date


# ======================================================================
# FACULTY TIMETABLE UTILITIES
# ======================================================================

# ======================================================================
# FACULTY TIMETABLE UTILITIES - CORRECTED VERSION
# ======================================================================
# REPLACE LINES 558-747 IN YOUR views.py WITH THIS SECTION

def get_faculty_timetable_grid(faculty):
    """
    Generate a timetable grid for a single faculty member.
    Returns structured data for template rendering.
    
    Returns:
        {
            'faculty': Faculty object,
            'grid': [(day, [schedule_or_none, ...]), ...],
            'max_slot': int,
            'stats': {...}
        }
    """
    # Get max slot number
    max_slot = TimeSlot.objects.aggregate(
        models.Max('slot_number')
    )['slot_number__max'] or 7
    
    # Get schedules for this faculty
    schedules = Schedule.objects.filter(
        faculty=faculty,
        date__isnull=True
    ).select_related('section', 'subject', 'room', 'timeslot', 'batch')
    
    # Create lookup dict: (day, slot) -> schedule
    schedule_map = {}
    for sch in schedules:
        key = (sch.timeslot.day, sch.timeslot.slot_number)
        schedule_map[key] = sch
    
    # Build grid
    days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    grid = []
    
    for day in days:
        row = []
        for slot in range(1, max_slot + 1):
            schedule = schedule_map.get((day, slot), None)
            row.append(schedule)
        grid.append((day, row))
    
    # Calculate stats
    total_sessions = len(schedules)
    unique_sections = set(s.section.name for s in schedules)
    unique_subjects = set(s.subject.name for s in schedules)
    days_teaching = set(s.timeslot.day for s in schedules)
    
    return {
        'faculty': faculty,
        'grid': grid,
        'max_slot': max_slot,
        'stats': {
            'total_sessions': total_sessions,
            'sections': sorted(list(unique_sections)),
            'subjects': sorted(list(unique_subjects)),
            'days_teaching': sorted(list(days_teaching)),
            'workload_limit': faculty.workload_limit,
            'workload_percentage': int((total_sessions / faculty.workload_limit) * 100) if faculty.workload_limit > 0 else 0,
        }
    }


# ======================================================================
# PERMISSION DECORATOR FOR ADMIN CHECK
# ======================================================================

def admin_required(view_func):
    """Decorator to check admin access."""
    actual_decorator = user_passes_test(
        lambda u: u.is_active and (u.is_staff or u.is_superuser or getattr(u, 'role', None) == "ADMIN"),
        login_url='login'
    )
    return actual_decorator(view_func)


def is_admin_user(user):
    return user.is_active and (user.is_staff or user.is_superuser or getattr(user, 'role', None) == "ADMIN")

# ======================================================================
# VIEW: Faculty Individual Timetable (Grid View)
# ======================================================================

@login_required
def view_faculty_timetable(request, faculty_id=None):
    """
    Display individual timetable for a faculty member.
    
    If faculty_id is provided and user is admin: view any faculty's timetable
    Otherwise: view current faculty's timetable (if logged in as faculty)
    """
    user_role = getattr(request.user, 'role', None)
    
    # Determine which faculty to view
    if faculty_id and is_admin_user(request.user):
        # Admin viewing any faculty's timetable
        faculty = get_object_or_404(Faculty, id=faculty_id)
    elif user_role == 'FACULTY':
        # Faculty viewing their own timetable
        faculty = getattr(request.user, 'faculty', None)
        if not faculty:
            return render(request, 'schedular/error.html', {
                'error_message': 'No faculty profile linked to this user account.'
            })
    else:
        return redirect('dashboard')
    
    # Get timetable data
    timetable_data = get_faculty_timetable_grid(faculty)
    
    context = {
        'faculty': faculty,
        'timetable_grid': timetable_data['grid'],
        'max_slot': timetable_data['max_slot'],
        'stats': timetable_data['stats'],
        'slot_start_hours': {1: 9, 2: 10, 3: 11, 4: 12, 5: 14, 6: 15, 7: 16},
    }
    
    return render(request, 'schedular/faculty_timetable.html', context)


# ======================================================================
# VIEW: Faculty Schedule by Day (Detailed List View)
# ======================================================================

@login_required
def faculty_schedule_by_day(request, faculty_id=None):
    """
    Display faculty schedule grouped by day with detailed information.
    """
    user_role = getattr(request.user, 'role', None)
    
    if faculty_id and is_admin_user(request.user):
        faculty = get_object_or_404(Faculty, id=faculty_id)
    elif user_role == 'FACULTY':
        faculty = getattr(request.user, 'faculty', None)
        if not faculty:
            return render(request, 'schedular/error.html', {
                'error_message': 'No faculty profile linked to this user account.'
            })
    else:
        return redirect('dashboard')
    
    # Get schedules by day
    schedules = Schedule.objects.filter(
        faculty=faculty,
        date__isnull=True
    ).select_related(
        'section', 'subject', 'room', 'timeslot', 'batch'
    ).order_by(
        'timeslot__day', 'timeslot__slot_number'
    )
    
    # Group by day
    by_day = {}
    days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    for day in days:
        by_day[day] = [s for s in schedules if s.timeslot.day == day]
    
    context = {
        'faculty': faculty,
        'schedule_by_day': by_day,
        'total_sessions': len(schedules),
    }
    
    return render(request, 'schedular/faculty_schedule_by_day.html', context)





# ======================================================================
# VIEW: All Faculties List (Admin Dashboard)
# ======================================================================






@admin_required
def all_faculty_timetables_list(request):
    """
    Display a list of all faculty members with quick access to their timetables.
    """
    faculties = Faculty.objects.all().order_by('name')
    
    # Enrich faculty list with basic stats
    faculty_data = []
    for faculty in faculties:
        schedules = Schedule.objects.filter(
            faculty=faculty,
            date__isnull=True
        )
        total_sessions = len(schedules)
        
        faculty_data.append({
            'faculty': faculty,
            'total_sessions': total_sessions,
            'workload_usage': int((total_sessions / faculty.workload_limit) * 100) if faculty.workload_limit > 0 else 0,
        })
    
    context = {
        'faculty_data': faculty_data,
        'total_faculties': len(faculties),
    }
    
    return render(request, 'schedular/all_faculty_timetables.html', context)




# ======================================================================
# EXPORT: Faculty Timetable to PDF
# ======================================================================

@login_required
@require_http_methods(["GET"])
def export_faculty_timetable_pdf(request, faculty_id=None):
    """
    Export individual faculty timetable to PDF.
    """
    user_role = getattr(request.user, 'role', None)
    
    if faculty_id and is_admin_user(request.user):
        faculty = get_object_or_404(Faculty, id=faculty_id)
    elif user_role == 'FACULTY':
        faculty = getattr(request.user, 'faculty', None)
        if not faculty:
            return redirect('dashboard')
    else:
        return redirect('dashboard')
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="timetable_{faculty.name.replace(" ", "_")}.pdf"'
    
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        "FacultyTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20
    )
    
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )
    
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=8,
        leading=10
    )
    
    # ---- HEADER SECTION ----
    elements.append(Paragraph("<b>VARDHAMAN COLLEGE OF ENGINEERING</b>", title_style))
    elements.append(Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING", heading_style))
    elements.append(Paragraph("<b>FACULTY TIMETABLE</b>", heading_style))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph(f"<b>Faculty Name:</b> {faculty.name}", styles['Normal']))
    elements.append(Paragraph(f"<b>Email:</b> {faculty.email}", styles['Normal']))
    elements.append(Paragraph(f"<b>Workload Limit:</b> {faculty.workload_limit} hours/week", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # ---- GET TIMETABLE DATA ----
    timetable_data = get_faculty_timetable_grid(faculty)
    max_slot = timetable_data['max_slot']
    stats = timetable_data['stats']
    
    # ---- STATISTICS ----
    elements.append(Paragraph("<b>Teaching Summary:</b>", styles['Heading3']))
    stats_text = f"""
    <b>Total Sessions:</b> {stats['total_sessions']} | 
    <b>Sections:</b> {', '.join(stats['sections'])} | 
    <b>Subjects:</b> {', '.join(stats['subjects'])}
    """
    elements.append(Paragraph(stats_text, styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # ---- TIMETABLE GRID ----
    elements.append(Paragraph("<b>Weekly Schedule:</b>", styles['Heading3']))
    elements.append(Spacer(1, 8))
    
    # Build table headers (Day + Slots)
    col_widths = [50] + [65] * max_slot
    headers = [Paragraph("<b>Day</b>", cell_style)]
    for slot_num in range(1, max_slot + 1):
        headers.append(Paragraph(f"<b>P{slot_num}</b>", cell_style))
    
    table_data = [headers]
    
    # Build table rows
    for day, row in timetable_data['grid']:
        day_cell = [Paragraph(f"<b>{day}</b>", cell_style)]
        
        for schedule in row:
            if schedule:
                cell_content = f"""
                <b>{schedule.subject.name}</b><br/>
                {schedule.section.name}<br/>
                {schedule.room.name}
                """
            else:
                cell_content = "—"
            
            day_cell.append(Paragraph(cell_content, cell_style))
        
        table_data.append(day_cell)
    
    # Create and style table
    table = Table(table_data, colWidths=col_widths, rowHeights=[25] + [55] * 6)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4285F4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
    ]))
    
    elements.append(table)
    
    # ---- FOOTER ----
    elements.append(Spacer(1, 16))
    elements.append(Paragraph(f"Generated on: {date.today().strftime('%d-%m-%Y')}", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    return response


# ======================================================================
# EXPORT: All Faculty Timetables to PDF (combined)
# ======================================================================

@admin_required
@require_http_methods(["GET"])
def export_all_faculty_timetables_pdf(request):
    """
    Export timetables for all faculty members to a single PDF.
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="all_faculty_timetables.pdf"'
    
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20
    )
    
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )
    
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=7,
        leading=9
    )
    
    # Get all faculties
    faculties = Faculty.objects.all().order_by('name')
    
    for idx, faculty in enumerate(faculties):
        # Add page break between faculties (except before first)
        if idx > 0:
            elements.append(PageBreak())
        
        # Header
        elements.append(Paragraph(f"<b>{faculty.name}</b>", title_style))
        elements.append(Paragraph(f"Email: {faculty.email} | Workload Limit: {faculty.workload_limit}", heading_style))
        elements.append(Spacer(1, 12))
        
        # Get timetable
        timetable_data = get_faculty_timetable_grid(faculty)
        max_slot = timetable_data['max_slot']
        
        # Build table
        col_widths = [50] + [60] * max_slot
        headers = [Paragraph("<b>Day</b>", cell_style)]
        for slot_num in range(1, max_slot + 1):
            headers.append(Paragraph(f"<b>P{slot_num}</b>", cell_style))
        
        table_data = [headers]
        
        for day, row in timetable_data['grid']:
            day_cell = [Paragraph(f"<b>{day}</b>", cell_style)]
            
            for schedule in row:
                if schedule:
                    cell_content = f"{schedule.subject.name}\n{schedule.section.name}"
                else:
                    cell_content = "—"
                
                day_cell.append(Paragraph(cell_content, cell_style))
            
            table_data.append(day_cell)
        
        table = Table(table_data, colWidths=col_widths, rowHeights=[20] + [40] * 6)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4285F4")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
    
    if not elements:
        elements.append(Paragraph("No faculty data found.", styles["Normal"]))
    
    doc.build(elements)
    return response