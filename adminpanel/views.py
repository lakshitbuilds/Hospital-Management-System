from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import SystemSettings
from doctor.models import Doctor
from patient.models import Appointment, Billing, Notification, Patient
from receptionist.models import Receptionist

User = get_user_model()

DEPARTMENT_LABELS = dict(Doctor.DEPARTMENT_CHOICES)
STATUS_LABELS = dict(Appointment.STATUS_CHOICES)
STATUS_COLORS = {
    'pending': '#d97706',
    'confirmed': '#2563eb',
    'completed': '#16a34a',
    'cancelled': '#dc2626',
    'no_show': '#78716c',
}


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            messages.error(request, 'Access restricted to administrators.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def last_n_months(n):
    first_of_this_month = date.today().replace(day=1)
    months = []
    for i in range(n - 1, -1, -1):
        month = first_of_this_month.month - i
        year = first_of_this_month.year
        while month <= 0:
            month += 12
            year -= 1
        months.append(date(year, month, 1))
    return months


# ================================================================
# Dashboard
# ================================================================

@admin_required
def admin_dashboard(request):
    today = date.today()

    completed_appointments = Appointment.objects.filter(status='completed').select_related('doctor')
    revenue_estimate = sum(a.doctor.consultation_fee for a in completed_appointments)
    outstanding_bills = Billing.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    department_counts = (
        Appointment.objects.values('department')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    department_labels = [DEPARTMENT_LABELS.get(row['department'], row['department']) for row in department_counts]
    department_data = [row['count'] for row in department_counts]

    status_counts = Appointment.objects.values('status').annotate(count=Count('id'))
    status_labels = [STATUS_LABELS.get(row['status'], row['status']) for row in status_counts]
    status_data = [row['count'] for row in status_counts]
    status_colors = [STATUS_COLORS.get(row['status'], '#6b7280') for row in status_counts]

    months = last_n_months(6)
    trend_labels = [m.strftime('%b %Y') for m in months]
    trend_data = [
        Patient.objects.filter(created_at__year=m.year, created_at__month=m.month).count()
        for m in months
    ]

    context = {
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'total_receptionists': Receptionist.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'today_count': Appointment.objects.filter(appointment_date=today).count(),
        'pending_count': Appointment.objects.filter(status='pending').count(),
        'revenue_estimate': revenue_estimate,
        'outstanding_bills': outstanding_bills,
        'department_labels': department_labels,
        'department_data': department_data,
        'status_labels': status_labels,
        'status_data': status_data,
        'status_colors': status_colors,
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'recent_appointments': Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-created_at')[:5],
        'recent_users': User.objects.exclude(role='admin').order_by('-date_joined')[:5],
    }
    return render(request, 'adminpanel/dashboard.html', context)


# ================================================================
# Doctors
# ================================================================

@admin_required
def doctor_list(request):
    query = request.GET.get('q', '').strip()
    doctors = Doctor.objects.select_related('user').order_by('user__first_name')
    if query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(department__icontains=query)
            | Q(specialization__icontains=query)
        )
    return render(request, 'adminpanel/doctor_list.html', {'doctors': doctors, 'query': query})


@admin_required
def add_doctor(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_add_doctor')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('admin_add_doctor')

        name_parts = full_name.split(' ', 1)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            role='doctor',
        )

        doctor = Doctor.objects.create(
            user=user,
            department=request.POST.get('department'),
            specialization=request.POST.get('specialization', ''),
            phone_number=request.POST.get('phone_number', ''),
            qualification=request.POST.get('qualification', ''),
            experience_years=request.POST.get('experience_years') or 0,
            consultation_fee=request.POST.get('consultation_fee') or 0,
            license_number=request.POST.get('license_number', ''),
        )

        messages.success(request, f'Dr. {doctor.user.get_full_name()} has been onboarded successfully.')
        return redirect('admin_doctor_detail', doctor_id=doctor.id)

    return render(request, 'adminpanel/add_doctor.html', {'departments': Doctor.DEPARTMENT_CHOICES})


@admin_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor.objects.select_related('user'), id=doctor_id)
    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient__user').order_by('-appointment_date')

    context = {
        'doctor': doctor,
        'total_appointments': appointments.count(),
        'total_patients': Patient.objects.filter(appointments__doctor=doctor).distinct().count(),
        'completed_count': appointments.filter(status='completed').count(),
        'recent_appointments': appointments[:8],
    }
    return render(request, 'adminpanel/doctor_detail.html', context)


# ================================================================
# Receptionists
# ================================================================

@admin_required
def receptionist_list(request):
    query = request.GET.get('q', '').strip()
    receptionists = Receptionist.objects.select_related('user').order_by('user__first_name')
    if query:
        receptionists = receptionists.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(employee_id__icontains=query)
        )
    return render(request, 'adminpanel/receptionist_list.html', {'receptionists': receptionists, 'query': query})


