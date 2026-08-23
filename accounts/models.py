"""
Core data models for the accounts app.

This file defines the single custom `User` model shared by all four
portals in the system (admin, doctor, receptionist, patient) as well as
`SystemSettings`, a hospital-wide settings singleton. The actual business
logic that reads and writes the OTP-related fields below (generating an
OTP, emailing/texting it, checking it, counting failed attempts, and
locking out after too many wrong guesses) lives in `patient/views.py`,
not here — this file only declares the fields that logic depends on.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model used for every role in the system (admin, doctor,
    receptionist, patient). Extends Django's built-in AbstractUser but
    swaps the login identifier from username to email, and adds a `role`
    field plus OTP (one-time password) fields used for OTP-based login.
    """

    # Which portal/permission level this account belongs to. Used
    # throughout the app to decide what a logged-in user is allowed to see.
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
        ('patient', 'Patient'),
    )

    email = models.EmailField(unique=True)
    # Defaults to 'patient' since self-registration is normally done by patients.
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')

    # The following four fields support OTP-based login (e.g. "email me a
    # code to sign in"). They are only data storage — the logic that
    # generates, sends, and verifies OTPs lives in patient/views.py.

    # The current one-time password code sent to the user, if any.
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    # Timestamp of when otp_code was generated, used to expire old codes.
    otp_created_at = models.DateTimeField(blank=True, null=True)
    # Counts consecutive wrong OTP guesses; reset on success. Used to
    # trigger the temporary lockout below once too many attempts fail.
    otp_attempts = models.PositiveSmallIntegerField(default=0)
    # If set to a future time, OTP login is temporarily blocked for this
    # user (a brute-force lockout, e.g. 10 minutes after 3 wrong guesses).
    otp_locked_until = models.DateTimeField(blank=True, null=True)

    # Use email instead of username to log in...
    USERNAME_FIELD = 'email'
    # ...but Django's createsuperuser command still expects a username,
    # so it stays required even though it isn't used for login itself.
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.role})"


class SystemSettings(models.Model):
    """Single row of hospital-wide toggles, managed from the admin dashboard."""

    # Global on/off switch for OTP login across the whole hospital system.
    # When False, admins have disabled OTP login without touching .env.
    otp_login_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'

    @classmethod
    def get_solo(cls):
        # Singleton accessor: there should only ever be one row (id=1) for
        # these settings, so this fetches it if it exists or creates it
        # with default values the first time it's needed. Callers should
        # always use SystemSettings.get_solo() instead of querying directly.
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return 'System Settings'