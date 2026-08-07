from django.db import models
from django.conf import settings
# from .models import Patient,Doctor


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

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.department}"
