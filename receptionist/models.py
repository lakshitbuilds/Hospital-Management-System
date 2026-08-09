from django.conf import settings
from django.db import models


class Receptionist(models.Model):
    SHIFT_CHOICES = (
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='receptionist_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='receptionists/profile_pictures/', blank=True, null=True)
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, default='morning')
    date_joined = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last = Receptionist.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.employee_id = f"REC{next_id:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name() or self.user.username}"
