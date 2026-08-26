"""
Shared appointment-related email senders. Used by patient/doctor/receptionist
views (wherever an appointment is booked or cancelled) and by the
send_appointment_reminders management command. Mirrors the branded
HTML + plain-text pattern _send_otp_email (views.py) already uses.

Sends fail_silently=True, unlike the OTP email: by the time any of these
are called the appointment/bill/cancellation has already been committed to
the database, so a transient SMTP failure shouldn't turn into a 500 for the
patient on top of it.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone


def _appointment_context(appointment):
    return {
        'first_name': appointment.patient.user.first_name,
        'doctor_name': appointment.doctor.user.get_full_name(),
        'department': appointment.get_department_display(),
        'appointment_date': appointment.appointment_date,
        'time_slot': appointment.time_slot,
        'visit_type': appointment.get_visit_type_display(),
        'current_year': timezone.now().year,
    }


def send_appointment_booked_email(appointment):
    """Notify the patient that an appointment of theirs was just booked (self-service or staff-assisted)."""
    context = _appointment_context(appointment)
    text_body = (
        f"Hi {context['first_name'] or 'there'}, your appointment with Dr. {context['doctor_name']} "
        f"({context['department']}) on {appointment.appointment_date} at {appointment.time_slot} is booked."
    )
    email = EmailMultiAlternatives(
        subject='Your MediCare Hospital appointment is booked',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[appointment.patient.user.email],
    )
    email.attach_alternative(render_to_string('patient/emails/appointment_booked_email.html', context), 'text/html')
    email.send(fail_silently=True)


def send_appointment_cancelled_email(appointment, cancelled_by=None):
    """
    Notify the patient that an appointment of theirs was cancelled.
    ``cancelled_by`` is an optional human-readable actor ('the front desk',
    'the doctor') to mirror the wording already used in this project's
    cancellation Notification messages; left as None for a patient's own
    self-cancellation.
    """
    context = _appointment_context(appointment)
    context['cancelled_by'] = cancelled_by
    who = f' by {cancelled_by}' if cancelled_by else ''
    text_body = (
        f"Hi {context['first_name'] or 'there'}, your appointment with Dr. {context['doctor_name']} "
        f"on {appointment.appointment_date} at {appointment.time_slot} was cancelled{who}."
    )
    email = EmailMultiAlternatives(
        subject='Your MediCare Hospital appointment was cancelled',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[appointment.patient.user.email],
    )
    email.attach_alternative(render_to_string('patient/emails/appointment_cancelled_email.html', context), 'text/html')
    email.send(fail_silently=True)


def send_appointment_reminder_email(appointment):
    """Remind the patient they have an appointment tomorrow. Called by send_appointment_reminders."""
    context = _appointment_context(appointment)
    text_body = (
        f"Hi {context['first_name'] or 'there'}, this is a reminder that you have an appointment with "
        f"Dr. {context['doctor_name']} tomorrow ({appointment.appointment_date}) at {appointment.time_slot}."
    )
    email = EmailMultiAlternatives(
        subject='Reminder: your MediCare Hospital appointment is tomorrow',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[appointment.patient.user.email],
    )
    email.attach_alternative(render_to_string('patient/emails/appointment_reminder_email.html', context), 'text/html')
    email.send(fail_silently=True)
