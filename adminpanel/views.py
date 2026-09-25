"""Views for the adminpanel app.

This module implements the entire admin portal: the dashboard (with
Chart.js-powered charts for patient/appointment trends), onboarding and
listing of doctors and receptionists, system-wide oversight of patients
and appointments, billing management, the global OTP-login security
toggle, account activation/deactivation, notifications, and the admin's
own profile/password management.

Every view below is decorated with `admin_required`, so only an
authenticated user whose `role` is `'admin'` can reach any of them.
There is no `forms.py` in this project (project-wide convention) --
POST data is read directly from `request.POST` in each view.
"""
from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import SystemSettings
from doctor.models import Doctor
from patient.models import Appointment, Billing, Notification, Patient
from receptionist.models import Receptionist
from input_validation import is_valid_name
from pagination import paginate
from safe_redirect import safe_next_redirect

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
    """Decorator that restricts a view to logged-in users with role='admin'.

    Wraps `view_func` with Django's `login_required` first (so anonymous
    users are sent to the login page), then checks `request.user.role`.
    Non-admin users get an error message and are redirected to `home`
    instead of reaching the view.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            messages.error(request, 'Access restricted to administrators.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def last_n_months(n):
    """Return a list of `n` `date` objects, one per month, oldest first.

    Each date is the first day of its month, ending with the first day of
    the current month. Used to build the x-axis labels/buckets for the
    patient registration trend chart on the dashboard.
    """
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
    """Render the admin dashboard (main landing page after admin login).

    Restricted to admins via `admin_required`. Computes summary stats
    (counts, revenue estimate, outstanding bills) plus the data for the
    three Chart.js charts on the page -- appointments-by-department bar
    chart, appointment-status donut chart, and a 6-month patient
    registration trend line chart. Each chart's labels/data/colors are
    plain Python lists here; the template turns them into JSON for
    Chart.js via the `|json_script:"id"` filter, and the dashboard's JS
    reads that JSON to build the charts. Returns the rendered
    `adminpanel/dashboard.html` template.
    """
    today = date.today()

    revenue_estimate = Appointment.objects.filter(status='completed').aggregate(
        total=Sum('doctor__consultation_fee')
    )['total'] or 0
    outstanding_bills = Billing.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    # --- Chart 1: appointments by department (bar chart) ---
    # Group appointments by department and count them, most popular first.
    department_counts = (
        Appointment.objects.values('department')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Convert each raw department code (e.g. 'cardiology') to its human-readable
    # label for the chart axis, and pull out the matching counts in the same
    # order -- these two lists line up index-for-index, which is what
    # Chart.js expects for its `labels` and `data` arrays.
    department_labels = [DEPARTMENT_LABELS.get(row['department'], row['department']) for row in department_counts]
    department_data = [row['count'] for row in department_counts]

    # --- Chart 2: appointment status breakdown (donut chart) ---
    # Same label/data pairing as above, plus a per-slice color list (looked
    # up from STATUS_COLORS, falling back to a neutral gray) so each status
    # (pending/confirmed/completed/...) is always drawn in the same color.
    status_counts = Appointment.objects.values('status').annotate(count=Count('id'))
    status_labels = [STATUS_LABELS.get(row['status'], row['status']) for row in status_counts]
    status_data = [row['count'] for row in status_counts]
    status_colors = [STATUS_COLORS.get(row['status'], '#6b7280') for row in status_counts]

    # --- Chart 3: patient registrations over the last 6 months (line chart) ---
    # Build one bucket per month (oldest to newest) and count how many
    # patients were created in each, so the x-axis always shows a full
    # 6-month window even for months with zero registrations.
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
    """List all doctors, with an optional search box (admin-only).

    Reads an optional `q` query-string parameter and, if present, filters
    doctors by first/last name, department, or specialization
    (case-insensitive partial match). Renders
    `adminpanel/doctor_list.html` with the (possibly filtered) doctors
    and the current query string.
    """
    query = request.GET.get('q', '').strip()
    doctors = Doctor.objects.select_related('user').order_by('user__first_name', 'id')
    if query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(department__icontains=query)
            | Q(specialization__icontains=query)
        )
    page_obj, elided_page_range = paginate(request, doctors)
    return render(request, 'adminpanel/doctor_list.html', {
        'page_obj': page_obj,
        'elided_page_range': elided_page_range,
        'query': query,
    })


@admin_required
def add_doctor(request):
    """Onboard a new doctor (admin-only).

    On GET, renders the raw HTML add-doctor form
    (`adminpanel/add_doctor.html`) along with the department choices.
    On POST, reads the submitted fields straight from `request.POST`
    (no forms.py, per project convention), validates that the password
    confirmation matches and the email isn't already registered, then
    creates a new `User` with role='doctor' and a linked `Doctor` record
    in one go. On success, redirects to that doctor's detail page; on
    validation failure, redirects back to this same form with an error
    message.
    """
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        department = request.POST.get('department')

        if not all([full_name, email, password, confirm_password, department]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('admin_add_doctor')

        if not is_valid_name(full_name):
            messages.error(request, 'Please enter a valid full name (letters only).')
            return redirect('admin_add_doctor')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_add_doctor')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('admin_add_doctor')

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        try:
            validate_password(password, User(email=email, first_name=first_name, last_name=last_name))
        except ValidationError as exc:
            for error_message in exc.messages:
                messages.error(request, error_message)
            return redirect('admin_add_doctor')

        # experience_years/consultation_fee are unsigned columns -- a
        # negative value would crash with a raw DB error rather than a
        # friendly message, so reject it before it ever reaches .create().
        try:
            experience_years = int(request.POST.get('experience_years') or 0)
            consultation_fee = int(request.POST.get('consultation_fee') or 0)
        except ValueError:
            messages.error(request, 'Experience and consultation fee must be numbers.')
            return redirect('admin_add_doctor')

        if experience_years < 0 or consultation_fee < 0:
            messages.error(request, 'Experience and consultation fee cannot be negative.')
            return redirect('admin_add_doctor')

        # Wrapped in transaction.atomic() so a concurrent duplicate-email
        # submission (racing past the .exists() check above) rolls back
        # the User instead of leaving it orphaned with no Doctor profile.
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role='doctor',
                )

                doctor = Doctor.objects.create(
                    user=user,
                    department=department,
                    specialization=request.POST.get('specialization', ''),
                    phone_number=request.POST.get('phone_number', ''),
                    qualification=request.POST.get('qualification', ''),
                    experience_years=experience_years,
                    consultation_fee=consultation_fee,
                    license_number=request.POST.get('license_number', ''),
                )
        except IntegrityError:
            messages.error(request, 'Email already registered.')
            return redirect('admin_add_doctor')

        messages.success(request, f'Dr. {doctor.user.get_full_name()} has been onboarded successfully.')
        return redirect('admin_doctor_detail', doctor_id=doctor.id)

    return render(request, 'adminpanel/add_doctor.html', {'departments': Doctor.DEPARTMENT_CHOICES})


@admin_required
def doctor_detail(request, doctor_id):
    """Show a single doctor's profile and appointment history (admin-only).

    Looks up the `Doctor` by `doctor_id` (404 if not found) and gathers
    their appointments plus summary counts (total appointments, distinct
    patients seen, completed count). Renders
    `adminpanel/doctor_detail.html` with the doctor, those stats, and the
    8 most recent appointments.
    """
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
    """List all receptionists, with an optional search box (admin-only).

    Reads an optional `q` query-string parameter and, if present, filters
    receptionists by first/last name or employee ID (case-insensitive
    partial match). Renders `adminpanel/receptionist_list.html` with the
    (possibly filtered) receptionists and the current query string. This
    is also the page that hosts the inline shift-change control handled
    by `update_receptionist_shift` below.
    """
    query = request.GET.get('q', '').strip()
    receptionists = Receptionist.objects.select_related('user').order_by('user__first_name', 'id')
    if query:
        receptionists = receptionists.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(employee_id__icontains=query)
        )
    page_obj, elided_page_range = paginate(request, receptionists)
    return render(request, 'adminpanel/receptionist_list.html', {
        'page_obj': page_obj,
        'elided_page_range': elided_page_range,
        'query': query,
    })


@admin_required
def add_receptionist(request):
    """Onboard a new receptionist (admin-only).

    On GET, renders the raw HTML add-receptionist form
    (`adminpanel/add_receptionist.html`). On POST, reads the submitted
    fields from `request.POST`, validates that the password confirmation
    matches and the email isn't already registered, then creates a new
    `User` with role='receptionist' and a linked `Receptionist` record
    (including their initial `shift`, defaulting to 'morning'). On
    success, redirects to the receptionist list; on validation failure,
    redirects back to this same form with an error message.
    """
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not all([full_name, email, password, confirm_password]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('admin_add_receptionist')

        if not is_valid_name(full_name):
            messages.error(request, 'Please enter a valid full name (letters only).')
            return redirect('admin_add_receptionist')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_add_receptionist')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('admin_add_receptionist')

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        try:
            validate_password(password, User(email=email, first_name=first_name, last_name=last_name))
        except ValidationError as exc:
            for error_message in exc.messages:
                messages.error(request, error_message)
            return redirect('admin_add_receptionist')

        # Wrapped in transaction.atomic() so a concurrent duplicate-email
        # submission (racing past the .exists() check above) rolls back
        # the User instead of leaving it orphaned with no Receptionist profile.
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role='receptionist',
                )

                receptionist = Receptionist.objects.create(
                    user=user,
                    phone=request.POST.get('phone', ''),
                    shift=request.POST.get('shift', 'morning'),
                )
        except IntegrityError:
            messages.error(request, 'Email already registered.')
            return redirect('admin_add_receptionist')

        messages.success(request, f'{receptionist.user.get_full_name()} has been onboarded successfully.')
        return redirect('admin_receptionist_list')

    return render(request, 'adminpanel/add_receptionist.html')


@admin_required
def update_receptionist_shift(request, receptionist_id):
    """Change one receptionist's shift (admin-only).

    This is the ONLY place in the whole project where a receptionist's
    `shift` field can be changed -- receptionists cannot edit their own
    shift anymore, so this admin-side view is now the sole mechanism.
    It's wired up as an inline auto-submitting `<select>` per row on the
    receptionist list page (`update_receptionist_shift`'s form submits
    via `onchange="this.form.submit()"`, with no separate submit button),
    rather than a dedicated edit page.

    Looks up the `Receptionist` by `receptionist_id` (404 if not found).
    On POST, validates the submitted `shift` value against
    `Receptionist.SHIFT_CHOICES` before saving it (silently ignoring
    anything invalid). Always redirects back to wherever the request
    came from (the `next` POST field), falling back to the receptionist
    list.
    """
    receptionist = get_object_or_404(Receptionist, id=receptionist_id)
    if request.method == 'POST':
        shift = request.POST.get('shift')
        if shift in dict(Receptionist.SHIFT_CHOICES):
            receptionist.shift = shift
            receptionist.save()
            messages.success(request, f'{receptionist.user.get_full_name()}\'s shift has been updated to {receptionist.get_shift_display()}.')
    return safe_next_redirect(request, 'admin_receptionist_list')


# ================================================================
# Patients
# ================================================================

@admin_required
def patient_list(request):
    """List all patients system-wide, with an optional search box (admin-only).

    Reads an optional `q` query-string parameter and, if present, filters
    patients by first/last name, patient ID, or email (case-insensitive
    partial match). Renders `adminpanel/patient_list.html` with the
    (possibly filtered) patients and the current query string.
    """
    query = request.GET.get('q', '').strip()
    patients = Patient.objects.select_related('user', 'registered_by__user').order_by('-created_at', '-id')
    if query:
        patients = patients.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(patient_id__icontains=query)
            | Q(user__email__icontains=query)
        )
    page_obj, elided_page_range = paginate(request, patients)
    return render(request, 'adminpanel/patient_list.html', {
        'page_obj': page_obj,
        'elided_page_range': elided_page_range,
        'query': query,
    })


@admin_required
def patient_detail(request, patient_id):
    """Show a single patient's profile and appointment history (admin-only).

    Looks up the `Patient` by `patient_id` (404 if not found), computes
    their age from `date_of_birth` (if set), and gathers their full
    appointment history. Renders `adminpanel/patient_detail.html` with
    the patient, computed age, and appointments.
    """
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
    """List every appointment system-wide, newest first (admin-only).

    Reads optional `status` and `q` query-string parameters -- `status`
    narrows to one Appointment.status value (or 'all', the default), `q`
    searches the patient's and doctor's names (case-insensitive partial
    match). This used to be done entirely client-side in JS over every row
    already in the DOM; it's server-side now so it keeps working once the
    list is paginated (a client-side filter could otherwise only ever see
    whatever rows happen to be on the current page).
    """
    status = request.GET.get('status', 'all')
    query = request.GET.get('q', '').strip()

    appointments = Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-appointment_date', '-id')

    if status and status != 'all':
        appointments = appointments.filter(status=status)

    if query:
        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=query)
            | Q(patient__user__last_name__icontains=query)
            | Q(doctor__user__first_name__icontains=query)
            | Q(doctor__user__last_name__icontains=query)
        )

    page_obj, elided_page_range = paginate(request, appointments)
    return render(request, 'adminpanel/appointment_list.html', {
        'page_obj': page_obj,
        'elided_page_range': elided_page_range,
        'query': query,
        'current_status': status,
    })


@admin_required
def update_appointment_status(request, appointment_id):
    """Change any appointment's status system-wide (admin-only).

    This is the mechanism for an admin to correct a status a doctor (or
    anyone else) set by mistake -- e.g. an appointment marked 'completed'
    by accident can be reverted back to 'confirmed'. Wired up as an
    inline auto-submitting `<select>` per row on the admin appointment
    list, the same pattern `update_receptionist_shift` above uses for
    shift.

    Looks up the `Appointment` by `appointment_id` (404 if not found;
    deliberately not scoped to a doctor/patient, since admin oversight is
    system-wide). On POST, validates the submitted `status` value against
    `Appointment.STATUS_CHOICES` before saving it (silently ignoring
    anything invalid). Always redirects back to wherever the request
    came from (the `next` POST field), falling back to the appointment
    list.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Appointment.STATUS_CHOICES):
            appointment.status = status
            appointment.save()
            messages.success(request, f"Appointment status updated to {appointment.get_status_display()}.")
    return safe_next_redirect(request, 'admin_appointment_list')


