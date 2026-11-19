"""
engine.py — EduSchedule Timetable Generation Engine (v14 — Elective Same-Day Stacking Fix)

v14 change: schedule_electives() was missing a `break` after a successful
placement inside its slot loop. The `placed_days` set and the day-level
`if day in placed_days: continue` check make it clear the intent was
"place at most one session of this elective pair per day, spread across
`target` distinct days." But without the break, once a session was placed
in one slot, the inner loop kept trying *other* slots on that same day —
and if faculty/rooms were free, it would keep stacking more sessions of
the same pair onto that single day until `placed >= target` was reached.
That's exactly what produced the "SUBJECT REPEAT >2×" validation failures
on every elective subject (Cloud Security, NLP, IoT Security, Web and
Social Media Analytics, Ethical Hacking, Data Science for Engineers) —
they were hitting their weekly_hours target in 1 day instead of 3.
"""

import random
from django.db import transaction
from .models import (
    Schedule, Section, Subject, Batch, TimeSlot,
    Room, FacultySubject, Faculty, FacultyLeave
)

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]


# ─────────────────────────────────────────────
# SLOT HELPERS
# ─────────────────────────────────────────────

def get_existing_slot_numbers():
    """Return sorted unique slot numbers existing in DB."""
    return sorted(
        list(set(TimeSlot.objects.order_by().values_list('slot_number', flat=True)))
    )


def get_valid_lab_pairs():
    """Returns consecutive slot pairs for 2-hour lab blocks."""
    existing = set(get_existing_slot_numbers())
    preferred_pairs = [(5, 6), (6, 7)]
    return [p for p in preferred_pairs if p[0] in existing and p[1] in existing]


# ─────────────────────────────────────────────
# TIMESLOT CACHE
# ─────────────────────────────────────────────
_ts_cache = {}


def get_timeslot(day, slot_number):
    key = (day, slot_number)
    if key not in _ts_cache:
        _ts_cache[key] = TimeSlot.objects.filter(
            day=day, slot_number=slot_number
        ).first()
    return _ts_cache[key]


# ─────────────────────────────────────────────
# CONFLICT TRACKER
# ─────────────────────────────────────────────
class ConflictTracker:
    def __init__(self):
        self.faculty_busy      = set()
        self.room_busy         = set()
        self.section_busy      = set()
        self.subject_day_count = {}
        self.faculty_count     = {}
        self.batch_busy        = set()

    def faculty_available(self, fid, day, slot):
        return (fid, day, slot) not in self.faculty_busy

    def room_available(self, rid, day, slot):
        return (rid, day, slot) not in self.room_busy

    def section_slot_free(self, sid, day, slot):
        return (sid, day, slot) not in self.section_busy

    def subject_count_today(self, sec_id, sub_id, day):
        return self.subject_day_count.get((sec_id, sub_id, day), 0)

    def faculty_under_limit(self, fid, limit):
        return self.faculty_count.get(fid, 0) < limit

    def faculty_within_overflow(self, fid, limit, overflow=1):
        """Allow overflow for gap filling."""
        return self.faculty_count.get(fid, 0) < limit + overflow

    def batch_available(self, bid, day, slot):
        return (bid, day, slot) not in self.batch_busy

    def mark_theory(self, sec_id, sub_id, fid, rid, day, slot):
        self.faculty_busy.add((fid, day, slot))
        self.room_busy.add((rid, day, slot))
        self.section_busy.add((sec_id, day, slot))
        key = (sec_id, sub_id, day)
        self.subject_day_count[key] = self.subject_day_count.get(key, 0) + 1
        self.faculty_count[fid] = self.faculty_count.get(fid, 0) + 1

    def mark_lab_slot(self, sec_id, sub_id, fid, rid, day, slot):
        self.faculty_busy.add((fid, day, slot))
        self.room_busy.add((rid, day, slot))
        self.section_busy.add((sec_id, day, slot))
        self.faculty_count[fid] = self.faculty_count.get(fid, 0) + 1

    def mark_batch(self, bid, day, slot):
        if bid is not None:
            self.batch_busy.add((bid, day, slot))


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _on_leave_ids():
    return set(
        FacultyLeave.objects.filter(approved=True)
        .values_list('faculty_id', flat=True)
    )


