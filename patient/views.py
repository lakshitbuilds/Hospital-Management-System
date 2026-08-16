import secrets
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from .models import Patient, Appointment, ContactMessage, Notification
from doctor.models import Doctor

User = get_user_model()


ROLE_REDIRECTS = {
    'admin': 'admin_dashboard',
    'doctor': 'doctor_home',
    'receptionist': 'receptionist_dashboard',
}


def _send_otp_email(user):
    otp = f'{secrets.randbelow(1000000):06d}'
    user.otp_code = otp
    user.otp_created_at = timezone.now()
    user.save(update_fields=['otp_code', 'otp_created_at'])

    context = {
        'otp': otp,
        'valid_minutes': settings.OTP_VALID_MINUTES,
        'first_name': user.first_name,
        'current_year': user.otp_created_at.year,
    }
    text_body = (
        f'Hi {user.first_name or "there"}, your MediCare Hospital login code is {otp}. '
        f'It expires in {settings.OTP_VALID_MINUTES} minutes.'
    )
    html_body = render_to_string('patient/emails/otp_email.html', context)

    email = EmailMultiAlternatives(
        subject='Your MediCare Hospital login code',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_body, 'text/html')
    email.send(fail_silently=False)


def _redirect_for_role(request, user):
    target = ROLE_REDIRECTS.get(user.role)
    if target:
        try:
            return redirect(reverse(target))
        except NoReverseMatch:
            messages.info(request, f'{user.role.capitalize()} dashboard is not available yet.')
            return redirect('home')
    return redirect('home')


# ================================================================
# Public Pages
# ================================================================

def home(request):
    return render(request, "patient/index.html")


def about(request):
    return render(request, "patient/about.html")


def services(request):
    return render(request, "patient/services.html")


def department(request):
    return render(request, "patient/departments.html")


def doctors(request):
    doctor_list = list(Doctor.objects.select_related('user').all())
    for index, doc in enumerate(doctor_list):
        doc.photo_path = f'public/images/doctor-{(index % 8) + 1}.jpg'
    return render(request, "patient/doctors.html", {'doctors': doctor_list})


def contact(request):
    if request.method == 'POST':
        ContactMessage.objects.create(
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message'),
        )
        messages.success(request, 'Your message has been received.')
        return redirect('contact')

    return render(request, 'patient/contact.html')


# ================================================================
# Auth
# ================================================================

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        selected_role = request.POST.get('role')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if selected_role and user.role != selected_role:
                messages.error(request, f'This account is not registered as {selected_role.capitalize()}. Please select the correct role and try again.')
                return redirect('login')

            _send_otp_email(user)
            request.session['pending_otp_user_id'] = user.id

            messages.success(request, f'A verification code has been sent to {user.email}.')
            return redirect('verify_otp')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    return render(request, "patient/login.html")


def verify_otp(request):
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.error(request, 'Please login again.')
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        entered_code = request.POST.get('otp_code', '').strip()
        expiry = user.otp_created_at + timedelta(minutes=settings.OTP_VALID_MINUTES) if user.otp_created_at else None

        if not user.otp_code or not expiry or timezone.now() > expiry:
            messages.error(request, 'This code has expired. Please request a new one.')
            return redirect('verify_otp')

        if entered_code != user.otp_code:
            messages.error(request, 'Incorrect verification code.')
            return redirect('verify_otp')

        user.otp_code = None
        user.otp_created_at = None
        user.save(update_fields=['otp_code', 'otp_created_at'])
        del request.session['pending_otp_user_id']

        auth_login(request, user)
        return _redirect_for_role(request, user)

    return render(request, 'patient/verify_otp.html', {'email': user.email})


def resend_otp(request):
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.error(request, 'Please login again.')
        return redirect('login')

    user = get_object_or_404(User, id=user_id)
    _send_otp_email(user)
    messages.success(request, f'A new verification code has been sent to {user.email}.')
    return redirect('verify_otp')


def register(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        dob = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='patient'
        )

        Patient.objects.create(
            user=user,
            phone=phone,
            date_of_birth=dob,
            gender=gender.capitalize()
        )

        _send_otp_email(user)
        request.session['pending_otp_user_id'] = user.id

        messages.success(request, f'Account created. A verification code has been sent to {user.email}.')
        return redirect('verify_otp')

    return render(request, 'patient/register.html')


def forgot_password(request):
    return render(request, "patient/forgot_password.html")


def logout_view(request):
    logout(request)
    return redirect('login')


# ================================================================
# Patient Profile
# ================================================================

@login_required
def patient_profile(request):
    patient, created = Patient.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()

        patient.phone = request.POST.get('phone')
        patient.date_of_birth = request.POST.get('date_of_birth') or None
        patient.gender = request.POST.get('gender')
        patient.blood_group = request.POST.get('blood_group')
        patient.address = request.POST.get('address')
        patient.city = request.POST.get('city')
        patient.state = request.POST.get('state')
        patient.country = request.POST.get('country')
        patient.pincode = request.POST.get('pincode')
        patient.emergency_contact_name = request.POST.get('emergency_contact_name')
        patient.emergency_contact_number = request.POST.get('emergency_contact_number')
        patient.allergies = request.POST.get('allergies')
        patient.medical_history = request.POST.get('medical_history')

        if request.FILES.get('profile_image'):
            patient.profile_image = request.FILES['profile_image']

        patient.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('patient_profile')

    context = {
        'patient': patient,
        'appointments_count': patient.appointments.count(),
        'prescriptions_count': patient.prescriptions.count(),
        'member_since_year': patient.created_at.year,
    }
    return render(request, 'patient/profile.html', context)


# ================================================================
# Appointments
# ================================================================

@login_required
def book_appointment(request):
    doctors = Doctor.objects.select_related('user').all()

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        if not doctor_id:
            messages.error(request, 'Please select a doctor.')
            return redirect('book_appointment')

        doctor = get_object_or_404(Doctor, id=doctor_id)
        patient = Patient.objects.get(user=request.user)

        department = request.POST.get('department')
        appointment_date = request.POST.get('appointment_date')
        time_slot = request.POST.get('time_slot')
        visit_type = request.POST.get('visit_type')
        reason = request.POST.get('reason')

        if Appointment.objects.filter(doctor=doctor, appointment_date=appointment_date, time_slot=time_slot).exclude(status='cancelled').exists():
            messages.error(request, 'This slot is already booked.')
            return redirect('book_appointment')

        Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            department=department,
            appointment_date=appointment_date,
            time_slot=time_slot,
            visit_type=visit_type,
            reason=reason,
        )

        Notification.objects.create(
            user=request.user,
            notification_type='general',
            message=f'Your appointment with Dr. {doctor.user.get_full_name()} has been requested.'
        )

        messages.success(request, 'Appointment request sent successfully.')
        return redirect('my_appointments')

    return render(request, 'patient/book_appointment.html', {'doctors': doctors})


@login_required
def my_appointments(request):
    patient = Patient.objects.get(user=request.user)
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor__user').order_by('-appointment_date')
    return render(request, 'patient/my_appointments.html', {'appointments': appointments})


@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__user=request.user)

    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()

        Notification.objects.create(
            user=request.user,
            notification_type='cancelled',
            message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} was cancelled.'
        )

    return redirect('my_appointments')


# ================================================================
# Notifications
# ================================================================

@login_required
def notifications_view(request):
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'patient/notifications.html', {'notifications': notes})


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')


@login_required
def dismiss_notification(request, notification_id):
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('notifications')