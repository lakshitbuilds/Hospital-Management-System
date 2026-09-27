from django.db.models import Q
from django.shortcuts import render

from patient.models import Patient
from .views import doctor_required, get_doctor


@doctor_required
def patient_list(request):
    """Show the distinct patients who have appointments with this doctor."""
    doctor = get_doctor(request)
    query = request.GET.get('q', '').strip()

    patients = (
        Patient.objects
        .filter(appointments__doctor=doctor)
        .select_related('user')
        .distinct()
        .order_by('user__first_name', 'user__last_name')
    )

    if query:
        patients = patients.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(phone__icontains=query)
        )

    return render(request, 'doctor/patient_list.html', {
        'patients': patients,
        'query': query,
    })