def pick_faculty(subject, day, slot, tracker, exclude_ids=None, allow_overflow=False, overflow_limit=1):
    """Least-loaded eligible faculty available for a single slot."""
    exclude_ids = (exclude_ids or set()) | _on_leave_ids()
    candidates = []
    
    for fs in FacultySubject.objects.filter(subject=subject).select_related('faculty'):
        if fs.faculty_id in exclude_ids:
            continue
        if not tracker.faculty_available(fs.faculty.id, day, slot):
            continue
        
        if allow_overflow:
            if tracker.faculty_within_overflow(fs.faculty.id, fs.faculty.workload_limit, overflow_limit):
                candidates.append(fs.faculty)
        else:
            if tracker.faculty_under_limit(fs.faculty.id, fs.faculty.workload_limit):
                candidates.append(fs.faculty)
    
    return (
        min(candidates, key=lambda f: tracker.faculty_count.get(f.id, 0))
        if candidates else None
    )


def pick_lab_faculty(subject, day, slot1, slot2, tracker, exclude_ids=None, allow_overflow=False, overflow_limit=1):
    """Faculty free for BOTH consecutive lab slots."""
    exclude_ids = (exclude_ids or set()) | _on_leave_ids()
    candidates = []
    
    for fs in FacultySubject.objects.filter(subject=subject).select_related('faculty'):
        if fs.faculty_id in exclude_ids:
            continue
        if not tracker.faculty_available(fs.faculty.id, day, slot1):
            continue
        if not tracker.faculty_available(fs.faculty.id, day, slot2):
            continue
        
        if allow_overflow:
            if tracker.faculty_within_overflow(fs.faculty.id, fs.faculty.workload_limit, overflow_limit):
                candidates.append(fs.faculty)
        else:
            if tracker.faculty_under_limit(fs.faculty.id, fs.faculty.workload_limit):
                candidates.append(fs.faculty)
    
    return (
        min(candidates, key=lambda f: tracker.faculty_count.get(f.id, 0))
        if candidates else None
    )


def pick_room(is_lab, day, slot, tracker, exclude_ids=None):
    """First free room of the correct type."""
    exclude_ids = exclude_ids or set()
    for room in Room.objects.filter(is_lab=is_lab).exclude(id__in=exclude_ids):
        if tracker.room_available(room.id, day, slot):
            return room
    return None


def pick_room_for_section(section, day, slot, tracker, section_rooms, exclude_ids=None, allow_fallback=False):
    """
    Room picker for a section's ORDINARY (non-lab) theory classes.

    Each section is assigned exactly one fixed classroom (section_rooms),
    so every regular theory session for that section happens in the same
    room all week — only lab sessions (and the second parallel room
    needed for elective pairs) use a different room.

    allow_fallback=True lets the emergency/final-resort safety nets fall
    back to any other free non-lab room rather than leave a slot empty;
    the normal scheduling passes keep this False so the "one room per
    section" rule holds whenever possible.
    """
    exclude_ids = exclude_ids or set()
    assigned = section_rooms.get(section.id)

    if assigned and assigned.id not in exclude_ids and tracker.room_available(assigned.id, day, slot):
        return assigned

    if allow_fallback:
        return pick_room(is_lab=False, day=day, slot=slot, tracker=tracker, exclude_ids=exclude_ids)

    return None


def pick_lab_room(day, slot1, slot2, tracker, exclude_ids=None):
    """Lab room free for BOTH consecutive slots."""
    exclude_ids = exclude_ids or set()
    for room in Room.objects.filter(is_lab=True).exclude(id__in=exclude_ids):
        if (tracker.room_available(room.id, day, slot1) and
                tracker.room_available(room.id, day, slot2)):
            return room
    return None


# ─────────────────────────────────────────────
# CAPACITY ANALYSIS
# ─────────────────────────────────────────────

