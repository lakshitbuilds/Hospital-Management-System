from django.contrib import admin
from .models import Doctor, DoctorAvailability, BlockedDate, Prescription, PrescriptionMedicine

admin.site.register(Doctor)
admin.site.register(DoctorAvailability)
admin.site.register(BlockedDate)
admin.site.register(Prescription)
admin.site.register(PrescriptionMedicine)
