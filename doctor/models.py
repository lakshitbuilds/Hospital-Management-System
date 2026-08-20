from datetime import datetime, timedelta, time as time_cls

from django.db import models
from django.conf import settings


class Doctor(models.Model):
    DEPARTMENT_CHOICES = (
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('orthopedics', 'Orthopedics'),
        ('pediatrics', 'Pediatrics'),
        ('dermatology', 'Dermatology'),
        ('general', 'General Medicine'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES)
    specialization = models.CharField(max_length=100, blank=True)

    phone_number = models.CharField(max_length=20, blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='doctors/profile_pictures/', blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True)
    registered_since = models.PositiveIntegerField(blank=True, null=True)

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
        if self.blocked_dates.filter(date=appointment_date).exists():
            return {'available': False, 'reason': 'Doctor is on leave (holiday) on this date.', 'slots': []}

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

        booked_slots = set(
            self.appointments.filter(appointment_date=appointment_date)
            .exclude(status='cancelled')
            .values_list('time_slot', flat=True)
        )

        step_minutes = max(self.slot_duration, 1) + max(self.buffer_time, 0)
        current = datetime.combine(appointment_date, start_time)
        end = datetime.combine(appointment_date, end_time)

        slots = []
        while current + timedelta(minutes=self.slot_duration) <= end:
            label = current.strftime('%I:%M %p')
            slots.append({'time': label, 'booked': label in booked_slots})
            if self.max_per_day and len(slots) >= self.max_per_day:
                break
            current += timedelta(minutes=step_minutes)

        return {'available': True, 'reason': None, 'slots': slots}


class DoctorAvailability(models.Model):
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    is_available = models.BooleanField(default=True)
    start_time = models.TimeField(default='09:00')
    end_time = models.TimeField(default='17:00')

    class Meta:
        unique_together = ('doctor', 'day')
        ordering = ['id']

    def __str__(self):
        return f"{self.doctor} - {self.day}"


class BlockedDate(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='blocked_dates')
    date = models.DateField()
    reason = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['date']
        unique_together = ('doctor', 'date')

    def __str__(self):
        return f"{self.doctor} - {self.date}"


class Prescription(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey('patient.Patient', on_delete=models.CASCADE, related_name='prescriptions')
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
    FREQUENCY_CHOICES = (
        ('once_a_day', 'Once a day'),
        ('twice_a_day', 'Twice a day'),
        ('thrice_a_day', 'Thrice a day'),
        ('every_6_hours', 'Every 6 hours'),
        ('every_8_hours', 'Every 8 hours'),
        ('as_needed', 'As needed'),
    )

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50, blank=True)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, blank=True)
    duration = models.CharField(max_length=50, blank=True)
    instructions = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name