def analyze_faculty_capacity(sections, log):
    """Analyze overall faculty capacity against required sessions."""
    log.append("\n📊 CAPACITY ANALYSIS...")
    
    total_required = 0
    for section in sections:
        subjects = Subject.objects.filter(semester=section.semester)
        for subject in subjects:
            if not subject.is_lab:
                total_required += subject.weekly_hours
    
    total_capacity = 0
    faculty_list = Faculty.objects.all()
    for faculty in faculty_list:
        total_capacity += faculty.workload_limit
    
    log.append(f"  📋 Total theory/elective sessions required: {total_required}")
    log.append(f"  👥 Total faculty capacity available: {total_capacity}")
    
    if total_capacity >= total_required:
        log.append(f"  ✅ Capacity OK (margin: +{total_capacity - total_required})")
        return None
    else:
        shortage = total_required - total_capacity
        overflow_needed = (shortage // len(faculty_list)) + 2 if faculty_list else 5
        log.append(f"  ⚠️ SHORTAGE DETECTED: need +{shortage} sessions")
        log.append(f"     Recommended overflow per faculty: +{overflow_needed}")
        return overflow_needed


# ─────────────────────────────────────────────
# FIXED THEORY ROOM PER SECTION
# ─────────────────────────────────────────────

def assign_section_theory_rooms(sections, log):
    """
    Give every section exactly one non-lab classroom that will host ALL
    of its ordinary theory classes for the week. Labs continue to use
    whichever lab room is free (via pick_lab_room), and elective pairs
    still need a second, different room for the parallel session — but
    plain theory classes for a section always land in this one room.

    Rooms are handed out round-robin across sections so load is spread
    across the available non-lab classrooms; if there are more sections
    than non-lab rooms, rooms are reused (the conflict tracker still
    prevents two sections from double-booking the same room/slot).
    """
    theory_rooms = list(Room.objects.filter(is_lab=False))
    assignment = {}

    if not theory_rooms:
        log.append("  ⚠ No non-lab rooms found — cannot assign fixed theory rooms.")
        return assignment

    for i, section in enumerate(sections):
        room = theory_rooms[i % len(theory_rooms)]
        assignment[section.id] = room
        log.append(f"  🏫 {section.name} → fixed theory room: {room.name}")

    return assignment


# ─────────────────────────────────────────────
# LAB SCHEDULING
# ─────────────────────────────────────────────

def schedule_labs(sections, tracker, available_slots, log):
    for section in sections:
        labs = list(Subject.objects.filter(semester=section.semester, is_lab=True))
        if not labs:
            log.append(f"  ℹ No lab subjects for {section.name}")
            continue

        batches = list(Batch.objects.filter(section=section))
        batch1 = batches[0] if batches else None
        has_two_batches = len(batches) >= 2

        lab_pairs = []
        i = 0
        while i < len(labs):
            if i + 1 < len(labs):
                lab_pairs.append((labs[i], labs[i + 1]))
                i += 2
            else:
                lab_pairs.append((labs[i], None))
                i += 1

        days_used = set()
        shuffled_days = DAYS[:]
        random.shuffle(shuffled_days)
        lab_slot_pairs = get_valid_lab_pairs()

        if not lab_slot_pairs:
            log.append("  ⚠ No valid lab slot pairs (need slots 5+6 or 6+7)")
            continue

        for lab_a, lab_b in lab_pairs:
            placed = False
            for day in shuffled_days:
                if day in days_used:
                    continue
                for s1, s2 in lab_slot_pairs:
                    if s1 not in available_slots or s2 not in available_slots:
                        continue
                    t1 = get_timeslot(day, s1)
                    t2 = get_timeslot(day, s2)
                    if not t1 or not t2:
                        continue
                    if not (tracker.section_slot_free(section.id, day, s1) and
                            tracker.section_slot_free(section.id, day, s2)):
                        continue

                    fac_a = pick_lab_faculty(lab_a, day, s1, s2, tracker)
                    if not fac_a:
                        continue
                    room_a = pick_lab_room(day, s1, s2, tracker)
                    if not room_a:
                        continue

                    fac_b = room_b = batch2 = None
                    if lab_b and has_two_batches:
                        fac_b = pick_lab_faculty(
                            lab_b, day, s1, s2, tracker, exclude_ids={fac_a.id}
                        )
                        if not fac_b:
                            continue
                        room_b = pick_lab_room(day, s1, s2, tracker, exclude_ids={room_a.id})
                        if not room_b:
                            continue
                        batch2 = batches[1]

                    for slot_num, ts in [(s1, t1), (s2, t2)]:
                        Schedule.objects.create(
                            section=section, batch=batch1, subject=lab_a,
                            faculty=fac_a, room=room_a, timeslot=ts,
                        )
                        tracker.mark_lab_slot(
                            section.id, lab_a.id, fac_a.id, room_a.id, day, slot_num
                        )
                        tracker.mark_batch(batch1.id if batch1 else None, day, slot_num)

                        if lab_b and fac_b and room_b and batch2:
                            Schedule.objects.create(
                                section=section, batch=batch2, subject=lab_b,
                                faculty=fac_b, room=room_b, timeslot=ts,
                            )
                            tracker.mark_lab_slot(
                                section.id, lab_b.id, fac_b.id, room_b.id, day, slot_num
                            )
                            tracker.mark_batch(batch2.id, day, slot_num)

                    days_used.add(day)
                    placed = True
                    log.append(f"  ✅ LAB [{lab_a.name}] → {section.name}")
                    break
                if placed:
                    break

            if not placed:
                log.append(f"  ⚠ FAILED lab [{lab_a.name}] for {section.name}")


# ─────────────────────────────────────────────
# ELECTIVE SCHEDULING
# ─────────────────────────────────────────────

def schedule_electives(sections, tracker, available_slots, log, section_rooms):
    for section in sections:
        if section.semester.number < 5:
            continue

        electives = list(
            Subject.objects.filter(
                semester=section.semester,
                is_lab=False, is_elective=True,
                elective_group__isnull=False,
            ).order_by('elective_group', 'name')
        )
        if not electives:
            continue

        groups = {}
        for sub in electives:
            groups.setdefault(sub.elective_group, []).append(sub)

        for group_id, pair in groups.items():
            if len(pair) < 2:
                log.append(f"  ⚠ Elective group {group_id} has only 1 subject")
                continue

            sub_a, sub_b = pair[0], pair[1]
            target = sub_a.weekly_hours
            placed = 0
            placed_days = set()
            shuffled_days = DAYS[:]
            random.shuffle(shuffled_days)

            for day in shuffled_days:
                if placed >= target:
                    break
                if day in placed_days:
                    continue

                slots_to_try = list(available_slots)
                random.shuffle(slots_to_try)

                for slot in slots_to_try:
                    if placed >= target:
                        break
                    t = get_timeslot(day, slot)
                    if not t or not tracker.section_slot_free(section.id, day, slot):
                        continue

                    fac_a = pick_faculty(sub_a, day, slot, tracker)
                    if not fac_a:
                        continue
                    # sub_a keeps the section's usual classroom whenever it's
                    # free; sub_b (the parallel elective) needs a different
                    # room since both run at the same time.
                    room_a = pick_room_for_section(
                        section, day, slot, tracker, section_rooms, allow_fallback=True
                    )
                    if not room_a:
                        continue
                    fac_b = pick_faculty(sub_b, day, slot, tracker, exclude_ids={fac_a.id})
                    if not fac_b:
                        continue
                    room_b = pick_room(is_lab=False, day=day, slot=slot, tracker=tracker, exclude_ids={room_a.id})
                    if not room_b:
                        continue

                    entry_a = Schedule.objects.create(
                        section=section, subject=sub_a, faculty=fac_a, room=room_a, timeslot=t,
                    )
                    entry_b = Schedule.objects.create(
                        section=section, subject=sub_b, faculty=fac_b, room=room_b, timeslot=t,
                        elective_pair=entry_a,
                    )
                    entry_a.elective_pair = entry_b
                    entry_a.save(update_fields=['elective_pair'])

                    tracker.mark_theory(section.id, sub_a.id, fac_a.id, room_a.id, day, slot)
                    tracker.mark_theory(section.id, sub_b.id, fac_b.id, room_b.id, day, slot)
                    placed_days.add(day)
                    placed += 1
                    # FIX (v14): stop trying more slots today once this day's
                    # session is placed — move on to the next day instead of
                    # stacking every remaining session onto today. This is what
                    # was missing and caused the >2×/day violations.
                    break

            if placed < target:
                log.append(f"  ⚠ Elective [{sub_a.name}] {section.name}: {placed}/{target}")


# ─────────────────────────────────────────────
# THEORY SCHEDULING
# ─────────────────────────────────────────────

def schedule_theory(sections, tracker, available_slots, log, section_rooms):
    for section in sections:
        theory_subjects = list(Subject.objects.filter(
            semester=section.semester, is_lab=False, is_elective=False,
        ))
        theory_subjects.sort(key=lambda s: -s.weekly_hours)

        for subject in theory_subjects:
            target = subject.weekly_hours
            placed = 0

            # Pass 1: Maximum 1 session per day
            shuffled_days = DAYS[:]
            random.shuffle(shuffled_days)

            for day in shuffled_days:
                if placed >= target:
                    break
                if tracker.subject_count_today(section.id, subject.id, day) >= 1:
                    continue

                shuffled_slots = list(available_slots)
                random.shuffle(shuffled_slots)

                for slot in shuffled_slots:
                    if not tracker.section_slot_free(section.id, day, slot):
                        continue
                    t = get_timeslot(day, slot)
                    if not t:
                        continue
                    fac = pick_faculty(subject, day, slot, tracker)
                    if not fac:
                        continue
                    room = pick_room_for_section(section, day, slot, tracker, section_rooms)
                    if not room:
                        continue

                    Schedule.objects.create(
                        section=section, subject=subject, faculty=fac, room=room, timeslot=t,
                    )
                    tracker.mark_theory(section.id, subject.id, fac.id, room.id, day, slot)
                    placed += 1
                    break

            # Pass 2: Allow up to 2 sessions per day if needed
            if placed < target:
                shuffled_days = DAYS[:]
                random.shuffle(shuffled_days)

                for day in shuffled_days:
                    if placed >= target:
                        break
                    if tracker.subject_count_today(section.id, subject.id, day) >= 2:
                        continue

                    shuffled_slots = list(available_slots)
                    random.shuffle(shuffled_slots)

                    for slot in shuffled_slots:
                        if placed >= target:
                            break
                        if tracker.subject_count_today(section.id, subject.id, day) >= 2:
                            break
                        if not tracker.section_slot_free(section.id, day, slot):
                            continue
                        t = get_timeslot(day, slot)
                        if not t:
                            continue
                        fac = pick_faculty(subject, day, slot, tracker)
                        if not fac:
                            continue
                        room = pick_room_for_section(section, day, slot, tracker, section_rooms)
                        if not room:
                            continue

                        Schedule.objects.create(
                            section=section, subject=subject, faculty=fac, room=room, timeslot=t,
                        )
                        tracker.mark_theory(section.id, subject.id, fac.id, room.id, day, slot)
                        placed += 1


# ─────────────────────────────────────────────
# FAIRNESS PASS
# ─────────────────────────────────────────────

def fairness_pass(sections, tracker, available_slots, log, section_rooms):
    log.append("\n🔄 FAIRNESS PASS...")
    revisions_made = 0
    
    for section in sections:
        theory_subjects = list(Subject.objects.filter(
            semester=section.semester, is_lab=False, is_elective=False,
        ))
        
        for subject in theory_subjects:
            existing = Schedule.objects.filter(
                section=section, subject=subject, date__isnull=True, batch__isnull=True
            ).count()
            target = subject.weekly_hours
            
            if existing >= target:
                continue
            
            needed = target - existing
            placed_now = 0
            shuffled_days = DAYS[:]
            random.shuffle(shuffled_days)
            
            for day in shuffled_days:
                if placed_now >= needed:
                    break
                if tracker.subject_count_today(section.id, subject.id, day) >= 2:
                    continue
                
                shuffled_slots = list(available_slots)
                random.shuffle(shuffled_slots)
                
                for slot in shuffled_slots:
                    if placed_now >= needed or tracker.subject_count_today(section.id, subject.id, day) >= 2:
                        break
                    if not tracker.section_slot_free(section.id, day, slot):
                        continue
                    
                    t = get_timeslot(day, slot)
                    if not t:
                        continue
                    
                    fac = pick_faculty(subject, day, slot, tracker)
                    if not fac:
                        continue
                    room = pick_room_for_section(section, day, slot, tracker, section_rooms)
                    if not room:
                        continue
                    
                    Schedule.objects.create(section=section, subject=subject, faculty=fac, room=room, timeslot=t)
                    tracker.mark_theory(section.id, subject.id, fac.id, room.id, day, slot)
                    placed_now += 1
                    revisions_made += 1
    
    if revisions_made > 0:
        log.append(f"  ✅ Fairness pass: {revisions_made} sessions placed")


# ─────────────────────────────────────────────
# EMERGENCY GAP FILLER
# ─────────────────────────────────────────────

def emergency_gap_filler(sections, tracker, available_slots, log, section_rooms, adaptive_overflow=None):
    log.append("\n🚨 EMERGENCY GAP FILLER...")
    
    gap_count_before = 0
    gaps_filled = 0
    overflow_sessions = 0
    
    for section in sections:
        for day in DAYS:
            for slot in available_slots:
                if tracker.section_slot_free(section.id, day, slot):
                    gap_count_before += 1
    
    if adaptive_overflow is None:
        if gap_count_before > 20:
            adaptive_overflow = 5
        elif gap_count_before > 10:
            adaptive_overflow = 3
        else:
            adaptive_overflow = 2
    
    log.append(f"  Initial gaps: {gap_count_before} | Using overflow limit: +{adaptive_overflow}")
    
    for section in sections:
        theory_subjects = list(Subject.objects.filter(
            semester=section.semester, is_lab=False, is_elective=False,
        ))
        
        subject_needs = {}
        for subject in theory_subjects:
            existing = Schedule.objects.filter(
                section=section, subject=subject, date__isnull=True, batch__isnull=True
            ).count()
            target = subject.weekly_hours
            if existing < target:
                subject_needs[subject.id] = (subject, target - existing)
        
        if not subject_needs:
            continue
        
        shuffled_days = DAYS[:]
        random.shuffle(shuffled_days)
        
        for day in shuffled_days:
            shuffled_slots = list(available_slots)
            random.shuffle(shuffled_slots)
            
            for slot in shuffled_slots:
                if not tracker.section_slot_free(section.id, day, slot):
                    continue
                
                best_subject = None
                for sub_id, (subject, needed) in list(subject_needs.items()):
                    # STRICT GUARANTEE: Never exceed 2 sessions per day for a section
                    if tracker.subject_count_today(section.id, subject.id, day) >= 2:
                        continue
                    best_subject = subject
                    break
                
                if not best_subject:
                    continue
                
                t = get_timeslot(day, slot)
                if not t:
                    continue
                
                fac = pick_faculty(best_subject, day, slot, tracker, allow_overflow=False)
                
                if not fac:
                    fac = pick_faculty(
                        best_subject, day, slot, tracker, 
                        allow_overflow=True, overflow_limit=adaptive_overflow
                    )
                    if fac:
                        overflow_sessions += 1
                
                if not fac:
                    continue
                
                room = pick_room_for_section(
                    section, day, slot, tracker, section_rooms, allow_fallback=True
                )
                if not room:
                    continue
                
                Schedule.objects.create(
                    section=section, subject=best_subject, faculty=fac, room=room, timeslot=t,
                )
                tracker.mark_theory(section.id, best_subject.id, fac.id, room.id, day, slot)
                gaps_filled += 1
                
                subject_needs[best_subject.id] = (best_subject, subject_needs[best_subject.id][1] - 1)
                if subject_needs[best_subject.id][1] <= 0:
                    del subject_needs[best_subject.id]
    
    gap_count_after = 0
    for section in sections:
        for day in DAYS:
            for slot in available_slots:
                if tracker.section_slot_free(section.id, day, slot):
                    gap_count_after += 1
    
    log.append(
        f"  📊 Gaps filled: {gaps_filled} | Overflow: {overflow_sessions} | "
        f"Remaining: {gap_count_after}/{gap_count_before}"
    )
    
    if gap_count_after == 0:
        log.append(f"  🎉 ALL GAPS FILLED!")
    else:
        log.append(f"  ⚠ {gap_count_after} gaps remain")
    
    return gap_count_after


# ─────────────────────────────────────────────
# FINAL RESORT FILL (STRICT MAX-2 PER DAY GUARANTEE)
# ─────────────────────────────────────────────

def final_resort_fill(sections, tracker, available_slots, log, section_rooms):
    """
    LAST RESORT: Fill remaining empty slots while strictly guaranteeing
    subject_count_today < 2 to prevent constraint violations.
    """
    gap_count_before = 0
    for section in sections:
        for day in DAYS:
            for slot in available_slots:
                if tracker.section_slot_free(section.id, day, slot):
                    gap_count_before += 1
    
    if gap_count_before == 0:
        return
    
    log.append(f"\n💀 FINAL RESORT FILL — Filling remaining gaps safely...")
    gaps_filled = 0
    
    for section in sections:
        theory_subjects = list(Subject.objects.filter(
            semester=section.semester, is_lab=False, is_elective=False,
        ))
        
        for day in DAYS:
            for slot in available_slots:
                if not tracker.section_slot_free(section.id, day, slot):
                    continue
                
                t = get_timeslot(day, slot)
                if not t:
                    continue
                
                # Pick any subject for this section that has NOT hit the 2-per-day limit
                chosen_subject = None
                chosen_fac = None
                
                for subject in theory_subjects:
                    if tracker.subject_count_today(section.id, subject.id, day) >= 2:
                        continue
                    
                    # Try to find any available faculty for this subject
                    for fs in FacultySubject.objects.filter(subject=subject).select_related('faculty'):
                        if tracker.faculty_available(fs.faculty.id, day, slot):
                            chosen_subject = subject
                            chosen_fac = fs.faculty
                            break
                    if chosen_subject:
                        break
                
                if not chosen_subject or not chosen_fac:
                    continue
                
                room = pick_room_for_section(
                    section, day, slot, tracker, section_rooms, allow_fallback=True
                )
                if not room:
                    continue
                
                Schedule.objects.create(
                    section=section, subject=chosen_subject, faculty=chosen_fac, room=room, timeslot=t,
                )
                tracker.mark_theory(section.id, chosen_subject.id, chosen_fac.id, room.id, day, slot)
                gaps_filled += 1
    
    log.append(f"  ✅ Final resort safely filled {gaps_filled} gaps")


# ─────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────

def validate_timetable():
    violations = []
    seen_faculty = {}
    seen_room = {}
    seen_batch_slot = {}
    seen_sub_day = {}
    theory_rows_by_slot = {}

    all_rows = list(
        Schedule.objects.filter(date__isnull=True).select_related(
            'section', 'subject', 'faculty', 'room', 'timeslot', 'elective_pair'
        )
    )

    for s in all_rows:
        day = s.timeslot.day
        slot = s.timeslot.slot_number

        fk = (s.faculty_id, day, slot)
        if fk in seen_faculty:
            violations.append(f"FACULTY CLASH: {s.faculty.name} at {day} slot {slot}")
        seen_faculty[fk] = s.id

        rk = (s.room_id, day, slot)
        if rk in seen_room:
            violations.append(f"ROOM CLASH: {s.room.name} at {day} slot {slot}")
        seen_room[rk] = s.id

        if s.batch_id is None:
            sk = (s.section_id, day, slot)
            theory_rows_by_slot.setdefault(sk, []).append(s)
        else:
            bk = (s.section_id, s.batch_id, day, slot)
            if bk in seen_batch_slot:
                violations.append(f"BATCH CLASH: {s.section.name} at {day} slot {slot}")
            seen_batch_slot[bk] = s.id

        subk = (s.section_id, s.subject_id, day, s.batch_id)
        seen_sub_day[subk] = seen_sub_day.get(subk, 0) + 1
        if seen_sub_day[subk] > 2:
            violations.append(f"SUBJECT REPEAT >2×: {s.subject.name} in {s.section.name}")

    for (section_id, day, slot), rows in theory_rows_by_slot.items():
        if len(rows) == 1:
            continue
        if len(rows) == 2:
            r1, r2 = rows
            if r1.subject_id == r2.subject_id or r1.faculty_id == r2.faculty_id:
                violations.append(
                    f"SECTION CLASH: {r1.section.name} at {day} slot {slot}"
                )
        else:
            violations.append(
                f"SECTION CLASH: {rows[0].section.name} at {day} slot {slot} — {len(rows)} rows"
            )

    return violations


def check_missing_faculty_mappings(sections, log):
    log.append("\n🔗 Checking faculty-subject mappings...")
    issues = 0
    
    for section in sections:
        subjects = Subject.objects.filter(semester=section.semester)
        for subject in subjects:
            fac_count = FacultySubject.objects.filter(subject=subject).count()
            if fac_count == 0:
                log.append(
                    f"  ⚠ NO FACULTY MAPPED: [{subject.name}] "
                    f"(semester {section.semester.number})"
                )
                issues += 1
    
    if issues == 0:
        log.append(f"  ✅ All subjects have faculty mappings")


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def generate_timetable():
    _ts_cache.clear()
    log = []

    try:
        with transaction.atomic():
            deleted, _ = Schedule.objects.filter(date__isnull=True).delete()
            log.append(f"🗑 Cleared {deleted} existing entries.")

            sections = list(Section.objects.select_related('semester').all())
            if not sections:
                return False, "No sections found."

            log.append(f"📋 {len(sections)} section(s): {', '.join(s.name for s in sections)}")

            available_slots = get_existing_slot_numbers()
            log.append(f"⏰ Slots: {available_slots}")

            if not available_slots:
                return False, "No TimeSlots in DB."

            check_missing_faculty_mappings(sections, log)
            
            recommended_overflow = analyze_faculty_capacity(sections, log)

            tracker = ConflictTracker()

            log.append("\n🏫 Assigning fixed theory rooms per section...")
            section_rooms = assign_section_theory_rooms(sections, log)

            log.append("\n📐 Scheduling Labs...")
            schedule_labs(sections, tracker, available_slots, log)

            log.append("\n🎯 Scheduling Electives...")
            schedule_electives(sections, tracker, available_slots, log, section_rooms)

            log.append("\n📚 Scheduling Theory...")
            schedule_theory(sections, tracker, available_slots, log, section_rooms)

            log.append("\n🔄 Fairness Pass...")
            fairness_pass(sections, tracker, available_slots, log, section_rooms)

            log.append("\n🚨 Emergency Gap Filler...")
            gaps_remaining = emergency_gap_filler(
                sections, tracker, available_slots, log, section_rooms,
                adaptive_overflow=recommended_overflow
            )

            if gaps_remaining > 0:
                final_resort_fill(sections, tracker, available_slots, log, section_rooms)

            log.append("\n🔍 Validating...")
            violations = validate_timetable()
            if violations:
                log.append(f"\n❌ {len(violations)} violation(s):")
                for v in violations:
                    log.append(f"   • {v}")
                raise Exception("Constraint violations detected.")

            total = Schedule.objects.filter(date__isnull=True).count()
            log.append(f"\n✅ SUCCESS! {total} schedule entries created.")

    except Exception as e:
        log.append(f"\n💥 {e}")
        return False, "\n".join(log)

    return True, "\n".join(log)


# ─────────────────────────────────────────────
# DYNAMIC SUBSTITUTION
# ─────────────────────────────────────────────

def substitute_for_leave(leave):
    WEEKDAY_MAP = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
    leave_day = WEEKDAY_MAP.get(leave.date.weekday())
    if not leave_day:
        return []

    affected = Schedule.objects.filter(
        faculty=leave.faculty, timeslot__day=leave_day, date__isnull=True,
    ).select_related('subject', 'timeslot', 'room', 'section', 'batch')

    tracker = ConflictTracker()
    for s in Schedule.objects.filter(date=leave.date).select_related('timeslot'):
        tracker.faculty_busy.add((s.faculty_id, s.timeslot.day, s.timeslot.slot_number))

    results = []
    for entry in affected:
        day = entry.timeslot.day
        slot = entry.timeslot.slot_number
        sub_fac = pick_faculty(entry.subject, day, slot, tracker, exclude_ids={entry.faculty_id})
        if sub_fac:
            Schedule.objects.create(
                section=entry.section, batch=entry.batch, subject=entry.subject,
                faculty=sub_fac, room=entry.room, timeslot=entry.timeslot, date=leave.date,
            )
            tracker.faculty_busy.add((sub_fac.id, day, slot))
        results.append((entry, sub_fac))

    return results