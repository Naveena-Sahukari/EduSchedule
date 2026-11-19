from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('FACULTY', 'Faculty'),
        ('STUDENT', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    faculty = models.OneToOneField(
        'Faculty', on_delete=models.CASCADE, null=True, blank=True
    )
    section = models.ForeignKey(
        'Section', on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return self.username


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Semester(models.Model):
    number = models.IntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return f"Semester {self.number} — {self.department}"


class Section(models.Model):
    name = models.CharField(max_length=10)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Batch(models.Model):
    name = models.CharField(max_length=20)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.section} - {self.name}"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    is_lab = models.BooleanField(default=False)
    weekly_hours = models.IntegerField(default=3)

    # ── Elective fields (REQ-03) ──────────────────────────────────────────
    # Mark a subject as an elective. Two subjects with the same elective_group
    # number will be scheduled simultaneously in different rooms, displayed as
    # "Sub-A / Sub-B" in the timetable (e.g. "DAS / WDS").
    # Only applies to Semester 5+ (3rd year and above).
    # Example: set DAS → is_elective=True, elective_group=1
    #          set WDS → is_elective=True, elective_group=1
    #          They will be paired automatically.
    is_elective = models.BooleanField(
        default=False,
        help_text="Tick if this is an elective subject (runs simultaneously with its pair)"
    )
    elective_group = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "Pair electives by giving them the same group number "
            "(e.g. both 'DAS' and 'WDS' get group=1). "
            "Leave blank for non-electives."
        )
    )

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        """Used in timetable cells — normal subjects return their own name."""
        return self.name


class Faculty(models.Model):
    """Faculty model with timetable helper methods"""
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    workload_limit = models.IntegerField(default=20)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Faculty"

    # ──── TIMETABLE HELPER METHODS ────────────────────────────────────
    
    def get_all_schedules(self):
        """
        Get all schedules for this faculty across all sections.
        Returns schedules grouped by day.
        """
        schedules = Schedule.objects.filter(
            faculty=self,
            date__isnull=True
        ).select_related(
            'section', 'subject', 'room', 'timeslot', 'batch'
        ).order_by(
            'timeslot__day', 'timeslot__slot_number'
        )
        return schedules

    def get_schedules_by_day(self):
        """
        Organize all faculty schedules by day of the week.
        Returns: {'MON': [...], 'TUE': [...], ...}
        """
        schedules = self.get_all_schedules()
        by_day = {}
        
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        for day in days:
            by_day[day] = [s for s in schedules if s.timeslot.day == day]
        
        return by_day

    def get_timetable_grid(self):
        """
        Create a 2D grid of faculty's timetable.
        Returns: [(day_name, [schedule_or_none, schedule_or_none, ...]), ...]
        
        Grid structure:
        - Rows: Days (MON-SAT)
        - Columns: Slot numbers (1-7 or based on TimeSlot.slot_number max)
        """
        # Get max slot number
        max_slot = TimeSlot.objects.aggregate(
            models.Max('slot_number')
        )['slot_number__max'] or 7
        
        schedules = self.get_all_schedules()
        
        # Create a dict for quick lookup: (day, slot) -> schedule
        schedule_map = {}
        for sch in schedules:
            key = (sch.timeslot.day, sch.timeslot.slot_number)
            schedule_map[key] = sch
        
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        grid = []
        
        for day in days:
            row = []
            for slot in range(1, max_slot + 1):
                schedule = schedule_map.get((day, slot), None)
                row.append(schedule)
            grid.append((day, row))
        
        return grid

    def get_unique_sections(self):
        """Get all unique sections this faculty teaches."""
        return self.get_all_schedules().values_list(
            'section__name', flat=True
        ).distinct()

    def get_unique_subjects(self):
        """Get all unique subjects this faculty teaches."""
        return self.get_all_schedules().values_list(
            'subject__name', flat=True
        ).distinct()

    def get_weekly_load(self):
        """Calculate total teaching hours per week."""
        schedules = self.get_all_schedules()
        return len(schedules)

    def get_schedule_summary(self):
        """
        Get a summary of faculty's teaching load.
        Returns: {
            'total_sessions': int,
            'sections': [...],
            'subjects': [...],
            'weekly_load': int,
            'days_teaching': [...]
        }
        """
        schedules = self.get_all_schedules()
        days_teaching = set(s.timeslot.day for s in schedules)
        
        return {
            'total_sessions': len(schedules),
            'sections': list(self.get_unique_sections()),
            'subjects': list(self.get_unique_subjects()),
            'weekly_load': len(schedules),
            'days_teaching': sorted(list(days_teaching)),
            'workload_limit': self.workload_limit,
            'workload_percentage': int((len(schedules) / self.workload_limit) * 100) if self.workload_limit > 0 else 0,
        }


class FacultySubject(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.faculty} → {self.subject}"

    class Meta:
        unique_together = ('faculty', 'subject')


class FacultyLeave(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    date = models.DateField()
    reason = models.TextField()
    approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.faculty} — {self.date}"

    class Meta:
        ordering = ['-date']


class Room(models.Model):
    name = models.CharField(max_length=50)
    is_lab = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
    ]
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    slot_number = models.IntegerField()

    def __str__(self):
        return f"{self.get_day_display()} — Slot {self.slot_number}"

    class Meta:
        ordering = ['day', 'slot_number']
        unique_together = ('day', 'slot_number')


class Schedule(models.Model):
    """Schedule model representing a single class session"""
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)

    # When two elective subjects run simultaneously, this links the paired entry
    # so the timetable can display them as "Sub-A / Sub-B" in one cell.
    elective_pair = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paired_with',
        help_text="Points to the simultaneously-running elective Schedule entry"
    )

    def __str__(self):
        if self.batch:
            return f"{self.section} — {self.batch} — {self.subject}"
        return f"{self.section} — {self.subject} — {self.timeslot}"

    class Meta:
        ordering = ['timeslot__day', 'timeslot__slot_number']
    
    def display_label(self):
        """
        Return a display label for the timetable cell.
        Format: "SubjectName (Faculty) Room"
        """
        return f"{self.subject.name} ({self.faculty.name}) {self.room.name}"