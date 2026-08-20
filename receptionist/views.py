from datetime import date, datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from doctor.models import Doctor, DoctorAvailability
from patient.models import Appointment, Billing, Notification, Patient

from .models import Receptionist

User = get_user_model()


def receptionist_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'receptionist':
            messages.error(request, 'Access restricted to receptionists.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_receptionist(request):
    receptionist, _ = Receptionist.objects.get_or_create(user=request.user)
    return receptionist


def parse_time_slot(time_slot):
    try:
        return datetime.strptime(time_slot, '%I:%M %p').time()
    except (ValueError, TypeError):
        return datetime.min.time()


# ================================================================
# Dashboard
# ================================================================

@receptionist_required
def receptionist_dashboard(request):
    receptionist = get_receptionist(request)
    today = date.today()

    todays_qs = Appointment.objects.filter(appointment_date=today).select_related('patient__user', 'doctor__user')
    todays_appointments = sorted(todays_qs, key=lambda a: parse_time_slot(a.time_slot))[:5]

    context = {
        'receptionist': receptionist,
        'today_count': todays_qs.count(),
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'pending_count': Appointment.objects.filter(status='pending').count(),
        'todays_appointments': todays_appointments,
        'recent_patients': Patient.objects.select_related('user').order_by('-created_at')[:5],
    }
    return render(request, 'receptionist/dashboard.html', context)


# ================================================================
# Patients
# ================================================================

@receptionist_required
def patient_list(request):
    query = request.GET.get('q', '').strip()
    patients = Patient.objects.select_related('user').order_by('-created_at')

    if query:
        patients = patients.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(patient_id__icontains=query)
            | Q(phone__icontains=query)
            | Q(user__email__icontains=query)
        )

    return render(request, 'receptionist/patient_list.html', {'patients': patients, 'query': query})


@receptionist_required
def register_patient(request):
    receptionist = get_receptionist(request)

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('receptionist_register_patient')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('receptionist_register_patient')

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='patient',
        )

        patient = Patient.objects.create(
            user=user,
            registered_by=receptionist,
            phone=request.POST.get('phone', ''),
            date_of_birth=request.POST.get('date_of_birth') or None,
            gender=request.POST.get('gender', ''),
            blood_group=request.POST.get('blood_group', ''),
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            country=request.POST.get('country', ''),
            pincode=request.POST.get('pincode', ''),
            emergency_contact_name=request.POST.get('emergency_contact_name', ''),
            emergency_contact_number=request.POST.get('emergency_contact_number', ''),
            allergies=request.POST.get('allergies', ''),
            medical_history=request.POST.get('medical_history', ''),
        )

        messages.success(request, f'Patient {patient.user.get_full_name()} registered successfully with ID {patient.patient_id}.')
        return redirect('receptionist_patient_detail', patient_id=patient.id)

    return render(request, 'receptionist/register_patient.html')


@receptionist_required
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient.objects.select_related('user', 'registered_by'), id=patient_id)
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor__user').order_by('-appointment_date')

    age = None
    if patient.date_of_birth:
        today = date.today()
        age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    return render(request, 'receptionist/patient_detail.html', {
        'patient': patient,
        'age': age,
        'appointments': appointments,
    })


# ================================================================
# Appointments
# ================================================================

@receptionist_required
def appointment_list(request):
    appointments = Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-appointment_date')
    return render(request, 'receptionist/appointment_list.html', {'appointments': appointments})


@receptionist_required
def today_appointments(request):
    today = date.today()
    qs = Appointment.objects.filter(appointment_date=today).select_related('patient__user', 'doctor__user')
    appointments = sorted(qs, key=lambda a: parse_time_slot(a.time_slot))

    counts = {
        'total': len(appointments),
        'confirmed': sum(1 for a in appointments if a.status == 'confirmed'),
        'pending': sum(1 for a in appointments if a.status == 'pending'),
        'completed': sum(1 for a in appointments if a.status == 'completed'),
    }

    return render(request, 'receptionist/today_appointments.html', {'appointments': appointments, 'counts': counts})


@receptionist_required
def get_doctor_slots(request):
    doctor_id = request.GET.get('doctor')
    date_str = request.GET.get('date')

    doctor = get_object_or_404(Doctor, id=doctor_id)
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse({'available': False, 'reason': 'Invalid date.', 'slots': []}, status=400)

    return JsonResponse(doctor.get_available_slots(appointment_date))


@receptionist_required
def book_appointment(request):
    patients = Patient.objects.select_related('user').order_by('user__first_name')
    doctors = Doctor.objects.select_related('user').all()
    preselected_patient_id = request.GET.get('patient')

    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        time_slot = request.POST.get('time_slot')

        if not patient_id or not doctor_id:
            messages.error(request, 'Please select both a patient and a doctor.')
            return redirect('receptionist_book_appointment')

        if not time_slot:
            messages.error(request, 'Please select a time slot.')
            return redirect('receptionist_book_appointment')

        patient = get_object_or_404(Patient, id=patient_id)
        doctor = get_object_or_404(Doctor, id=doctor_id)
        appointment_date = request.POST.get('appointment_date')

        try:
            parsed_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.error(request, 'Please select a valid date.')
            return redirect('receptionist_book_appointment')

        availability = doctor.get_available_slots(parsed_date)
        if not availability['available']:
            messages.error(request, availability['reason'] or 'Doctor is unavailable on this date.')
            return redirect('receptionist_book_appointment')

        matching_slot = next((s for s in availability['slots'] if s['time'] == time_slot), None)
        if matching_slot is None or matching_slot['booked']:
            messages.error(request, 'This slot is already booked.')
            return redirect('receptionist_book_appointment')

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            department=request.POST.get('department', doctor.department),
            appointment_date=appointment_date,
            time_slot=time_slot,
            visit_type=request.POST.get('visit_type', 'new'),
            reason=request.POST.get('reason', ''),
            status='confirmed',
        )

        Billing.objects.create(
            appointment=appointment,
            patient=patient,
            bill_type='consultation',
            amount=doctor.consultation_fee,
        )

        Notification.objects.create(
            user=patient.user,
            notification_type='confirmed',
            message=f'Your appointment with Dr. {doctor.user.get_full_name()} on {appointment.appointment_date} at {time_slot} has been confirmed by the front desk.',
        )

        messages.success(request, 'Appointment booked successfully.')
        return redirect('receptionist_appointment_list')

    return render(request, 'receptionist/book_appointment.html', {
        'patients': patients,
        'doctors': doctors,
        'preselected_patient_id': preselected_patient_id,
    })