# ================================================================
# Billing
# ================================================================

@admin_required
def billing_list(request):
    """List all bills, with an optional search box (admin-only).

    Reads an optional `q` query-string parameter and, if present, filters
    bills by the patient's first/last name or patient ID
    (case-insensitive partial match). Renders
    `adminpanel/billing_list.html` with the (possibly filtered) bills,
    the current query string, and the total amount still outstanding
    across all pending bills.
    """
    query = request.GET.get('q', '').strip()
    bills = Billing.objects.select_related('patient__user', 'appointment__doctor__user').order_by('-created_at', '-id')

    if query:
        bills = bills.filter(
            Q(patient__user__first_name__icontains=query)
            | Q(patient__user__last_name__icontains=query)
            | Q(patient__patient_id__icontains=query)
        )

    page_obj, elided_page_range = paginate(request, bills)
    return render(request, 'adminpanel/billing_list.html', {
        'page_obj': page_obj,
        'elided_page_range': elided_page_range,
        'query': query,
        'pending_total': Billing.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
    })


@admin_required
def mark_bill_paid(request, bill_id):
    """Mark a single bill as paid (admin-only).

    Looks up the `Billing` record by `bill_id` (404 if not found). On
    POST, sets its `status` to 'paid' and stamps `paid_at` with the
    current time. Always redirects back to wherever the request came
    from (the `next` POST field), falling back to the billing list.
    """
    bill = get_object_or_404(Billing, id=bill_id)
    if request.method == 'POST':
        bill.status = 'paid'
        bill.paid_at = timezone.now()
        bill.save()
        messages.success(request, 'Bill marked as paid.')
    return safe_next_redirect(request, 'admin_billing_list')


