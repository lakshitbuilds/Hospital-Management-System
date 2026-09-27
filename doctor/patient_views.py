from django.shortcuts import render

from patient.models import Patient
from .views import doctor_required, get_doctor


@doctor_required
def patient_list(request):
    """Show the distinct patients who have appointments with this doctor."""
    doctor = get_doctor(request)
    patients = (
        Patient.objects
        .filter(appointments__doctor=doctor)
        .select_related('user')
        .distinct()
        .order_by('user__first_name', 'user__last_name')
    )
    return render(request, 'doctor/patient_list.html', {'patients': patients})
