"""Models for the adminpanel app.

This app intentionally defines no models of its own. The admin portal is a
management/reporting layer on top of data owned by other apps, so it simply
reuses the existing models: `accounts.User` (login/role), `doctor.Doctor`,
`patient.Patient`, and `receptionist.Receptionist`. Keeping this file empty
avoids duplicating those models or creating a second source of truth for
the same data.
"""
from django.db import models

# Create your models here.
# (Deliberately left empty -- see module docstring above for why.)
