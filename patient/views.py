"""
Views for the ``patient`` app.

This module is the busiest file in the project. It serves three groups of
pages:

1. Public marketing pages (home/about/services/department/doctors/contact)
   that any visitor can see.
2. The SHARED authentication flow for ALL FOUR roles (admin, doctor,
   receptionist, patient) -- ``login``, ``verify_otp``, ``resend_otp``,
   ``register``, ``logout_view``. Login is a two-step process: a normal
   email/password check via ``authenticate()``, followed by an email OTP
   (one-time passcode) step before Django's real session login happens.
   Whether the OTP step runs at all is controlled by the
   ``accounts.SystemSettings.get_solo().otp_login_enabled`` database flag
   (NOT the old, unused ``settings.OTP_LOGIN_ENABLED``).
3. Patient-only self-service pages: profile editing, appointment booking
   (with a "pay at the front desk" billing checkpoint before the
   appointment is actually created), viewing bills, and notifications.

House style note: this project has no ``forms.py`` anywhere. Every POST
handler below reads fields straight off ``request.POST.get(...)`` from
plain HTML ``<form method="POST">`` templates -- that is intentional, not
an oversight.
"""

import secrets
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse, NoReverseMatch
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.http import JsonResponse
from django.db import IntegrityError

from .models import Patient, Appointment, Billing, ContactMessage, Notification
from .emails import send_appointment_booked_email, send_appointment_cancelled_email
from doctor.models import Doctor
from image_validation import validate_uploaded_image
from accounts.models import SystemSettings

User = get_user_model()


# Maps each non-patient role to the URL name of its own dashboard, used by
# _redirect_for_role() below to send freshly logged-in users to the right
# place. Patients aren't listed here because they fall through to the
# default 'home' redirect.
ROLE_REDIRECTS = {
    'admin': 'admin_dashboard',
    'doctor': 'doctor_home',
    'receptionist': 'receptionist_dashboard',
}


