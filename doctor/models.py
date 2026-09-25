"""
Domain models for the doctor-side portal.

This module defines the Doctor profile itself (linked one-to-one to the
shared accounts.User account for users with role='doctor'), the doctor's
weekly availability and one-off blocked (holiday) dates used to compute
bookable appointment slots, and the prescriptions (with their medicine line
items) that a doctor writes for a patient, usually while working through a
specific appointment.
"""
from datetime import datetime, timedelta, time as time_cls

from django.db import models
from django.conf import settings


class Doctor(models.Model):
    """
    A doctor's professional profile, extending the base accounts.User account
    (one-to-one) with hospital-specific details: department/specialization,
    consultation fee, qualifications, and scheduling settings.

    The `consultation_fee` field is read elsewhere in the project when a
    patient/receptionist books an appointment, to auto-create the matching
    Billing record for that appointment.

    Related from other models via reverse FKs: `availability`
    (DoctorAvailability), `blocked_dates` (BlockedDate), `appointments`
    (patient.Appointment), and `prescriptions` (Prescription).
    """
    # Departments this doctor can be assigned to; shown as a dropdown
    # wherever the doctor's profile is edited.
    DEPARTMENT_CHOICES = (
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('orthopedics', 'Orthopedics'),
        ('pediatrics', 'Pediatrics'),
        ('dermatology', 'Dermatology'),
        ('general', 'General Medicine'),
    )

    # Links this profile to the shared accounts.User row for the doctor
    # (that User's role should be 'doctor'). One doctor <-> one User.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    # Which hospital department the doctor belongs to (see DEPARTMENT_CHOICES above).
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES)
    specialization = models.CharField(max_length=100, blank=True)

    phone_number = models.CharField(max_length=20, blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    # Fee charged per consultation. Used elsewhere in the project (the
    # appointment booking flow) to auto-create the corresponding Billing
    # record when a patient or receptionist books with this doctor.
    consultation_fee = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='doctors/profile_pictures/', blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True)
    registered_since = models.PositiveIntegerField(blank=True, null=True)

    # Scheduling settings used together by get_available_slots() below to
    # generate this doctor's bookable time slots for a given day:
    # slot_duration = length of one appointment slot (minutes),
    # buffer_time = gap left between consecutive slots (minutes),
    # max_per_day = optional cap on how many slots to offer per day.
    slot_duration = models.PositiveIntegerField(default=30)
    buffer_time = models.PositiveIntegerField(default=5)
    max_per_day = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.department}"

    def get_available_slots(self, appointment_date):
        """
        Single source of truth for bookable time slots on a given date, used by
        both the patient and receptionist booking flows. Honors the doctor's
        blocked (holiday) dates and weekly availability/day-off settings, and
        generates slots from start_time/end_time using slot_duration + buffer_time.

        Returns {'available': bool, 'reason': str|None, 'slots': [{'time': '09:00 AM', 'booked': bool}, ...]}
        """
        # A date that's already passed can never be booked, regardless of
        # weekly schedule/holidays -- checked first, before any other rule,
        # since both the patient and receptionist booking views trust this
        # return value as their sole date validation.
        if appointment_date < datetime.now().date():
            return {'available': False, 'reason': 'That date has already passed.', 'slots': []}

        if self.blocked_dates.filter(date=appointment_date).exists():
            return {'available': False, 'reason': 'Doctor is on leave (holiday) on this date.', 'slots': []}

        # Convert the date to a lowercase weekday name ('monday', 'tuesday',
        # ...) matching the DAY_CHOICES keys used by DoctorAvailability, so
        # we can look up this doctor's saved schedule for that weekday.
        day_key = appointment_date.strftime('%A').lower()
        day_schedule = self.availability.filter(day=day_key).first()

        if day_schedule is None:
            # No explicit schedule saved yet for this weekday -- fall back to the
            # model's own defaults (09:00-17:00, available) rather than treating
            # an unconfigured day as closed.
            start_time, end_time = time_cls(9, 0), time_cls(17, 0)
        elif not day_schedule.is_available:
            return {'available': False, 'reason': 'Doctor does not see patients on this day of the week.', 'slots': []}
        else:
            start_time, end_time = day_schedule.start_time, day_schedule.end_time

        # Collect the time-slot labels already taken by this doctor on this
        # date (ignoring cancelled appointments, since a cancelled slot frees
        # back up) so they can be flagged as booked below.
        booked_slots = set(
            self.appointments.filter(appointment_date=appointment_date)
            .exclude(status='cancelled')
            .values_list('time_slot', flat=True)
        )

        # Each slot is slot_duration minutes long, followed by a buffer_time
        # gap before the next slot starts.
        step_minutes = max(self.slot_duration, 1) + max(self.buffer_time, 0)
        current = datetime.combine(appointment_date, start_time)
        end = datetime.combine(appointment_date, end_time)

        # When booking for today, a slot that has already started is no
        # longer something a patient/receptionist can walk into -- skip it
        # rather than offering a same-day slot in the past.
        now = datetime.now()
        is_today = appointment_date == now.date()

        # Walk forward from start_time to end_time in step_minutes
        # increments, emitting one slot per iteration (marked booked/free)
        # until there's no more room for a full slot_duration block before
        # end_time, or the optional max_per_day cap is reached. Past slots
        # (today only) are skipped entirely rather than counted toward
        # max_per_day, so a doctor's daily cap still reflects real,
        # bookable slots.
        slots = []
        while current + timedelta(minutes=self.slot_duration) <= end:
            if not (is_today and current < now):
                label = current.strftime('%I:%M %p')
                slots.append({'time': label, 'booked': label in booked_slots})
                if self.max_per_day and len(slots) >= self.max_per_day:
                    break
            current += timedelta(minutes=step_minutes)

        if is_today and not slots:
            return {'available': False, 'reason': 'No more slots available today.', 'slots': []}

        return {'available': True, 'reason': None, 'slots': slots}


