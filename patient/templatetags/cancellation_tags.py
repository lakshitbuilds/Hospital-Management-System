from django import template
from patient.models import Appointment

register = template.Library()


@register.simple_tag
def cancellation_reasons():
    return Appointment.CANCELLATION_REASONS