@receptionist_required
def confirm_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        appointment.status = 'confirmed'
        appointment.save()
        Notification.objects.create(
            user=appointment.patient.user,
            notification_type='confirmed',
            message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.appointment_date} has been confirmed.',
        )
        messages.success(request, 'Appointment confirmed.')
    return redirect(request.POST.get('next') or 'receptionist_appointment_list')


@receptionist_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        Notification.objects.create(
            user=appointment.patient.user,
            notification_type='cancelled',
            message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.appointment_date} was cancelled by the front desk.',
        )
        messages.success(request, 'Appointment cancelled.')
    return redirect(request.POST.get('next') or 'receptionist_appointment_list')


@receptionist_required
def mark_no_show(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        if appointment.status in ('cancelled', 'completed', 'no_show'):
            messages.error(request, 'This appointment cannot be marked as a no-show.')
        else:
            appointment.status = 'no_show'
            appointment.save()

            Billing.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                bill_type='no_show_fee',
                amount=appointment.doctor.consultation_fee,
            )

            Notification.objects.create(
                user=appointment.patient.user,
                notification_type='general',
                message=(
                    f'You missed your appointment with Dr. {appointment.doctor.user.get_full_name()} '
                    f'on {appointment.appointment_date}. A no-show fee of Rs.{appointment.doctor.consultation_fee} '
                    f'has been added to your billing.'
                ),
            )
            messages.success(request, 'Appointment marked as a no-show and a fee has been billed to the patient.')
    return redirect(request.POST.get('next') or 'receptionist_appointment_list')


# ================================================================
# Billing
# ================================================================

@receptionist_required
def billing_list(request):
    query = request.GET.get('q', '').strip()
    bills = Billing.objects.select_related('patient__user', 'appointment__doctor__user').order_by('-created_at')

    if query:
        bills = bills.filter(
            Q(patient__user__first_name__icontains=query)
            | Q(patient__user__last_name__icontains=query)
            | Q(patient__patient_id__icontains=query)
        )

    return render(request, 'receptionist/billing_list.html', {
        'bills': bills,
        'query': query,
        'pending_total': Billing.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
    })


@receptionist_required
def mark_bill_paid(request, bill_id):
    bill = get_object_or_404(Billing, id=bill_id)
    if request.method == 'POST':
        bill.status = 'paid'
        bill.paid_at = timezone.now()
        bill.save()
        messages.success(request, 'Bill marked as paid.')
    return redirect(request.POST.get('next') or 'receptionist_billing_list')


# ================================================================
# Doctors
# ================================================================

@receptionist_required
def doctor_list(request):
    today = date.today()
    today_day = today.strftime('%A').lower()
    doctors = Doctor.objects.select_related('user').all()
    availability_map = {a.doctor_id: a for a in DoctorAvailability.objects.filter(day=today_day)}

    doctor_rows = []
    for index, doc in enumerate(doctors):
        avail = availability_map.get(doc.id)
        doctor_rows.append({
            'doctor': doc,
            'photo_path': f'public/images/doctor-{(index % 8) + 1}.jpg',
            'available_today': avail.is_available if avail else (today_day != 'sunday'),
            'today_appointment_count': Appointment.objects.filter(doctor=doc, appointment_date=today).exclude(status='cancelled').count(),
        })

    return render(request, 'receptionist/doctor_list.html', {'doctor_rows': doctor_rows})


# ================================================================
# Notifications
# ================================================================

@receptionist_required
def notifications_view(request):
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'receptionist/notifications.html', {
        'notifications': notes,
        'unread_count': notes.filter(is_read=False).count(),
    })


@receptionist_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('receptionist_notifications')


@receptionist_required
def dismiss_notification(request, notification_id):
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('receptionist_notifications')


# ================================================================
# Profile
# ================================================================

@receptionist_required
def receptionist_profile(request):
    receptionist = get_receptionist(request)
    registered_patients = Patient.objects.filter(registered_by=receptionist).select_related('user').order_by('-created_at')

    return render(request, 'receptionist/profile.html', {
        'receptionist': receptionist,
        'total_registered': registered_patients.count(),
        'recent_registrations': registered_patients[:5],
    })


@receptionist_required
def edit_profile(request):
    receptionist = get_receptionist(request)

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()

        receptionist.phone = request.POST.get('phone', '')

        if request.FILES.get('profile_picture'):
            receptionist.profile_picture = request.FILES['profile_picture']

        receptionist.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('receptionist_profile')

    return render(request, 'receptionist/edit_profile.html', {'receptionist': receptionist})


@receptionist_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('receptionist_change_password')

        if new_password != confirm_new_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('receptionist_change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password updated successfully.')
        return redirect('receptionist_profile')

    return render(request, 'receptionist/change_password.html')