class DoctorAvailability(models.Model):
    """
    One doctor's recurring weekly schedule for a single day of the week
    (e.g. "Dr. X is available Monday 09:00-17:00"). There is exactly one row
    per (doctor, day) pair -- enforced by unique_together below. This is
    read by Doctor.get_available_slots() to know the working hours (or
    day-off status) to generate bookable slots from.
    """
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    # The doctor this weekly schedule entry belongs to; the reverse accessor
    # `doctor.availability` is what get_available_slots() queries.
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    # Whether the doctor sees patients at all on this weekday (unchecked in
    # the availability form means a day off).
    is_available = models.BooleanField(default=True)
    start_time = models.TimeField(default='09:00')
    end_time = models.TimeField(default='17:00')

    class Meta:
        # At most one schedule row per doctor per weekday.
        unique_together = ('doctor', 'day')
        ordering = ['id']

    def __str__(self):
        return f"{self.doctor} - {self.day}"


class BlockedDate(models.Model):
    """
    A single specific date on which a doctor is unavailable (e.g. holiday or
    leave), overriding their normal weekly availability for just that one
    date. Checked first by Doctor.get_available_slots() before it falls
    back to the regular weekly schedule.
    """
    # The doctor who is unavailable on `date`; the reverse accessor
    # `doctor.blocked_dates` is what get_available_slots() queries.
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='blocked_dates')
    date = models.DateField()
    reason = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['date']
        unique_together = ('doctor', 'date')

    def __str__(self):
        return f"{self.doctor} - {self.date}"


class Prescription(models.Model):
    """
    A prescription written by a doctor for a patient: a diagnosis plus
    advice and an optional follow-up date, with the actual medicines stored
    separately as PrescriptionMedicine rows (see `medicines` reverse
    relation). Usually created while the doctor is working through a
    specific appointment, but `appointment` is optional so a prescription
    can still exist without one.
    """
    # Doctor who wrote this prescription.
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    # The patient (patient.Patient profile, not the raw User) this
    # prescription is for.
    patient = models.ForeignKey('patient.Patient', on_delete=models.CASCADE, related_name='prescriptions')
    # Optional link to the specific appointment this was written during.
    # SET_NULL means if that appointment is ever deleted, this prescription
    # is kept but simply loses the link, rather than being deleted too.
    appointment = models.ForeignKey('patient.Appointment', on_delete=models.SET_NULL, related_name='prescriptions', blank=True, null=True)
    diagnosis = models.TextField()
    advice = models.TextField(blank=True)
    follow_up_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient} - {self.diagnosis[:40]}"


class PrescriptionMedicine(models.Model):
    """
    A single medicine line item belonging to a Prescription (name, dosage,
    frequency, duration, instructions). A Prescription typically has several
    of these -- accessible via its `medicines` reverse relation -- one per
    medicine the doctor prescribed.
    """
    FREQUENCY_CHOICES = (
        ('once_a_day', 'Once a day'),
        ('twice_a_day', 'Twice a day'),
        ('thrice_a_day', 'Thrice a day'),
        ('every_6_hours', 'Every 6 hours'),
        ('every_8_hours', 'Every 8 hours'),
        ('as_needed', 'As needed'),
    )

    # The parent prescription this medicine line item belongs to.
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50, blank=True)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, blank=True)
    duration = models.CharField(max_length=50, blank=True)
    instructions = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name