@admin_required
def billing_receipt(request, bill_id):
    """Printable receipt for one bill (admin-only, system-wide).

    Read-only -- just looks up the `Billing` by `bill_id` (404 if not
    found) and renders `adminpanel/billing_receipt.html`. That template
    is a print-friendly page (a "Print" button calling `window.print()`
    plus an `@media print` rule hiding the sidebar/topbar/actions) --
    this project has no PDF library, so every "receipt"/"printout" here
    follows the same browser-print pattern already used by
    `doctor/patient_details.html` and `doctor/prescription_history.html`.
    """
    bill = get_object_or_404(Billing, id=bill_id)
    return render(request, 'adminpanel/billing_receipt.html', {'bill': bill})


# ================================================================
# Security Settings
# ================================================================

@admin_required
def security_settings(request):
    """View/toggle the hospital-wide OTP login setting (admin-only).

    `SystemSettings.get_solo()` fetches (or creates) the single
    DB-backed settings row shared by the whole application -- there is
    only ever one instance. Its `otp_login_enabled` flag is a global
    switch, not a per-account preference: flipping it here turns
    OTP-based (two-step) login on or off for EVERY account in the
    hospital, across all 4 roles (admin/doctor/receptionist/patient) at
    once, not just for the admin who changes it.

    On GET, renders `adminpanel/security_settings.html` with the current
    settings, which shows a single toggle switch that auto-submits the
    form via `onchange="this.form.submit()"` (no separate save button).
    On POST, sets `otp_login_enabled` based on whether the checkbox was
    present in the submitted data, saves it, and redirects back to this
    same page with a confirmation message.
    """
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
    """Flip a user's active/inactive status (admin-only).

    This is the account activate/deactivate mechanism for the whole
    project -- there is deliberately NO separate "delete user" feature;
    disabling login access is done by toggling `User.is_active` instead
    of removing the account. Works generically for any user
    (doctor/receptionist/patient), which is why the URL just takes a
    `user_id` rather than being split per role.

    Looks up the target `User` by `user_id` (404 if not found). On POST,
    first checks `target.role == 'admin'`: if the target is an admin
    account, the toggle is refused outright (an error message is shown
    and nothing is changed) so that admins can never deactivate another
    admin -- including themselves -- through this view. For any
    non-admin target, `is_active` is simply flipped to its opposite
    value and saved. Either way, redirects back to wherever the request
    came from (the `next` POST field), falling back to the dashboard.
    """
    target = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if target.role == 'admin':
            messages.error(request, 'Administrator accounts cannot be deactivated from here.')
        else:
            target.is_active = not target.is_active
            target.save()
            state = 'activated' if target.is_active else 'deactivated'
            messages.success(request, f'{target.get_full_name()} has been {state}.')

    return safe_next_redirect(request, 'admin_dashboard')


