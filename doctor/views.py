from datetime import datetime, date
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from .models import Doctor, DoctorAvailability, BlockedDate, Prescription, PrescriptionMedicine
from patient.models import Patient, Appointment, Notification


def doctor_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'doctor':
            messages.error(request, 'Access restricted to doctors.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def parse_time_slot(time_slot):
    try:
        return datetime.strptime(time_slot, '%I:%M %p').time()
    except (ValueError, TypeError):
        return datetime.min.time()


def get_doctor(request):
    return get_object_or_404(Doctor, user=request.user)


# ================================================================
# Dashboard
# ================================================================

@doctor_required
def doctor_home(request):
    doctor = get_doctor(request)
    today = date.today()

    todays_qs = Appointment.objects.filter(doctor=doctor, appointment_date=today).select_related('patient__user')
    todays_appointments = sorted(todays_qs, key=lambda a: parse_time_slot(a.time_slot))[:4]

    total_patients = Patient.objects.filter(appointments__doctor=doctor).distinct().count()
    pending_prescriptions = Appointment.objects.filter(doctor=doctor, status='completed', prescriptions__isnull=True).count()
    appointments_this_month = Appointment.objects.filter(doctor=doctor, appointment_date__month=today.month, appointment_date__year=today.year).count()

    recent_patient_ids = (
        Appointment.objects.filter(doctor=doctor)
        .order_by('-appointment_date')
        .values_list('patient_id', flat=True)
    )
    seen = []
    for pid in recent_patient_ids:
        if pid not in seen:
            seen.append(pid)
        if len(seen) >= 3:
            break
    recent_patients = Patient.objects.filter(id__in=seen).select_related('user')

    context = {
        'doctor': doctor,
        'today_count': todays_qs.count(),
        'total_patients': total_patients,
        'pending_prescriptions': pending_prescriptions,
        'appointments_this_month': appointments_this_month,
        'todays_appointments': todays_appointments,
        'recent_patients': recent_patients,
    }
    return render(request, 'doctor/dashboard.html', context)


# ================================================================
# Appointments
# ================================================================

@doctor_required
def today_appointments(request):
    doctor = get_doctor(request)
    today = date.today()
    qs = Appointment.objects.filter(doctor=doctor, appointment_date=today).select_related('patient__user')
    appointments = sorted(qs, key=lambda a: parse_time_slot(a.time_slot))

    counts = {
        'total': len(appointments),
        'completed': sum(1 for a in appointments if a.status == 'completed'),
        'pending': sum(1 for a in appointments if a.status == 'pending'),
        'upcoming': sum(1 for a in appointments if a.status == 'confirmed'),
    }

    return render(request, 'doctor/today_appointments.html', {'appointments': appointments, 'counts': counts})


@doctor_required
def mark_appointment_complete(request, appointment_id):
    doctor = get_doctor(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
    if request.method == 'POST':
        appointment.status = 'completed'
        appointment.save()
    return redirect('today_appointments')


@doctor_required
def appointment_list(request):
    doctor = get_doctor(request)
    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient__user').order_by('-appointment_date')
    return render(request, 'doctor/appointment_list.html', {'appointments': appointments})


@doctor_required
def doctor_cancel_appointment(request, appointment_id):
    doctor = get_doctor(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        Notification.objects.create(
            user=appointment.patient.user,
            notification_type='cancelled',
            message=f'Your appointment with Dr. {doctor.user.get_full_name()} on {appointment.appointment_date} was cancelled by the doctor.'
        )
    return redirect('appointment_list')


# ================================================================
# Patients
# ================================================================

@doctor_required
def patient_details(request, patient_id):
    doctor = get_doctor(request)
    patient = get_object_or_404(Patient.objects.distinct(), id=patient_id, appointments__doctor=doctor)

    history = Appointment.objects.filter(doctor=doctor, patient=patient).order_by('-appointment_date')
    prescriptions = Prescription.objects.filter(doctor=doctor, patient=patient).prefetch_related('medicines')

    age = None
    if patient.date_of_birth:
        today = date.today()
        age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    return render(request, 'doctor/patient_details.html', {
        'patient': patient,
        'age': age,
        'history': history,
        'prescriptions': prescriptions,
    })


# ================================================================
# Prescriptions
# ================================================================

@doctor_required
def add_prescription(request):
    doctor = get_doctor(request)
    patients = Patient.objects.filter(appointments__doctor=doctor).select_related('user').distinct()

    preselected_patient_id = request.GET.get('patient')
    preselected_appointment_id = request.GET.get('appointment')

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        appointment_id = request.POST.get('appointment_id') or None
        diagnosis = request.POST.get('diagnosis')
        advice = request.POST.get('advice', '')
        follow_up_date = request.POST.get('follow_up_date') or None

        patient = get_object_or_404(Patient.objects.distinct(), id=patient_id, appointments__doctor=doctor)

        prescription = Prescription.objects.create(
            doctor=doctor,
            patient=patient,
            appointment_id=appointment_id,
            diagnosis=diagnosis,
            advice=advice,
            follow_up_date=follow_up_date,
        )

        names = request.POST.getlist('medicine_name[]')
        dosages = request.POST.getlist('dosage[]')
        frequencies = request.POST.getlist('frequency[]')
        durations = request.POST.getlist('duration[]')
        instructions = request.POST.getlist('instructions[]')

        for i, name in enumerate(names):
            if not name:
                continue
            PrescriptionMedicine.objects.create(
                prescription=prescription,
                name=name,
                dosage=dosages[i] if i < len(dosages) else '',
                frequency=frequencies[i] if i < len(frequencies) else '',
                duration=durations[i] if i < len(durations) else '',
                instructions=instructions[i] if i < len(instructions) else '',
            )

        Notification.objects.create(
            user=patient.user,
            notification_type='general',
            message=f'Dr. {doctor.user.get_full_name()} added a new prescription for you.'
        )

        messages.success(request, 'Prescription saved successfully.')
        return redirect('prescription_history')

    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient').order_by('-appointment_date')

    return render(request, 'doctor/add_prescription.html', {
        'patients': patients,
        'appointments': appointments,
        'preselected_patient_id': preselected_patient_id,
        'preselected_appointment_id': preselected_appointment_id,
    })


@doctor_required
def prescription_history(request):
    doctor = get_doctor(request)
    prescriptions = Prescription.objects.filter(doctor=doctor).select_related('patient__user').prefetch_related('medicines')
    return render(request, 'doctor/prescription_history.html', {'prescriptions': prescriptions})


# ================================================================
# Availability
# ================================================================

@doctor_required
def availability(request):
    doctor = get_doctor(request)
    days = [d[0] for d in DoctorAvailability.DAY_CHOICES]

    if request.method == 'POST':
        for day in days:
            is_available = request.POST.get(f'available_{day}') == 'on'
            start_time = request.POST.get(f'start_{day}') or '09:00'
            end_time = request.POST.get(f'end_{day}') or '17:00'

            DoctorAvailability.objects.update_or_create(
                doctor=doctor,
                day=day,
                defaults={
                    'is_available': is_available,
                    'start_time': start_time,
                    'end_time': end_time,
                }
            )

        doctor.slot_duration = request.POST.get('slot_duration') or 30
        doctor.buffer_time = request.POST.get('buffer_time') or 5
        max_per_day = request.POST.get('max_per_day')
        doctor.max_per_day = max_per_day or None
        doctor.save()

        BlockedDate.objects.filter(doctor=doctor).delete()
        blocked_dates = request.POST.getlist('blocked_date[]')
        blocked_reasons = request.POST.getlist('blocked_reason[]')
        for i, blocked_date in enumerate(blocked_dates):
            if not blocked_date:
                continue
            BlockedDate.objects.create(
                doctor=doctor,
                date=blocked_date,
                reason=blocked_reasons[i] if i < len(blocked_reasons) else '',
            )

        messages.success(request, 'Availability updated successfully.')
        return redirect('availability')

    schedule = {a.day: a for a in DoctorAvailability.objects.filter(doctor=doctor)}
    weekly_schedule = []
    for day_key, day_label in DoctorAvailability.DAY_CHOICES:
        entry = schedule.get(day_key)
        weekly_schedule.append({
            'day': day_key,
            'label': day_label,
            'is_available': entry.is_available if entry else (day_key != 'sunday'),
            'start_time': entry.start_time.strftime('%H:%M') if entry else '09:00',
            'end_time': entry.end_time.strftime('%H:%M') if entry else ('13:00' if day_key == 'saturday' else '17:00'),
        })

    blocked_dates = BlockedDate.objects.filter(doctor=doctor)

    return render(request, 'doctor/availability.html', {
        'doctor': doctor,
        'weekly_schedule': weekly_schedule,
        'blocked_dates': blocked_dates,
    })


# ================================================================
# Notifications
# ================================================================

@doctor_required
def notifications_view(request):
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'doctor/notifications.html', {
        'notifications': notes,
        'unread_count': notes.filter(is_read=False).count(),
    })


@doctor_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('doctor_notifications')


@doctor_required
def dismiss_notification(request, notification_id):
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('doctor_notifications')


# ================================================================
# Profile
# ================================================================

@doctor_required
def doctor_profile(request):
    doctor = get_doctor(request)
    total_patients = Patient.objects.filter(appointments__doctor=doctor).distinct().count()

    schedule = {a.day: a for a in DoctorAvailability.objects.filter(doctor=doctor)}
    weekly_schedule = []
    for day_key, day_label in DoctorAvailability.DAY_CHOICES:
        entry = schedule.get(day_key)
        weekly_schedule.append({
            'label': day_label,
            'is_available': entry.is_available if entry else (day_key != 'sunday'),
            'start_time': entry.start_time.strftime('%I:%M %p') if entry else '09:00 AM',
            'end_time': entry.end_time.strftime('%I:%M %p') if entry else ('01:00 PM' if day_key == 'saturday' else '05:00 PM'),
        })

    return render(request, 'doctor/doctor_profile.html', {
        'doctor': doctor,
        'total_patients': total_patients,
        'weekly_schedule': weekly_schedule,
    })


@doctor_required
def edit_profile(request):
    doctor = get_doctor(request)

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()

        doctor.phone_number = request.POST.get('phone_number', '')
        doctor.department = request.POST.get('department')
        doctor.specialization = request.POST.get('specialization', '')
        doctor.qualification = request.POST.get('qualification', '')
        doctor.experience_years = request.POST.get('experience_years') or 0
        doctor.consultation_fee = request.POST.get('consultation_fee') or 0
        doctor.bio = request.POST.get('bio', '')

        if request.FILES.get('profile_picture'):
            doctor.profile_picture = request.FILES['profile_picture']

        doctor.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('doctor_profile')

    return render(request, 'doctor/edit_profile.html', {'doctor': doctor})


@doctor_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        if new_password != confirm_new_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password updated successfully.')
        return redirect('doctor_profile')

    return render(request, 'doctor/change_password.html')
