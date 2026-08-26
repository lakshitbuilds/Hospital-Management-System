from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from patient.models import Appointment
from patient.emails import send_appointment_reminder_email


class Command(BaseCommand):
    help = (
        "Emails a reminder to every patient whose appointment (status "
        "'pending' or 'confirmed') falls tomorrow and hasn't already been "
        "reminded. Meant to be run once a day via a scheduled task -- see "
        "DATABASE.md/README for how this project sets that up."
    )

    def handle(self, *args, **options):
        tomorrow = (timezone.now() + timedelta(days=1)).date()
        appointments = Appointment.objects.filter(
            appointment_date=tomorrow,
            status__in=['pending', 'confirmed'],
            reminder_sent=False,
        ).select_related('patient__user', 'doctor__user')

        sent = 0
        for appointment in appointments:
            send_appointment_reminder_email(appointment)
            appointment.reminder_sent = True
            appointment.save(update_fields=['reminder_sent'])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder email(s) for {tomorrow}.'))
