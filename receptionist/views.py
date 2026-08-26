"""
Views for the receptionist (front-desk) portal.

Covers everything a receptionist does day to day: the dashboard, patient
search/registration/detail, appointment listing/booking/confirmation/
cancellation/no-show handling, the doctor directory, notifications, the
receptionist's own profile/password management, and billing (viewing bills
and marking them paid). Every view here is gated to users whose
`request.user.role == 'receptionist'` via the `receptionist_required`
decorator defined below. As with the rest of this project, there is no
forms.py - POST data is read directly from `request.POST` in each view.
"""

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
from patient.emails import send_appointment_booked_email, send_appointment_cancelled_email

from .models import Receptionist

User = get_user_model()


def receptionist_required(view_func):
    """
    Decorator that restricts a view to logged-in users with role == 'receptionist'.

    Wraps `login_required` (so anonymous users are sent to the login page first),
    then checks the role: non-receptionists get an error message and are
    redirected to `home`. Used on every view in this file.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'receptionist':
            messages.error(request, 'Access restricted to receptionists.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_receptionist(request):
    """
    Return the `Receptionist` profile for the logged-in user, creating it if
    it doesn't exist yet (first login after the account was made). Used by
    every view that needs the current receptionist's profile data.
    """
    receptionist, _ = Receptionist.objects.get_or_create(user=request.user)
    return receptionist


def parse_time_slot(time_slot):
    """
    Parse a time slot string like '09:30 AM' into a `time` object so
    appointments can be sorted chronologically. Falls back to
    `datetime.min.time()` (i.e. sorts first) if the string is missing or
    not in the expected format, so a bad value never raises during sorting.
    """
    try:
        return datetime.strptime(time_slot, '%I:%M %p').time()
    except (ValueError, TypeError):
        return datetime.min.time()


# ================================================================
# Dashboard
# ================================================================

@receptionist_required
def receptionist_dashboard(request):
    """
    Serves the receptionist dashboard (`receptionist_dashboard` URL).

    Restricted to receptionists. Gathers today's appointments (sorted by
    time slot, limited to the first 5), overall patient/doctor counts,
    the count of pending appointments, and the 5 most recently created
    patients, then renders the dashboard template with that summary.
    """
    receptionist = get_receptionist(request)
    today = date.today()

    todays_qs = Appointment.objects.filter(appointment_date=today).select_related('patient__user', 'doctor__user')
    # select_related() + sorted() in Python (rather than .order_by()) because time_slot
    # is stored as a free-text string (e.g. "09:30 AM") and needs parse_time_slot()
    # to sort in actual chronological order.
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
    """
    Serves the patient search/list page (`receptionist_patient_list` URL).

    Restricted to receptionists. Reads an optional `q` search term from the
    query string and, if present, filters patients by name, patient ID,
    phone, or email (case-insensitive partial match). Renders the list of
    matching patients, most recently created first.
    """
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
    """
    Serves walk-in patient registration (`receptionist_register_patient` URL).

    Restricted to receptionists. On GET, shows the raw HTML registration form.
    On POST: validates that the password fields match and the email isn't
    already taken, splits the submitted full name into first/last name,
    creates a new `User` with role='patient', then creates the linked
    `Patient` profile with `registered_by` set to the current receptionist
    (this is how the system tracks which walk-in patients each receptionist
    signed up - see `receptionist_profile` below, which lists them). On
    success, redirects to that patient's detail page.
    """
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

        # Split "First Last Middle..." into first_name (first word) and
        # last_name (everything else); last_name stays blank if only one word given.
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

        # registered_by links this patient record back to the receptionist who
        # walked them through registration at the front desk, for tracking/attribution.
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
    """
    Serves a single patient's detail page (`receptionist_patient_detail` URL).

    Restricted to receptionists. Looks up the patient by ID (404 if not
    found), pulls their full appointment history (most recent first),
    computes their current age from `date_of_birth` if it's set, and
    renders it all in the patient detail template.
    """
    patient = get_object_or_404(Patient.objects.select_related('user', 'registered_by'), id=patient_id)
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor__user').order_by('-appointment_date')

    age = None
    if patient.date_of_birth:
        today = date.today()
        # Subtract 1 from the naive year difference if this year's birthday
        # hasn't happened yet, so the age is accurate before/after the birthday.
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
    """
    Serves the full appointment list (`receptionist_appointment_list` URL).

    Restricted to receptionists. Simply lists every appointment in the
    system, most recent date first, with patient/doctor info preloaded.
    """
    appointments = Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-appointment_date')
    return render(request, 'receptionist/appointment_list.html', {'appointments': appointments})


@receptionist_required
def today_appointments(request):
    """
    Serves today's appointment schedule (`receptionist_today_appointments` URL).

    Restricted to receptionists. Filters appointments to today's date,
    sorts them chronologically by time slot (see `parse_time_slot`), and
    tallies counts by status (total/confirmed/pending/completed) for the
    template's summary bar.
    """
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
    """
    JSON endpoint (`receptionist_get_doctor_slots` URL) used by the booking
    form's JavaScript to fetch a doctor's available time slots for a given
    date, without a full page reload.

    Restricted to receptionists. Reads `doctor` and `date` from the query
    string; returns a 400 JSON error if the date can't be parsed, otherwise
    delegates to `Doctor.get_available_slots()` and returns its result as JSON
    (availability flag, reason if unavailable, and the list of slots).
    """
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
    """
    Serves staff-assisted appointment booking (`receptionist_book_appointment` URL).

    Restricted to receptionists. On GET, shows the booking form (optionally
    pre-selecting a patient via a `?patient=` query param, e.g. when linked
    from that patient's detail page). On POST: validates the patient, doctor,
    date, and time slot were all provided and that the date parses; re-checks
    the doctor's availability for that date/slot server-side (in case it was
    booked in the meantime); then creates the `Appointment` directly with
    status='confirmed' - unlike the patient self-service booking flow
    elsewhere in the project (which leaves new bookings pending an extra
    confirmation step), a receptionist is handling this in person, so it's
    confirmed immediately. A `Billing` row (bill_type='consultation', amount
    = the doctor's `consultation_fee`) is created alongside it, and the
    patient is notified. Redirects to the appointment list on success.
    """
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

        # Find the requested slot among the doctor's available slots for this date,
        # and reject the booking if it isn't listed or if it's already taken.
        matching_slot = next((s for s in availability['slots'] if s['time'] == time_slot), None)
        if matching_slot is None or matching_slot['booked']:
            messages.error(request, 'This slot is already booked.')
            return redirect('receptionist_book_appointment')

        # Booked immediately as 'confirmed' (no pending step) since a receptionist
        # is arranging this in person, unlike patient self-booking elsewhere.
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

        # Auto-generate the consultation bill for this appointment, using the
        # doctor's standard consultation fee as the amount.
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
        send_appointment_booked_email(appointment)

        messages.success(request, 'Appointment booked successfully.')
        return redirect('receptionist_appointment_list')

    return render(request, 'receptionist/book_appointment.html', {
        'patients': patients,
        'doctors': doctors,
        'preselected_patient_id': preselected_patient_id,
    })


@receptionist_required
def confirm_appointment(request, appointment_id):
    """
    Confirms a pending appointment (`receptionist_confirm_appointment` URL).

    Restricted to receptionists. On POST, sets the appointment's status to
    'confirmed', notifies the patient, and shows a success message.
    Redirects back to whatever URL was passed in the `next` POST field, or
    to the appointment list if none was given. GET requests just redirect
    without changing anything.
    """
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
    """
    Cancels an appointment (`receptionist_cancel_appointment` URL).

    Restricted to receptionists. On POST, sets the appointment's status to
    'cancelled', notifies the patient that the front desk cancelled it, and
    shows a success message. Redirects back to the `next` POST field if
    given, otherwise to the appointment list.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        Notification.objects.create(
            user=appointment.patient.user,
            notification_type='cancelled',
            message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.appointment_date} was cancelled by the front desk.',
        )
        send_appointment_cancelled_email(appointment, cancelled_by='the front desk')
        messages.success(request, 'Appointment cancelled.')
    return redirect(request.POST.get('next') or 'receptionist_appointment_list')


