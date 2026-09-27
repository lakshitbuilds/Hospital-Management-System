from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Patient


@login_required
def patient_dashboard(request):
    """Simple dashboard for the currently logged-in patient."""
    if request.user.role != 'patient':
        messages.error(request, 'Access restricted to patients.')
        return redirect('home')

    patient, _ = Patient.objects.get_or_create(user=request.user)
    appointments = patient.appointments.select_related('doctor__user')

    upcoming = (
        appointments
        .filter(
            appointment_date__gte=timezone.localdate(),
            status__in=['pending', 'confirmed'],
        )
        .order_by('appointment_date', 'time_slot')
    )

    context = {
        'patient': patient,
        'total_appointments': appointments.count(),
        'upcoming_count': upcoming.count(),
        'completed_count': appointments.filter(status='completed').count(),
        'upcoming_appointments': upcoming[:5],
    }
    return render(request, 'patient/dashboard.html', context)
