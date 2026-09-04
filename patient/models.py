"""
Database models for the ``patient`` app.

This module defines the core clinical/administrative entities that revolve
around a patient:

- ``Patient``: the patient's profile, one-to-one with the shared
  ``accounts.User`` account (email-based login, ``role='patient'``).
- ``Appointment``: a booking that links a ``Patient`` to a ``doctor.Doctor``.
- ``Billing``: a charge tied to a specific ``Appointment`` (and its
  ``Patient``), used by the "pay at the front desk" billing checkpoint that
  runs when a patient confirms a self-booked appointment.
- ``ContactMessage``: a simple "contact us" form submission, unrelated to
  the other models.
- ``Notification``: an in-app notification shown to any ``User`` (not just
  patients), e.g. appointment confirmations/cancellations.

Note: this project intentionally has no ``forms.py``. All user input is
read directly from ``request.POST`` in the views (raw HTML forms), so these
models are not backed by Django ``ModelForm`` classes.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
# from .models import Doctor



class Patient(models.Model):
    """
    A patient's profile and medical/contact details.

    Represents the real-world patient as a person receiving care. Linked
    one-to-one with the shared ``accounts.User`` account (which holds the
    login email/password and the ``role='patient'`` flag), so all
    authentication lives on ``User`` while this model holds patient-specific
    data. Patients can either self-register (via the public registration
    page) or be walk-in registered by front-desk staff, in which case
    ``registered_by`` points to the ``Receptionist`` who created the record.
    """
    # Allowed values for the `gender` field below.
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    )
    # Allowed values for the `blood_group` field below.
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    )

    # One-to-one link to the shared login account (accounts.User). This is
    # where email/password and `role` live; this Patient row only carries
    # the patient-specific profile data.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile'
    )

    # Human-friendly patient identifier (e.g. "PAT000007"), auto-generated
    # in save() below the first time the record is created.
    patient_id = models.CharField(max_length=20, unique=True, blank=True)
    profile_image = models.ImageField(upload_to='patients/profile_images/', blank=True, null=True)
    # Set only when a receptionist creates this patient as a walk-in
    # registration; left null for patients who self-register online.
    registered_by = models.ForeignKey('receptionist.Receptionist', on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_patients')

    phone = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True)

    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True)

    allergies = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-generate the display ID the first time this patient is
        # saved, based on the next available primary key (e.g. id=7 ->
        # "PAT000007"). Left alone on later saves since patient_id is
        # already set by then.
        if not self.patient_id:
            last = Patient.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.patient_id = f"PAT{next_id:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_id} - {self.user.get_full_name() or self.user.username}"

class Appointment(models.Model):
    """
    A booking that links a ``Patient`` to a ``doctor.Doctor`` for a given
    date and time slot. Created either directly by staff, or by a patient
    via the self-service booking flow (``book_appointment`` ->
    ``confirm_appointment_billing`` in ``views.py``), which only creates
    this row once the patient has acknowledged the billing notice.
    """
    # Lifecycle of a booking: starts 'pending', staff can move it to
    # 'confirmed'/'completed'/'cancelled', or the system can mark it
    # 'no_show' if the patient didn't turn up (see Billing.bill_type below).
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    )
    VISIT_TYPE_CHOICES = (
        ('new', 'New Visit'),
        ('follow-up', 'Follow-up Visit'),
    )
    # Department the appointment is booked under; independent of which
    # specialty the chosen doctor actually belongs to.
    DEPARTMENT_CHOICES = (
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('orthopedics', 'Orthopedics'),
        ('pediatrics', 'Pediatrics'),
        ('dermatology', 'Dermatology'),
        ('general', 'General Medicine'),
    )

    # The patient who booked/owns this appointment.
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    # The doctor the appointment is booked with.
    doctor = models.ForeignKey('doctor.Doctor', on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    time_slot = models.CharField(max_length=20)
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES, default='new')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, default='general')
    # Set by the send_appointment_reminders management command once a
    # "tomorrow" reminder email has gone out, so re-running the command
    # (e.g. if it's triggered more than once a day) never double-sends.
    reminder_sent = models.BooleanField(default=False)

    # No DB-level unique_together on (doctor, appointment_date, time_slot):
    # a cancelled appointment is meant to free that slot back up for
    # rebooking (see Doctor.get_available_slots()'s `.exclude(status='cancelled')`),
    # and MySQL has no partial/conditional unique index to express "unique
    # unless cancelled". Double-booking is instead prevented at the
    # application level -- every booking view re-checks get_available_slots()
    # immediately before calling Appointment.objects.create().

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.appointment_date} {self.time_slot}"

class Billing(models.Model):
    """
    A charge associated with one ``Appointment`` and the ``Patient`` who
    owes it. Rows are created for the "pay at the front desk" checkpoint
    when a patient confirms a self-booked appointment (``bill_type``
    defaults to 'consultation'), and can also represent a penalty fee
    charged when a patient misses an appointment ('no_show_fee').
    """
    BILL_TYPE_CHOICES = (
        ('consultation', 'Consultation Fee'),
        ('no_show_fee', 'No-Show Fee'),
    )
    # Payment state of the bill: 'pending' until settled at the front desk,
    # 'paid' once collected, or 'waived' if staff decide not to charge it.
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    )

    # The appointment this charge is for.
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='bills')
    # The patient who owes this charge (denormalized off `appointment` for
    # convenience, e.g. querying a patient's full billing history directly).
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bills')
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES, default='consultation')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp set once the bill is actually paid; stays null while pending.
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_bill_type_display()} - {self.patient} - Rs.{self.amount}"


class ContactMessage(models.Model):
    """
    A single submission of the public "contact us" form. Standalone record,
    not linked to ``Patient``, ``User``, or any other model here — anyone
    (patient or anonymous visitor) can submit one.
    """
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.subject}"

from django.conf import settings

class Notification(models.Model):
    """
    An in-app notification shown to a user. Linked directly to
    ``accounts.User`` (not ``Patient``), so any role can in principle
    receive one, though in practice these are created for patients when
    their appointments are booked/cancelled (see ``patient/views.py``).
    """
    # What kind of event this notification is about; drives any
    # type-specific styling/icons in the templates.
    TYPE_CHOICES = (
        ('confirmed', 'Appointment Confirmed'),
        ('reminder', 'Appointment Reminder'),
        ('cancelled', 'Appointment Cancelled'),
        ('general', 'General'),
    )
    # The user this notification is addressed to.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.message}"