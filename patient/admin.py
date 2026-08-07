from django.contrib import admin
from .models import Patient,Appointment,ContactMessage

admin.site.register(Patient)
admin.site.register(Appointment)
admin.site.register(ContactMessage)
# patient/admin.py