@receptionist_required
def mark_no_show(request, appointment_id):
    """
    Marks a patient as a no-show for an appointment (`receptionist_mark_no_show` URL).

    Restricted to receptionists. On POST: if the appointment is already
    cancelled, completed, or already marked no-show, refuses with an error
    (an appointment can only be marked no-show once, from an active state).
    Otherwise, sets its status to 'no_show' and - as a side effect - creates
    a *second*, separate `Billing` row for it with bill_type='no_show_fee'.
    The fee amount is simply the doctor's normal `consultation_fee` (there is
    no separate configurable no-show fee amount); this is billed in addition
    to any existing consultation billing for the same appointment. The patient
    is notified of both the missed appointment and the fee. Redirects back to
    the `next` POST field if given, otherwise to the appointment list.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        if appointment.status in ('cancelled', 'completed', 'no_show'):
            messages.error(request, 'This appointment cannot be marked as a no-show.')
        else:
            appointment.status = 'no_show'
            appointment.save()

            # No-show fee = the doctor's standard consultation fee (not a distinct,
            # configurable penalty amount), billed as its own Billing row.
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
    """
    Serves the billing list (`receptionist_billing_list` URL).

    Restricted to receptionists. Reads an optional `q` search term and, if
    given, filters bills by the associated patient's name or patient ID.
    Also computes `pending_total`, the sum of all bills across the whole
    system still in status='pending' (not just the filtered/displayed set),
    for a summary figure on the page.
    """
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
        # Sum of amounts for ALL pending bills system-wide (Sum returns None with
        # no matching rows, hence "or 0" to default to zero instead of None).
        'pending_total': Billing.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
    })


@receptionist_required
def mark_bill_paid(request, bill_id):
    """
    Marks a bill as paid (`receptionist_mark_bill_paid` URL).

    Restricted to receptionists. On POST, transitions the bill's status to
    'paid' and stamps `paid_at` with the current time, then shows a success
    message. Redirects back to the `next` POST field if given, otherwise to
    the billing list. GET requests just redirect without changing anything.
    """
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
    """
    Serves the doctor directory (`receptionist_doctor_list` URL).

    Restricted to receptionists. For every doctor, builds a row of display
    data: a placeholder photo, whether they're available today, and how
    many non-cancelled appointments they have today. Renders the directory
    template with that list.
    """
    today = date.today()
    today_day = today.strftime('%A').lower()
    doctors = Doctor.objects.select_related('user').all()
    # Look up each doctor's explicit availability record for today's weekday, if one exists.
    availability_map = {a.doctor_id: a for a in DoctorAvailability.objects.filter(day=today_day)}

    doctor_rows = []
    for index, doc in enumerate(doctors):
        avail = availability_map.get(doc.id)
        doctor_rows.append({
            'doctor': doc,
            # No real photo upload for doctors - cycle through 8 placeholder
            # images based on list position so each doctor gets a stable-looking photo.
            'photo_path': f'public/images/doctor-{(index % 8) + 1}.jpg',
            # Use the explicit DoctorAvailability record for today if one exists;
            # otherwise default to "available" on every day except Sunday.
            'available_today': avail.is_available if avail else (today_day != 'sunday'),
            'today_appointment_count': Appointment.objects.filter(doctor=doc, appointment_date=today).exclude(status='cancelled').count(),
        })

    return render(request, 'receptionist/doctor_list.html', {'doctor_rows': doctor_rows})


# ================================================================
# Notifications
# ================================================================

@receptionist_required
def notifications_view(request):
    """
    Serves the receptionist's notification list (`receptionist_notifications` URL).

    Restricted to receptionists. Lists all notifications addressed to the
    logged-in user's account and includes a count of unread ones.
    """
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'receptionist/notifications.html', {
        'notifications': notes,
        'unread_count': notes.filter(is_read=False).count(),
    })


@receptionist_required
def mark_all_read(request):
    """
    Marks every unread notification for the current user as read
    (`receptionist_mark_all_read` URL). Restricted to receptionists.
    Redirects back to the notifications list.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('receptionist_notifications')


