"""
Models for the receptionist app.

This module defines the `Receptionist` profile model, which holds the
front-desk-staff-specific data that doesn't belong on the shared `accounts.User`
model (e.g. employee ID, shift, phone number). The receptionist portal views
in `receptionist/views.py` read and update this profile.
"""

from django.conf import settings
from django.db import models


class Receptionist(models.Model):
    """
    Front-desk staff profile, one-to-one with a `User` whose `role` is 'receptionist'.

    Holds the extra data a receptionist needs beyond the base `User` fields
    (login/auth, name, email). Created lazily on first access via
    `receptionist.views.get_receptionist`, which does a `get_or_create`.
    """

    SHIFT_CHOICES = (
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    )

    # One-to-one link back to the shared auth user; deleting the user deletes this profile too.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='receptionist_profile')
    # Auto-generated in save() below (e.g. "REC000001") if left blank; not user-entered.
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='receptionists/profile_pictures/', blank=True, null=True)
    # Which shift this receptionist works. Receptionists can no longer change their own
    # shift from their profile-edit view (see receptionist/views.py) - that restriction
    # is enforced in the views/templates, not here; only an admin-only view may update it.
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default='morning')
    date_joined = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # If no employee_id was set yet, auto-generate the next sequential one
        # (based on the highest existing primary key) in the form "REC000001".
        if not self.employee_id:
            last = Receptionist.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.employee_id = f"REC{next_id:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.username}"
