from django.contrib import admin
from .models import (
    User, Department, Semester, Section, Batch,
    Faculty, Subject, FacultySubject, FacultyLeave,
    Room, TimeSlot, Schedule
)

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
@admin.register(User)
class UserAdmin(BaseUserAdmin):

    list_display = (
        'username',
        'email',
        'role',
        'faculty',
        'section',
        'is_active',
        'is_staff',
    )

    list_filter = (
        'role',
        'is_active',
        'is_staff',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    ordering = ('username',)

    fieldsets = BaseUserAdmin.fieldsets + (

        (
            "EduSchedule",

            {
                "fields": (
                    "role",
                    "faculty",
                    "section",
                )
            },
        ),

    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (

        (
            "EduSchedule",

            {
                "fields": (
                    "role",
                    "faculty",
                    "section",
                ),
            },
        ),

    )

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'department')
    list_filter = ('department',)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'semester')
    list_filter = ('semester',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'section')
    list_filter = ('section',)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'workload_limit')
    search_fields = ('name', 'email')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'semester', 'is_lab', 'weekly_hours')
    list_filter = ('semester', 'is_lab')
    search_fields = ('name',)


@admin.register(FacultySubject)
class FacultySubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'faculty', 'subject')
    list_filter = ('faculty',)


@admin.register(FacultyLeave)
class FacultyLeaveAdmin(admin.ModelAdmin):
    list_display = ('id', 'faculty', 'date', 'approved', 'rejected')
    list_filter = ('approved', 'rejected', 'date')
    actions = ['approve_leaves', 'reject_leaves']

    def approve_leaves(self, request, queryset):
        queryset.update(approved=True, rejected=False)
        self.message_user(request, f"{queryset.count()} leave(s) approved.")
    approve_leaves.short_description = "Approve selected leaves"

    def reject_leaves(self, request, queryset):
        queryset.update(approved=False, rejected=True)
        self.message_user(request, f"{queryset.count()} leave(s) rejected.")
    reject_leaves.short_description = "Reject selected leaves"


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_lab')
    list_filter = ('is_lab',)


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'day', 'slot_number')
    list_filter = ('day',)
    ordering = ('day', 'slot_number')


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'batch', 'subject', 'faculty', 'room', 'timeslot', 'date')
    list_filter = ('timeslot__day', 'section', 'subject__is_lab')
    search_fields = ('subject__name', 'faculty__name', 'section__name')