@admin_required
def add_receptionist(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_add_receptionist')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('admin_add_receptionist')

        name_parts = full_name.split(' ', 1)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            role='receptionist',
        )

        receptionist = Receptionist.objects.create(
            user=user,
            phone=request.POST.get('phone', ''),
            shift=request.POST.get('shift', 'morning'),
        )

        messages.success(request, f'{receptionist.user.get_full_name()} has been onboarded successfully.')
        return redirect('admin_receptionist_list')

    return render(request, 'adminpanel/add_receptionist.html')


@admin_required
def update_receptionist_shift(request, receptionist_id):
    receptionist = get_object_or_404(Receptionist, id=receptionist_id)
    if request.method == 'POST':
        shift = request.POST.get('shift')
        if shift in dict(Receptionist.SHIFT_CHOICES):
            receptionist.shift = shift
            receptionist.save()
            messages.success(request, f'{receptionist.user.get_full_name()}\'s shift has been updated to {receptionist.get_shift_display()}.')
    return redirect(request.POST.get('next') or 'admin_receptionist_list')


# ================================================================
# Patients
# ================================================================

@admin_required
def patient_list(request):
    query = request.GET.get('q', '').strip()
    patients = Patient.objects.select_related('user', 'registered_by').order_by('-created_at')
    if query:
        patients = patients.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(patient_id__icontains=query)
            | Q(user__email__icontains=query)
        )
    return render(request, 'adminpanel/patient_list.html', {'patients': patients, 'query': query})


@admin_required
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient.objects.select_related('user', 'registered_by'), id=patient_id)
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor__user').order_by('-appointment_date')

    age = None
    if patient.date_of_birth:
        today = date.today()
        age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    return render(request, 'adminpanel/patient_detail.html', {
        'patient': patient,
        'age': age,
        'appointments': appointments,
    })


# ================================================================
# Appointments
# ================================================================

@admin_required
def appointment_list(request):
    appointments = Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-appointment_date')
    return render(request, 'adminpanel/appointment_list.html', {'appointments': appointments})


# ================================================================
# Billing
# ================================================================

@admin_required
def billing_list(request):
    query = request.GET.get('q', '').strip()
    bills = Billing.objects.select_related('patient__user', 'appointment__doctor__user').order_by('-created_at')

    if query:
        bills = bills.filter(
            Q(patient__user__first_name__icontains=query)
            | Q(patient__user__last_name__icontains=query)
            | Q(patient__patient_id__icontains=query)
        )

    return render(request, 'adminpanel/billing_list.html', {
        'bills': bills,
        'query': query,
        'pending_total': Billing.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
    })


@admin_required
def mark_bill_paid(request, bill_id):
    bill = get_object_or_404(Billing, id=bill_id)
    if request.method == 'POST':
        bill.status = 'paid'
        bill.paid_at = timezone.now()
        bill.save()
        messages.success(request, 'Bill marked as paid.')
    return redirect(request.POST.get('next') or 'admin_billing_list')


# ================================================================
# Security Settings
# ================================================================

@admin_required
def security_settings(request):
    settings_obj = SystemSettings.get_solo()

    if request.method == 'POST':
        settings_obj.otp_login_enabled = 'otp_login_enabled' in request.POST
        settings_obj.save()
        state = 'enabled' if settings_obj.otp_login_enabled else 'disabled'
        messages.success(request, f'Two-step (OTP) login verification has been {state}.')
        return redirect('admin_security_settings')

    return render(request, 'adminpanel/security_settings.html', {'settings': settings_obj})


# ================================================================
# Account Status
# ================================================================

@admin_required
def toggle_user_status(request, user_id):
    target = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if target.role == 'admin':
            messages.error(request, 'Administrator accounts cannot be deactivated from here.')
        else:
            target.is_active = not target.is_active
            target.save()
            state = 'activated' if target.is_active else 'deactivated'
            messages.success(request, f'{target.get_full_name()} has been {state}.')

    return redirect(request.POST.get('next') or 'admin_dashboard')


# ================================================================
# Notifications
# ================================================================

@admin_required
def notifications_view(request):
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'adminpanel/notifications.html', {
        'notifications': notes,
        'unread_count': notes.filter(is_read=False).count(),
    })


@admin_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('admin_notifications')


@admin_required
def dismiss_notification(request, notification_id):
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('admin_notifications')


# ================================================================
# Profile
# ================================================================

@admin_required
def admin_profile(request):
    return render(request, 'adminpanel/profile.html', {
        'total_managed': Patient.objects.count() + Doctor.objects.count() + Receptionist.objects.count(),
    })


@admin_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('admin_profile')

    return render(request, 'adminpanel/edit_profile.html')


@admin_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('admin_change_password')

        if new_password != confirm_new_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('admin_change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password updated successfully.')
        return redirect('admin_profile')

    return render(request, 'adminpanel/change_password.html')