# ================================================================
# Notifications
# ================================================================

@admin_required
def notifications_view(request):
    """Show the logged-in admin's notification inbox (admin-only).

    Fetches all `Notification` rows belonging to `request.user` and
    renders `adminpanel/notifications.html` with the full list plus a
    count of unread ones.
    """
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'adminpanel/notifications.html', {
        'notifications': notes,
        'unread_count': notes.filter(is_read=False).count(),
    })


@admin_required
def mark_all_read(request):
    """Mark all of the logged-in admin's unread notifications as read.

    Bulk-updates every unread `Notification` belonging to `request.user`
    in a single query, then redirects back to the notifications page.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('admin_notifications')


@admin_required
def dismiss_notification(request, notification_id):
    """Delete a single notification belonging to the logged-in admin.

    Filters by both `notification_id` and `user=request.user` so an
    admin can only ever delete their own notifications, then deletes it
    and redirects back to the notifications page.
    """
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('admin_notifications')


# ================================================================
# Profile
# ================================================================

@admin_required
def admin_profile(request):
    """Show the logged-in admin's profile page (admin-only).

    Renders `adminpanel/profile.html` with a single summary figure --
    the combined total of all patients, doctors, and receptionists
    managed through this portal.
    """
    return render(request, 'adminpanel/profile.html', {
        'total_managed': Patient.objects.count() + Doctor.objects.count() + Receptionist.objects.count(),
    })


@admin_required
def edit_profile(request):
    """Edit the logged-in admin's own name/email (admin-only).

    On GET, renders the raw HTML edit-profile form
    (`adminpanel/edit_profile.html`). On POST, updates
    `request.user`'s first name, last name, and email directly from
    `request.POST` and saves, then redirects to the profile page with a
    success message.
    """
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        if not all([first_name, last_name, email]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('admin_profile')

        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('admin_profile')

    return render(request, 'adminpanel/edit_profile.html')


@admin_required
def change_password(request):
    """Change the logged-in admin's own password (admin-only).

    On GET, renders the raw HTML change-password form
    (`adminpanel/change_password.html`). On POST, verifies the supplied
    current password with `check_password`, checks the new password
    confirmation matches, then sets the new password and calls
    `update_session_auth_hash` so the admin isn't logged out by the
    password change. Redirects to the profile page on success, or back
    to this same form with an error message on failure.
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('admin_change_password')

        if not new_password or not confirm_new_password:
            messages.error(request, 'Please fill in both new password fields.')
            return redirect('admin_change_password')

        if new_password != confirm_new_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('admin_change_password')

        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            for error_message in exc.messages:
                messages.error(request, error_message)
            return redirect('admin_change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password updated successfully.')
        return redirect('admin_profile')

    return render(request, 'adminpanel/change_password.html')
