"""Shared cancellation processing; callers supply an authorized queryset."""
import logging

from django.contrib import messages
from django.db import DatabaseError, transaction
from django.utils import timezone
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render

from .emails import send_appointment_cancelled_email
from .models import Appointment, Notification
from safe_redirect import safe_next_redirect

logger = logging.getLogger(__name__)


def cancel_with_reason(request, appointments, appointment_id, *, portal, fallback, actor=None):
    appointment = get_object_or_404(appointments.select_related('patient__user', 'doctor__user'), pk=appointment_id)
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    raw_reason = request.POST.get('cancellation_reason', '')
    reason = raw_reason.strip()
    raw_explanation = request.POST.get('cancellation_explanation', '')
    explanation = raw_explanation.strip() if reason == 'Other' else ''
    ajax = 'application/json' in request.headers.get('Accept', '')

    def failure(message, status):
        if ajax:
            return JsonResponse({'success': False, 'error': message}, status=status)
        return render(request, 'includes/cancellation_error.html', {
            'portal_base': f'{portal}/base.html', 'appointment': appointment,
            'cancellation_reason': reason, 'cancellation_explanation': raw_explanation if reason == 'Other' else '', 'cancellation_error': message,
            'back_url': safe_next_redirect(request, fallback).url,
        }, status=status)

    if len(request.POST.getlist('cancellation_reason')) != 1 or reason not in Appointment.CANCELLATION_REASONS:
        return failure('Please select a valid cancellation reason.', 400)
    if reason == 'Other' and not explanation:
        return failure('Please specify the cancellation reason when selecting Other.', 400)
    try:
        with transaction.atomic():
            # A conditional update prevents double cancellation and also works
            # on SQLite, where select_for_update does not lock individual rows.
            changed = appointments.filter(pk=appointment.pk, status__in=['pending', 'confirmed']).update(
                status='cancelled', cancellation_reason=reason, cancellation_explanation=explanation, updated_at=timezone.now(),
            )
            if not changed:
                return failure('Only pending or confirmed appointments can be cancelled. This appointment is no longer active.', 409)
            appointment.status = 'cancelled'
            appointment.cancellation_reason = reason
            appointment.cancellation_explanation = explanation
            suffix = f' by {actor}' if actor else ''
            Notification.objects.create(
                user=appointment.patient.user, notification_type='cancelled',
                message=f'Your appointment with Dr. {appointment.doctor.user.get_full_name()} on {appointment.appointment_date} was cancelled{suffix}.',
            )
            transaction.on_commit(lambda: send_appointment_cancelled_email(appointment, cancelled_by=actor), robust=True)
    except DatabaseError:
        logger.exception('Unable to cancel appointment %s', appointment.pk)
        return failure('The cancellation could not be saved. Please try again. Your reason has been kept.', 503)
    messages.success(request, 'Appointment cancelled successfully.')
    if ajax:
        return JsonResponse({'success': True})
    return safe_next_redirect(request, fallback)
