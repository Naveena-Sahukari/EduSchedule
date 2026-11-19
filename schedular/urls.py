from django.urls import path
from . import views

# Import the faculty timetable view functions
from .views import (
    view_faculty_timetable,
    faculty_schedule_by_day,
    all_faculty_timetables_list,
    export_faculty_timetable_pdf,
    export_all_faculty_timetables_pdf,
)

urlpatterns = [
    # ========================================================================
    # AUTHENTICATION ROUTES
    # ========================================================================
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ========================================================================
    # ADMIN ROUTES
    # ========================================================================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('generate-timetable/', views.generate_timetable_view, name='generate_timetable'),
    path('approve-leave/<int:leave_id>/', views.approve_leave, name='approve_leave'),
    path('reject-leave/<int:leave_id>/', views.reject_leave, name='reject_leave'),

    # ========================================================================
    # FACULTY ROUTES
    # ========================================================================
    path('faculty-dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('apply-leave/', views.apply_leave, name='apply_leave'),

    # ========================================================================
    # STUDENT ROUTES
    # ========================================================================
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),

    # ========================================================================
    # EXPORT ROUTES (EXISTING)
    # ========================================================================
    path('export-pdf/', views.export_timetable_pdf, name='export_pdf'),

    # ========================================================================
    # FACULTY INDIVIDUAL TIMETABLE ROUTES (NEW)
    # ========================================================================
    
    # Faculty viewing their own timetable (grid format)
    path(
        'faculty/timetable/',
        view_faculty_timetable,
        name='view_faculty_timetable'
    ),
    
    # Admin viewing specific faculty's timetable (by faculty_id)
    path(
        'faculty/<int:faculty_id>/timetable/',
        view_faculty_timetable,
        name='view_specific_faculty_timetable'
    ),
    
    # Faculty viewing their own schedule by day (detailed list view)
    path(
        'faculty/schedule-by-day/',
        faculty_schedule_by_day,
        name='faculty_schedule_by_day'
    ),
    
    # Admin viewing specific faculty's schedule by day
    path(
        'faculty/<int:faculty_id>/schedule-by-day/',
        faculty_schedule_by_day,
        name='faculty_schedule_by_day_admin'
    ),
    
    # Admin viewing list of all faculty with timetables
    path(
        'faculty-timetables/',
        all_faculty_timetables_list,
        name='all_faculty_timetables_list'
    ),
    
    # Faculty exporting their own timetable to PDF
    path(
        'faculty/timetable/export-pdf/',
        export_faculty_timetable_pdf,
        name='export_faculty_timetable_pdf'
    ),
    
    # Admin exporting specific faculty's timetable to PDF
    path(
        'faculty/<int:faculty_id>/timetable/export-pdf/',
        export_faculty_timetable_pdf,
        name='export_specific_faculty_timetable_pdf'
    ),
    
    # Admin exporting all faculty timetables to PDF (bulk)
    path(
        'faculty-timetables/export-pdf/',
        export_all_faculty_timetables_pdf,
        name='export_all_faculty_timetables_pdf'
    ),
]