def _send_otp_email(user):
    """
    Generate a fresh 6-digit one-time passcode for ``user``, store it (plus
    when it was created and a reset attempt counter) on the User row, and
    email it to them. Called both when a login first requires OTP and when
    the user asks for the code to be resent (``resend_otp``). Does not
    touch ``otp_locked_until`` -- lockouts are only set/cleared elsewhere.
    """
    # secrets.randbelow gives a cryptographically random 0-999999 integer;
    # zero-padding to 6 digits keeps codes like "000042" formatted properly.
    otp = f'{secrets.randbelow(1000000):06d}'
    user.otp_code = otp
    user.otp_created_at = timezone.now()
    user.otp_attempts = 0
    user.save(update_fields=['otp_code', 'otp_created_at', 'otp_attempts'])

    context = {
        'otp': otp,
        'valid_minutes': settings.OTP_VALID_MINUTES,
        'first_name': user.first_name,
        'current_year': user.otp_created_at.year,
    }
    minute_word = 'minute' if settings.OTP_VALID_MINUTES == 1 else 'minutes'
    text_body = (
        f'Hi {user.first_name or "there"}, your MediCare Hospital login code is {otp}. '
        f'It expires in {settings.OTP_VALID_MINUTES} {minute_word}.'
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


def _send_password_reset_email(request, user):
    """
    Emails ``user`` a signed, single-use link to reset_password_confirm.
    Uses the same primitives Django's own PasswordResetView relies on
    (default_token_generator + a base64-encoded pk): the token embeds a hash
    of the user's current password, so it stops working the moment
    set_password() changes it (natural single-use), and it expires after
    PASSWORD_RESET_TIMEOUT seconds (see settings.py).

    fail_silently=True, matching the appointment emails rather than the OTP
    one: forgot_password always shows the same "check your email" message
    regardless of whether this send actually succeeds, to avoid letting the
    page be used to probe which addresses have accounts -- so there is
    nothing useful this call could raise back up to the request anyway.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = request.build_absolute_uri(
        reverse('reset_password_confirm', kwargs={'uidb64': uidb64, 'token': token})
    )
    valid_minutes = settings.PASSWORD_RESET_TIMEOUT // 60

    context = {
        'first_name': user.first_name,
        'reset_url': reset_url,
        'valid_minutes': valid_minutes,
        'current_year': timezone.now().year,
    }
    text_body = (
        f'Hi {user.first_name or "there"}, use this link to reset your MediCare Hospital password: '
        f'{reset_url} (expires in {valid_minutes} minutes).'
    )
    html_body = render_to_string('patient/emails/password_reset_email.html', context)

    email = EmailMultiAlternatives(
        subject='Reset your MediCare Hospital password',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_body, 'text/html')
    email.send(fail_silently=True)


def _redirect_for_role(request, user):
    """
    Send a just-authenticated user to their role's dashboard. Looks up the
    URL name in ROLE_REDIRECTS (admin/doctor/receptionist); patients, and
    any role whose dashboard URL doesn't resolve yet (NoReverseMatch), fall
    back to the public 'home' page. Used after both password+OTP login and
    fresh registration.
    """
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
    """Public landing page ('/'). No auth required. Just renders the template."""
    return render(request, "patient/index.html")


def about(request):
    """Public "About us" page. No auth required."""
    return render(request, "patient/about.html")


def services(request):
    """Public "Services" page. No auth required."""
    return render(request, "patient/services.html")


def department(request):
    """Public "Departments" page. No auth required."""
    return render(request, "patient/departments.html")


def doctors(request):
    """
    Public "Meet our doctors" listing page. No auth required. Fetches every
    Doctor row (with its User joined in) and assigns each one a stock
    photo path (cycling through 8 placeholder images by index) since the
    project doesn't have real doctor photos.
    """
    doctor_list = list(Doctor.objects.select_related('user').all())
    for index, doc in enumerate(doctor_list):
        doc.photo_path = f'public/images/doctor-{(index % 8) + 1}.jpg'
    return render(request, "patient/doctors.html", {'doctors': doctor_list})


def contact(request):
    """
    Public "Contact us" page. No auth required. On GET, shows the form; on
    POST, saves the submitted fields as a new ContactMessage row (no email
    is sent, it's just stored for staff to review) and redirects back to
    the same page with a success message.
    """
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')

        if not all([full_name, email, phone, subject, message_body]):
            messages.error(request, 'Please fill in all fields.')
            return redirect('contact')

        ContactMessage.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            subject=subject,
            message=message_body,
        )
        messages.success(request, 'Your message has been received.')
        return redirect('contact')

    return render(request, 'patient/contact.html')


# ================================================================
# Auth
# ================================================================

def login(request):
    """
    Shared login page/handler for ALL roles (admin, doctor, receptionist,
    patient) -- there's no separate login view per role. On GET, just
    shows the login form.

    On POST:
      - Authenticates by email + password (``username`` is the email here
        since the User model uses email-based auth).
      - If the form's selected role doesn't match the account's actual
        ``role``, rejects with an error (prevents a patient from logging
        in via the "doctor" tab, etc).
      - If the account is currently OTP-locked (too many wrong codes
        earlier), blocks the login and shows minutes remaining.
      - If OTP login is disabled system-wide
        (``SystemSettings.get_solo().otp_login_enabled`` is False), logs
        the user in immediately and redirects to their role dashboard.
      - Otherwise, this is only step one: it emails a fresh OTP, stashes
        the user's id in ``request.session['pending_otp_user_id']``
        (Django's real ``auth_login()`` has NOT run yet), and redirects to
        ``verify_otp`` to complete the second step.
      - On bad credentials, shows a generic "Invalid email or password"
        error and redirects back to the login page.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        selected_role = request.POST.get('role')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if selected_role and user.role != selected_role:
                messages.error(request, f'This account is not registered as {selected_role.capitalize()}. Please select the correct role and try again.')
                return redirect('login')

            # Still inside a lockout window from too many wrong OTP
            # attempts on a previous login attempt -- block outright
            # rather than sending a fresh code.
            if user.otp_locked_until and timezone.now() < user.otp_locked_until:
                minutes_left = int((user.otp_locked_until - timezone.now()).total_seconds() // 60) + 1
                messages.error(request, f'Too many incorrect attempts. Please try again in {minutes_left} minute{"s" if minutes_left != 1 else ""}.')
                return redirect('login')

            # DB-driven feature toggle: when OTP is switched off, skip
            # straight to a real Django session login.
            if not SystemSettings.get_solo().otp_login_enabled:
                auth_login(request, user)
                return _redirect_for_role(request, user)

            # OTP is required: send the code and remember which user is
            # mid-login via the session, then hand off to verify_otp.
            _send_otp_email(user)
            request.session['pending_otp_user_id'] = user.id

            messages.success(request, f'A verification code has been sent to {user.email}.')
            return redirect('verify_otp')
        else:
            messages.error(request, 'Invalid email or password.')
            return redirect('login')

    return render(request, "patient/login.html")


def verify_otp(request):
    """
    Step two of login for every role: the OTP entry page. Reached only via
    ``request.session['pending_otp_user_id']`` set by ``login`` (or
    ``register``) -- if that key is missing (e.g. direct navigation, or
    session expired), bounces back to ``login``.

    On GET: shows the entry form along with how many seconds are left
    before the current code expires and how many wrong attempts remain.

    On POST:
      - Rejects if the stored code is missing/expired.
      - On a wrong code: increments ``otp_attempts``; once it reaches
        ``settings.OTP_MAX_ATTEMPTS`` the account is locked for
        ``settings.OTP_LOCKOUT_MINUTES`` (``otp_locked_until`` set,
        pending session key dropped, user sent back to ``login``).
        Otherwise just reports how many attempts remain.
      - On a correct code: clears the OTP fields, drops the pending
        session key, performs the real ``auth_login()``, and redirects to
        the user's role dashboard via ``_redirect_for_role``.
    """
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.error(request, 'Please login again.')
        return redirect('login')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        entered_code = request.POST.get('otp_code', '').strip()
        # Expiry = the moment the code was generated, plus the configured
        # validity window. `expiry` is None if no code was ever generated.
        expiry = user.otp_created_at + timedelta(minutes=settings.OTP_VALID_MINUTES) if user.otp_created_at else None

        if not user.otp_code or not expiry or timezone.now() > expiry:
            messages.error(request, 'This code has expired. Please request a new one.')
            return redirect('verify_otp')

        if entered_code != user.otp_code:
            user.otp_attempts += 1

            # Hit the max wrong-attempt limit: wipe the OTP state, start a
            # timed lockout (`otp_locked_until`), and force the user all
            # the way back to the login page instead of letting them keep
            # guessing on this same page.
            if user.otp_attempts >= settings.OTP_MAX_ATTEMPTS:
                user.otp_code = None
                user.otp_created_at = None
                user.otp_attempts = 0
                user.otp_locked_until = timezone.now() + timedelta(minutes=settings.OTP_LOCKOUT_MINUTES)
                user.save(update_fields=['otp_code', 'otp_created_at', 'otp_attempts', 'otp_locked_until'])
                del request.session['pending_otp_user_id']
                messages.error(request, f'Too many incorrect attempts. Your account is locked for {settings.OTP_LOCKOUT_MINUTES} minutes.')
                return redirect('login')

            # Still under the limit: save the incremented attempt count
            # and let the user try again on this same page.
            user.save(update_fields=['otp_attempts'])
            remaining = settings.OTP_MAX_ATTEMPTS - user.otp_attempts
            messages.error(request, f'Incorrect verification code. {remaining} attempt{"s" if remaining != 1 else ""} remaining.')
            return redirect('verify_otp')

        # Correct code: clear OTP state so it can't be reused, drop the
        # pending-login marker, and finally perform the real session login.
        user.otp_code = None
        user.otp_created_at = None
        user.otp_attempts = 0
        user.save(update_fields=['otp_code', 'otp_created_at', 'otp_attempts'])
        del request.session['pending_otp_user_id']

        auth_login(request, user)
        return _redirect_for_role(request, user)

    # GET: compute how many seconds are left until the current code
    # expires, so the template can show a live countdown (never negative).
    seconds_remaining = 0
    if user.otp_created_at:
        expiry = user.otp_created_at + timedelta(minutes=settings.OTP_VALID_MINUTES)
        seconds_remaining = max(0, int((expiry - timezone.now()).total_seconds()))

    return render(request, 'patient/verify_otp.html', {
        'email': user.email,
        'otp_valid_minutes': settings.OTP_VALID_MINUTES,
        'seconds_remaining': seconds_remaining,
        'resend_cooldown_seconds': 30,
        'attempts_remaining': max(0, settings.OTP_MAX_ATTEMPTS - user.otp_attempts),
        'otp_lockout_minutes': settings.OTP_LOCKOUT_MINUTES,
    })


def resend_otp(request):
    """
    Regenerates and re-emails the OTP for the user currently mid-login
    (identified via ``request.session['pending_otp_user_id']``). If that
    session key is missing, sends the user back to ``login`` instead.
    Always redirects back to ``verify_otp`` on success.
    """
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        messages.error(request, 'Please login again.')
        return redirect('login')

    user = get_object_or_404(User, id=user_id)
    _send_otp_email(user)
    messages.success(request, f'A new verification code has been sent to {user.email}.')
    return redirect('verify_otp')


def register(request):
    """
    Public self-registration page for new PATIENTS only (other roles are
    presumably created by an admin elsewhere). On GET, shows the sign-up
    form.

    On POST:
      - Validates the two password fields match and the email isn't
        already registered.
      - Splits the submitted full name into first/last name.
      - Creates the ``User`` (with ``role='patient'``) and its matching
        ``Patient`` profile row.
      - If OTP login is disabled system-wide, logs the new user in right
        away and redirects to their dashboard.
      - Otherwise sends an OTP and stashes
        ``request.session['pending_otp_user_id']`` just like ``login``
        does, redirecting to ``verify_otp`` to finish signing in.
    """
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        dob = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not all([full_name, email, phone, gender, password, confirm_password]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('register')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('register')

        # Split "First Last Extra" into first_name="First",
        # last_name="Last Extra" (everything after the first space).
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        try:
            validate_password(password, User(email=email, first_name=first_name, last_name=last_name))
        except ValidationError as exc:
            for error_message in exc.messages:
                messages.error(request, error_message)
            return redirect('register')

        # username is set to the email since this project authenticates
        # by email rather than a separate username.
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

        if not SystemSettings.get_solo().otp_login_enabled:
            auth_login(request, user)
            messages.success(request, 'Account created successfully.')
            return _redirect_for_role(request, user)

        _send_otp_email(user)
        request.session['pending_otp_user_id'] = user.id

        messages.success(request, f'Account created. A verification code has been sent to {user.email}.')
        return redirect('verify_otp')

    return render(request, 'patient/register.html')


def forgot_password(request):
    """
    Public "forgot password" page. On GET, shows the request form.

    On POST: looks up an account by the submitted email and, if one exists,
    emails it a signed reset link via _send_password_reset_email(). Renders
    the same "check your email" success state regardless of whether a
    matching account was actually found, so this page can't be used to
    discover which email addresses are registered.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first() if email else None
        if user is not None:
            _send_password_reset_email(request, user)
        return render(request, 'patient/forgot_password.html', {'request_sent': True, 'sent_email': email})

    return render(request, 'patient/forgot_password.html')


def reset_password_confirm(request, uidb64, token):
    """
    Landing page for the link emailed by forgot_password. Validates the
    uid/token pair using the same primitives Django's own
    PasswordResetConfirmView relies on before allowing a new password to be
    set -- an invalid, expired, or already-used link (the token embeds a
    hash of the current password, so it stops matching the moment
    set_password() runs) instead shows an "expired" state with a link back
    to request a new one.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    token_valid = user is not None and default_token_generator.check_token(user, token)
    if not token_valid:
        return render(request, 'patient/reset_password_confirm.html', {'token_valid': False})

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not new_password or new_password != confirm_new_password:
            messages.error(request, 'Passwords do not match.')
        else:
            try:
                validate_password(new_password, user)
            except ValidationError as exc:
                for error_message in exc.messages:
                    messages.error(request, error_message)
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset. You can now log in.')
                return redirect('login')

    return render(request, 'patient/reset_password_confirm.html', {'token_valid': True})


def logout_view(request):
    """Logs the current user out of their Django session and sends them back to the login page. Any role can use this."""
    logout(request)
    return redirect('login')


# ================================================================
# Patient Profile
# ================================================================

@login_required
def patient_profile(request):
    """
    The logged-in patient's own profile page. Requires login (any role
    technically, but only patients have meaningful data here since it's
    keyed off ``request.user`` via ``Patient.objects.get_or_create``).

    On GET: renders the profile with counts of the patient's appointments
    and prescriptions and their "member since" year.

    On POST: updates both the ``User`` fields (name/email) and the
    ``Patient`` profile fields (contact info, medical details, optional
    new profile image) from the submitted form, saves both, and redirects
    back to this same page with a success message.
    """
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
            uploaded_image = request.FILES['profile_image']
            image_error = validate_uploaded_image(uploaded_image)
            if image_error:
                messages.error(request, image_error)
                return redirect('patient_profile')
            patient.profile_image = uploaded_image

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


@login_required
def change_password(request):
    """
    Lets the logged-in patient change their own account password, posted
    from the "Change Password" tab on patient_profile. Mirrors the pattern
    already used by doctor.views.change_password / receptionist.views.change_password
    (check the current password, compare the two new-password fields, then
    set_password + update_session_auth_hash so the change doesn't log the
    patient out of their current session) -- with one addition: this also
    runs the new password through Django's configured
    AUTH_PASSWORD_VALIDATORS, since this is new code with no reason to
    repeat the blank-password gap those older views still have.

    Always redirects back to patient_profile with the Change Password tab
    still open (via a #change-password hash that profile.js reads on load),
    since this form lives on that same page rather than a page of its own.
    """
    change_password_url = f"{reverse('patient_profile')}#change-password"

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect(change_password_url)

        if new_password != confirm_new_password:
            messages.error(request, 'New passwords do not match.')
            return redirect(change_password_url)

        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            for error_message in exc.messages:
                messages.error(request, error_message)
            return redirect(change_password_url)

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password updated successfully.')

    return redirect(change_password_url)


# ================================================================
# Appointments
# ================================================================

@login_required
def get_doctor_slots(request):
    """
    AJAX/JSON endpoint used by the booking form to fetch a doctor's
    available time slots for a chosen date (``?doctor=<id>&date=YYYY-MM-DD``).
    Requires login. Returns a 400 JSON error if the date can't be parsed,
    otherwise returns whatever ``Doctor.get_available_slots()`` computes
    (available flag + slot list, each slot marked booked/free).
    """
    doctor_id = request.GET.get('doctor')
    date_str = request.GET.get('date')

    doctor = get_object_or_404(Doctor, id=doctor_id)
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return JsonResponse({'available': False, 'reason': 'Invalid date.', 'slots': []}, status=400)

    return JsonResponse(doctor.get_available_slots(appointment_date))


@login_required
def book_appointment(request):
    """
    Step one of patient self-service booking (patient-only in practice,
    since it relies on ``Patient.objects.get(user=request.user)``).

    On GET: shows the booking form with the list of doctors to choose from.

    On POST: validates the chosen doctor, date, and time slot (must parse
    as a real date, and the slot must show up as free in
    ``doctor.get_available_slots()``). IMPORTANT: this view does NOT
    create the ``Appointment`` yet -- it only stashes the validated form
    data into ``request.session['pending_appointment']`` and redirects to
    ``confirm_appointment_billing``, which shows the "pay at the front
    desk" notice and is the view that actually creates the appointment
    and its bill once the patient confirms.
    """
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

        try:
            parsed_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.error(request, 'Please select a valid date.')
            return redirect('book_appointment')

        availability = doctor.get_available_slots(parsed_date)
        if not availability['available']:
            messages.error(request, availability['reason'] or 'Doctor is unavailable on this date.')
            return redirect('book_appointment')

        matching_slot = next((s for s in availability['slots'] if s['time'] == time_slot), None)
        if matching_slot is None or matching_slot['booked']:
            messages.error(request, 'This slot is already booked.')
            return redirect('book_appointment')

        # Nothing is saved to the database yet -- the chosen details are
        # only held in the session until the patient confirms on the
        # billing notice page (confirm_appointment_billing).
        request.session['pending_appointment'] = {
            'doctor_id': doctor.id,
            'department': department,
            'appointment_date': appointment_date,
            'time_slot': time_slot,
            'visit_type': visit_type,
            'reason': reason,
        }
        return redirect('confirm_appointment_billing')

    return render(request, 'patient/book_appointment.html', {'doctors': doctors})


@login_required
def confirm_appointment_billing(request):
    """
    Step two of patient self-service booking: a review-only page. Requires
    ``request.session['pending_appointment']`` to already be set by
    ``book_appointment``; if missing, bounces back there.

    Shows the doctor, date/time, visit type, reason, and consultation fee
    pulled from the pending session data. The "Proceed to Payment" button
    on this page links (GET, not a form) to ``card_payment``, which is
    where the appointment/bill are actually created.
    """
    pending = request.session.get('pending_appointment')
    if not pending:
        messages.error(request, 'Please choose a doctor, date, and time slot first.')
        return redirect('book_appointment')

    doctor = get_object_or_404(Doctor, id=pending['doctor_id'])
    parsed_date = datetime.strptime(pending['appointment_date'], '%Y-%m-%d').date()

    return render(request, 'patient/confirm_billing.html', {
        'doctor': doctor,
        'department': dict(Appointment.DEPARTMENT_CHOICES).get(pending['department'], pending['department']),
        'appointment_date': parsed_date,
        'time_slot': pending['time_slot'],
        'visit_type': dict(Appointment.VISIT_TYPE_CHOICES).get(pending['visit_type'], pending['visit_type']),
        'reason': pending['reason'],
        'consultation_fee': doctor.consultation_fee,
    })


@login_required
def card_payment(request):
    """
    Step three (final step) of patient self-service booking: a fake card
    checkout. There's no real payment gateway integrated -- this page just
    collects card-shaped fields for demo purposes and never validates or
    stores them. Submitting it is treated as an immediate successful
    payment.

    On GET: shows the card entry form plus the amount due, requiring
    ``request.session['pending_appointment']`` to already be set.

    On POST: re-checks the slot is still free (it may have been taken by
    someone else while the patient was on this page or the previous one)
    -- if not, discards the pending session data and sends them back to
    ``book_appointment``. If still free, this is the point where the real
    ``Appointment`` row is finally created, along with a ``Billing`` row
    already marked ``status='paid'`` (simulating the successful demo
    payment) and a ``Notification`` telling the patient their appointment
    is booked. Clears ``request.session['pending_appointment']`` and
    redirects to ``my_appointments``.
    """
    pending = request.session.get('pending_appointment')
    if not pending:
        messages.error(request, 'Please choose a doctor, date, and time slot first.')
        return redirect('book_appointment')

    doctor = get_object_or_404(Doctor, id=pending['doctor_id'])
    patient = Patient.objects.get(user=request.user)
    parsed_date = datetime.strptime(pending['appointment_date'], '%Y-%m-%d').date()

    if request.method == 'POST':
        # Re-validate availability in case the slot was booked by someone
        # else between the earlier steps and now.
        availability = doctor.get_available_slots(parsed_date)
        matching_slot = next((s for s in availability['slots'] if s['time'] == pending['time_slot']), None)
        if not availability['available'] or matching_slot is None or matching_slot['booked']:
            messages.error(request, 'Sorry, that slot was just taken. Please choose another.')
            del request.session['pending_appointment']
            return redirect('book_appointment')

        # This is the actual creation point for the appointment -- nothing
        # was written to the database during the earlier steps. The
        # availability recheck above closes most of the race window, but
        # two requests can still slip through it at almost the same instant
        # (e.g. a double-submitted click) -- caught here as a fallback
        # rather than surfacing a raw IntegrityError to the patient.
        try:
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                department=pending['department'],
                appointment_date=pending['appointment_date'],
                time_slot=pending['time_slot'],
                visit_type=pending['visit_type'],
                reason=pending['reason'],
            )
        except IntegrityError:
            messages.error(request, 'Sorry, that slot was just taken. Please choose another.')
            del request.session['pending_appointment']
            return redirect('book_appointment')

        # No real gateway is charged -- the "payment" is simulated, so the
        # bill is created already paid rather than left pending.
        Billing.objects.create(
            appointment=appointment,
            patient=patient,
            bill_type='consultation',
            amount=doctor.consultation_fee,
            status='paid',
            paid_at=timezone.now(),
        )

        Notification.objects.create(
            user=request.user,
            notification_type='general',
            message=f'Your appointment with Dr. {doctor.user.get_full_name()} has been booked and paid.'
        )
        send_appointment_booked_email(appointment)

        del request.session['pending_appointment']
        messages.success(request, 'Payment successful. Your appointment is booked!')
        return redirect('my_appointments')

    return render(request, 'patient/card_payment.html', {
        'doctor': doctor,
        'department': dict(Appointment.DEPARTMENT_CHOICES).get(pending['department'], pending['department']),
        'appointment_date': parsed_date,
        'time_slot': pending['time_slot'],
        'consultation_fee': doctor.consultation_fee,
    })


@login_required
def cancel_pending_appointment(request):
    """
    Lets the patient back out of the pending-appointment flow: discards
    ``request.session['pending_appointment']`` (if any) without creating
    anything, then redirects to ``book_appointment`` to start over.
    """
    request.session.pop('pending_appointment', None)
    return redirect('book_appointment')


@login_required
def my_appointments(request):
    """
    Lists the logged-in patient's own appointments (most recent date
    first), each with its doctor's info preloaded. Patient-only in
    practice (looks up ``Patient`` by ``request.user``).
    """
    patient = Patient.objects.get(user=request.user)
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor__user').order_by('-appointment_date')
    return render(request, 'patient/my_appointments.html', {'appointments': appointments})


@login_required
def my_billing(request):
    """
    Read-only view of the logged-in patient's own bills, newest first,
    plus a running total of everything still marked 'pending'. Patient-only
    in practice. No POST handling here -- payment is settled at the front
    desk, not through this page.
    """
    patient = Patient.objects.get(user=request.user)
    bills = Billing.objects.filter(patient=patient).select_related('appointment__doctor__user').order_by('-created_at')
    return render(request, 'patient/my_billing.html', {
        'bills': bills,
        'pending_total': sum(b.amount for b in bills if b.status == 'pending'),
    })


@login_required
def billing_receipt(request, bill_id):
    """
    Printable receipt for one of the logged-in patient's own bills.

    Scoped to `patient=patient` in the lookup (404 if the bill doesn't
    belong to them) so a patient can't view someone else's receipt by
    guessing an id in the URL. Renders `patient/billing_receipt.html`, a
    print-friendly page (a "Print" button calling `window.print()` plus
    an `@media print` rule hiding the site header/footer) -- this
    project has no PDF library, so every "receipt"/"printout" here
    follows the same browser-print pattern already used by
    `doctor/patient_details.html`.
    """
    patient = Patient.objects.get(user=request.user)
    bill = get_object_or_404(Billing, id=bill_id, patient=patient)
    return render(request, 'patient/billing_receipt.html', {'bill': bill})


@login_required
def cancel_appointment(request, appointment_id):
    """
    Lets a patient cancel one of their own appointments. The
    ``patient__user=request.user`` filter in the lookup doubles as an
    ownership check -- a 404 is raised if the appointment doesn't belong
    to the logged-in user, instead of leaking whether the id exists.
    Only acts on POST (sets status to 'cancelled' and creates a
    'cancelled'-type Notification); either way redirects to
    ``my_appointments``.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__user=request.user)

    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()

        Notification.objects.create(
            user=request.user,
            notification_type='cancelled',
            message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} was cancelled.'
        )
        send_appointment_cancelled_email(appointment)

    return redirect('my_appointments')


# ================================================================
# Notifications
# ================================================================

@login_required
def notifications_view(request):
    """Lists all notifications belonging to the logged-in user (any role, since Notification links to User directly)."""
    notes = Notification.objects.filter(user=request.user)
    return render(request, 'patient/notifications.html', {'notifications': notes})


@login_required
def mark_all_read(request):
    """Bulk-marks every unread notification for the logged-in user as read, then redirects back to the notifications list."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')


@login_required
def dismiss_notification(request, notification_id):
    """
    Deletes a single notification belonging to the logged-in user. The
    ``user=request.user`` filter ensures a user can't dismiss someone
    else's notification by guessing an id. Redirects back to the
    notifications list either way.
    """
    Notification.objects.filter(id=notification_id, user=request.user).delete()
    return redirect('notifications')