@receptionist_required
def dismiss_notification(request, notification_id):
    """
    Deletes a single notification belonging to the current user
    (`receptionist_dismiss_notification` URL). Restricted to receptionists.
    The `user=request.user` filter ensures a receptionist can only dismiss
    their own notifications. Redirects back to the notifications list.
    """
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('receptionist_notifications')


# ================================================================
# Profile
# ================================================================

@receptionist_required
def receptionist_profile(request):
    """
    Serves the receptionist's own profile page (`receptionist_profile` URL).

    Restricted to receptionists. Shows the receptionist's profile info plus
    a count and short list (5 most recent) of patients they've personally
    walk-in registered, found via `Patient.registered_by`.
    """
    receptionist = get_receptionist(request)
    registered_patients = Patient.objects.filter(registered_by=receptionist).select_related('user').order_by('-created_at')

    return render(request, 'receptionist/profile.html', {
        'receptionist': receptionist,
        'total_registered': registered_patients.count(),
        'recent_registrations': registered_patients[:5],
    })


@receptionist_required
def edit_profile(request):
    """
    Serves the receptionist's own profile edit form (`receptionist_edit_profile` URL).

    Restricted to receptionists. On POST, updates the user's name/email on
    the `User` model and the phone/profile picture on the `Receptionist`
    model. Note that `shift` is intentionally not handled here - it cannot
    be changed by the receptionist themselves; only a separate admin-only
    view can update it. Redirects to the profile page on success.
    """
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
    """
    Serves the receptionist's own password change form (`receptionist_change_password` URL).

    Restricted to receptionists. On POST, verifies the submitted current
    password against the stored one, checks the two new-password fields
    match, then sets the new password and calls
    `update_session_auth_hash()` so the receptionist isn't logged out by
    the password change. Redirects to the profile page on success.
    """
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
