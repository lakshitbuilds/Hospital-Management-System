from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout, get_user_model
from django.contrib.auth.decorators import login_required

from .models import Patient, Appointment, ContactMessage, Notification
from doctor.models import Doctor

User = get_user_model()


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
    return render(request, "patient/doctors.html")


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

        user = authenticate(request, username=email, password=password)

        if user is not None:
            auth_login(request, user)

            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'doctor':
                return redirect('doctor_dashboard')
            elif user.role == 'receptionist':
                return redirect('receptionist_dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    return render(request, "patient/login.html")


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

        messages.success(request, 'Account created successfully. Please login.')
        return redirect('login')

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

    return render(request, 'patient/profile.html', {'patient': patient})


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

        if Appointment.objects.filter(doctor=doctor, appointment_date=appointment_date, time_slot=time_slot).exists():
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