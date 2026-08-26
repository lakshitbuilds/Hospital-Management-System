"""
Views for the doctor-side portal of the Hospital Management System.

Covers everything a logged-in doctor (accounts.User with role='doctor') can
do: view their dashboard, manage today's/all appointments, look up a
patient's history, write and review prescriptions, configure their weekly
availability and blocked (holiday) dates, manage notifications, and edit
their own profile/password. Every view below is wrapped in `doctor_required`,
which gates access to the doctor role only.

As with the rest of this project, there is no forms.py -- all forms are
plain HTML <form method="POST"> elements in the templates, and fields are
read directly off request.POST / request.GET / request.FILES.
"""
from datetime import datetime, date
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from .models import Doctor, DoctorAvailability, BlockedDate, Prescription, PrescriptionMedicine
from patient.models import Patient, Appointment, Notification
from patient.emails import send_appointment_cancelled_email


def doctor_required(view_func):
    """
    Decorator applied to every view in this module to restrict access to
    logged-in users with role='doctor'. Wraps `login_required` (so an
    anonymous user is first sent to the login page), and additionally
    rejects any logged-in user whose role isn't 'doctor' -- showing an
    error message and redirecting them to the site home page instead of
    running the wrapped view.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'doctor':
            messages.error(request, 'Access restricted to doctors.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def parse_time_slot(time_slot):
    """
    Convert a stored time_slot string (e.g. "09:30 AM") into a real `time`
    object so appointments can be sorted chronologically. Falls back to
    midnight for a missing/malformed value instead of raising, so one bad
    value just sorts first rather than breaking the page.
    """
    try:
        return datetime.strptime(time_slot, '%I:%M %p').time()
    except (ValueError, TypeError):
        return datetime.min.time()


def get_doctor(request):
    """
    Look up the Doctor profile linked (one-to-one) to the currently
    logged-in user. Every view below calls this to scope its queries to
    "this doctor's" own data. Raises Http404 if the logged-in user has no
    Doctor profile row.
    """
    return get_object_or_404(Doctor, user=request.user)


# ================================================================
# Dashboard
# ================================================================

@doctor_required
def doctor_home(request):
    """
    Serves the `doctor_dashboard` URL -- the doctor's landing page after
    login. Restricted to the doctor role via `doctor_required`.

    Gathers summary stats for the logged-in doctor: today's appointments
    (capped to the soonest 4), a distinct count of all patients ever seen,
    how many completed appointments still have no prescription attached,
    how many appointments fall in the current month, and the 3 most
    recently-seen distinct patients. Renders 'doctor/dashboard.html'.
    """
    doctor = get_doctor(request)
    today = date.today()

    todays_qs = Appointment.objects.filter(doctor=doctor, appointment_date=today).select_related('patient__user')
    todays_appointments = sorted(todays_qs, key=lambda a: parse_time_slot(a.time_slot))[:4]

    total_patients = Patient.objects.filter(appointments__doctor=doctor).distinct().count()
    # An appointment counts as "pending prescription" once it's completed
    # but no Prescription row has been linked to it yet.
    pending_prescriptions = Appointment.objects.filter(doctor=doctor, status='completed', prescriptions__isnull=True).count()
    appointments_this_month = Appointment.objects.filter(doctor=doctor, appointment_date__month=today.month, appointment_date__year=today.year).count()

    # Build the 3 most recently-seen *distinct* patients: walk this
    # doctor's appointments newest-first and keep the first (most recent)
    # occurrence of each patient_id, stopping once 3 unique patients have
    # been collected. A plain .distinct() on the queryset wouldn't preserve
    # "most recent" ordering once duplicates are removed, so this is done
    # manually in Python instead.
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
    """
    Serves the `today_appointments` URL: lists all of this doctor's
    appointments scheduled for today, sorted by time of day, along with a
    breakdown of how many are completed/pending/upcoming. Restricted to the
    doctor role. Renders 'doctor/today_appointments.html'.
    """
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
    """
    POST-only action (restricted to the doctor role) that marks a single
    appointment as 'completed'. The `doctor=doctor` filter in the lookup
    below ensures a doctor can only complete their own appointments (a 404
    is raised otherwise). Redirects back to whichever page the form's
    hidden 'next' field points to, defaulting to `today_appointments`.
    """
    doctor = get_doctor(request)
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=doctor)
    if request.method == 'POST':
        appointment.status = 'completed'
        appointment.save()
    return redirect(request.POST.get('next') or 'today_appointments')


@doctor_required
def appointment_list(request):
    """
    Serves the `appointment_list` URL: the full history of this doctor's
    appointments (all dates/statuses), newest first. Restricted to the
    doctor role. Renders 'doctor/appointment_list.html'.
    """
    doctor = get_doctor(request)
    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient__user').order_by('-appointment_date')
    return render(request, 'doctor/appointment_list.html', {'appointments': appointments})


@doctor_required
def doctor_cancel_appointment(request, appointment_id):
    """
    POST-only action (restricted to the doctor role) that lets a doctor
    cancel one of their own appointments (again scoped via `doctor=doctor`
    so a doctor can't cancel another doctor's appointment). Sets the
    appointment status to 'cancelled' and creates a Notification so the
    patient is informed it was the doctor who cancelled. Redirects to
    `appointment_list`.
    """
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
        send_appointment_cancelled_email(appointment, cancelled_by='the doctor')
    return redirect('appointment_list')


# ================================================================
# Patients
# ================================================================

@doctor_required
def patient_details(request, patient_id):
    """
    Serves the `patient_details` URL: shows one patient's profile,
    appointment history with this doctor, and prescriptions written by this
    doctor. Restricted to the doctor role, and further restricted to
    patients this doctor has actually had an appointment with -- the
    `appointments__doctor=doctor` filter below means a doctor can't view an
    arbitrary patient's page just by guessing an id (404 otherwise).
    Renders 'doctor/patient_details.html'.
    """
    doctor = get_doctor(request)
    # `appointments__doctor=doctor` joins through the patient's
    # appointments; .distinct() avoids the same patient appearing more than
    # once in that join if they have several appointments with this doctor.
    patient = get_object_or_404(Patient.objects.distinct(), id=patient_id, appointments__doctor=doctor)

    history = Appointment.objects.filter(doctor=doctor, patient=patient).order_by('-appointment_date')
    prescriptions = Prescription.objects.filter(doctor=doctor, patient=patient).prefetch_related('medicines')

    # Compute age in whole years from date_of_birth: start with the year
    # difference, then subtract 1 if this year's birthday hasn't happened
    # yet (i.e. today's (month, day) is still earlier than the birthday's).
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
    """
    Serves the `add_prescription` URL. Restricted to the doctor role.

    On GET: shows the prescription form, with the patient/appointment
    dropdowns limited to this doctor's own patients/appointments, optionally
    pre-selected via `?patient=` / `?appointment=` query params (e.g. when
    linked to from a patient's detail page).

    On POST: creates one Prescription for the chosen patient (re-checking
    that the patient belongs to this doctor), then creates one
    PrescriptionMedicine per medicine row submitted from the dynamic
    "add another medicine" form fields, notifies the patient, and redirects
    to `prescription_history`.
    """
    doctor = get_doctor(request)
    patients = Patient.objects.filter(appointments__doctor=doctor).select_related('user').distinct()

    preselected_patient_id = request.GET.get('patient')
    preselected_appointment_id = request.GET.get('appointment')

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        # Linking to a specific appointment is optional, so an empty
        # submission is normalized to None rather than an empty string.
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

        # The template lets the doctor add any number of medicine rows
        # dynamically, so each field comes back as a same-length parallel
        # list (medicine_name[], dosage[], ...) rather than one fixed set of
        # POST keys. We iterate by index, using `names` as the reference
        # list and skipping any row where the medicine name was left blank;
        # the `i < len(...)` guards protect against a row where one of the
        # other fields wasn't submitted at all.
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
    """
    Serves the `prescription_history` URL: lists every prescription this
    doctor has written (with their medicine line items prefetched), ordered
    newest first per the Prescription model's default Meta.ordering.
    Restricted to the doctor role. Renders 'doctor/prescription_history.html'.
    """
    doctor = get_doctor(request)
    prescriptions = Prescription.objects.filter(doctor=doctor).select_related('patient__user').prefetch_related('medicines')
    return render(request, 'doctor/prescription_history.html', {'prescriptions': prescriptions})


# ================================================================
# Availability
# ================================================================

@doctor_required
def availability(request):
    """
    Serves the `availability` URL: lets a doctor configure their recurring
    weekly schedule and one-off blocked (holiday) dates. Restricted to the
    doctor role.

    On POST: for each weekday, creates/updates the matching
    DoctorAvailability row (is_available flag + start/end time) from the
    submitted checkbox/time inputs; updates the doctor's slot_duration,
    buffer_time and max_per_day scheduling settings; then wipes and
    recreates all of this doctor's BlockedDate rows from the submitted
    parallel date/reason lists. Redirects back to `availability`.

    On GET: builds a full Monday-Sunday `weekly_schedule` list for display,
    falling back to sensible defaults (09:00-17:00 on weekdays, 09:00-13:00
    Saturday, closed Sunday) for any day that has no saved
    DoctorAvailability row yet.
    """
    doctor = get_doctor(request)
    days = [d[0] for d in DoctorAvailability.DAY_CHOICES]

    if request.method == 'POST':
        # One DoctorAvailability row is created/updated per weekday, keyed
        # by (doctor, day) -- update_or_create relies on that unique_together
        # constraint to either update the existing row or insert a new one.
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

        # Simplest way to sync the blocked-dates list from a raw HTML form
        # with no per-row database ids: delete all of this doctor's
        # existing BlockedDate rows and recreate them fresh from whatever
        # date/reason rows were submitted this time.
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

    # For any weekday the doctor hasn't explicitly configured yet, fall back
    # to a default schedule rather than showing it as blank: open every day
    # except Sunday, 09:00-17:00, with a shorter 09:00-13:00 day on Saturday.
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
    """
    Serves the doctor's notification inbox. Restricted to the doctor role,
    and scoped to `user=request.user` so a doctor only ever sees their own
    notifications. Renders 'doctor/notifications.html' with the full list
    plus an unread count.
    """
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'doctor/notifications.html', {
        'notifications': notes,
        'unread_count': notes.filter(is_read=False).count(),
    })


@doctor_required
def mark_all_read(request):
    """
    Marks every unread notification belonging to the logged-in doctor as
    read, then redirects back to the `doctor_notifications` page.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('doctor_notifications')


@doctor_required
def dismiss_notification(request, notification_id):
    """
    Deletes a single notification belonging to the logged-in doctor. The
    `user=request.user` filter ensures a doctor can only dismiss their own
    notifications (deleting nothing if the id doesn't belong to them, rather
    than raising). Redirects back to `doctor_notifications`.
    """
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('doctor_notifications')


# ================================================================
# Profile
# ================================================================

@doctor_required
def doctor_profile(request):
    """
    Serves the `doctor_profile` URL: a read-only view of the doctor's own
    profile, showing their details, a distinct count of all patients seen,
    and their weekly schedule (formatted in 12-hour time for display).
    Restricted to the doctor role. Renders 'doctor/doctor_profile.html'.
    """
    doctor = get_doctor(request)
    total_patients = Patient.objects.filter(appointments__doctor=doctor).distinct().count()

    # Same day-off/default-hours fallback as the `availability` view above,
    # just formatted here as 12-hour times (e.g. "09:00 AM") for display.
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
    """
    Serves the `edit_profile` URL. Restricted to the doctor role.

    On GET: shows the edit form pre-filled from the doctor's linked User and
    Doctor rows.

    On POST: updates the basic account fields (first/last name, email) on
    the shared accounts.User, and the hospital-specific fields (phone,
    department, specialization, qualification, experience, consultation
    fee, bio, and optionally a new profile picture) on the Doctor profile.
    Redirects to `doctor_profile` on success.
    """
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
    """
    Serves the `change_password` URL, letting the logged-in doctor change
    their own account password. Restricted to the doctor role.

    On POST: verifies the submitted current password against the stored
    hash, checks the two new-password fields match, then sets and saves the
    new password. `update_session_auth_hash` is called afterwards so
    changing the password doesn't invalidate the doctor's current session
    (Django would otherwise log them out on password change). Redirects to
    `doctor_profile` on success, or back to `change_password` with an error
    message on validation failure.
    """
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
