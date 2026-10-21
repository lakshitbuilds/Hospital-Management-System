"""Add a repeatable set of fictional patients and scheduled appointments."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from doctor.models import Doctor
from patient.models import Appointment, Billing, Patient


NAMES = [
    ('Aarav', 'Shah'), ('Diya', 'Patel'), ('Vivaan', 'Joshi'),
    ('Ananya', 'Desai'), ('Aditya', 'Singh'), ('Isha', 'Mehta'),
    ('Sai', 'Nair'), ('Avni', 'Reddy'), ('Arnav', 'Gupta'),
    ('Kiara', 'Bose'), ('Reyansh', 'Sethi'), ('Myra', 'Rao'),
    ('Ayaan', 'Kapoor'), ('Sara', 'Menon'), ('Krish', 'Bhat'),
    ('Tara', 'Sharma'), ('Dhruv', 'Trivedi'), ('Riya', 'Verma'),
    ('Kabir', 'Saxena'), ('Aditi', 'Kulkarni'), ('Ishaan', 'Das'),
    ('Nisha', 'Iyer'), ('Vihaan', 'Chopra'), ('Meera', 'Sinha'),
    ('Dev', 'Malik'),
]


class Command(BaseCommand):
    help = 'Create 25 fictional demo patients with appointments across all doctors.'

    @transaction.atomic
    def handle(self, *args, **options):
        doctors = list(Doctor.objects.select_related('user').order_by('pk'))
        if not doctors:
            raise CommandError('Add at least one doctor before seeding patients.')
        if len(doctors) > len(NAMES):
            raise CommandError('There are more doctors than the 25 available demo patients.')
        User = get_user_model()
        today = timezone.localdate()
        created_patients = created_appointments = created_bills = 0

        for index, (first, last) in enumerate(NAMES):
            number = index + 1
            email = f'hms.demo.patient{number:02d}@example.invalid'
            username = f'hms_demo_patient_{number:02d}'
            user = User.objects.filter(email=email).first()
            if user and (user.username != username or user.role != 'patient'):
                raise CommandError(f'Demo account collision for {email}.')
            if not user:
                if User.objects.filter(username=username).exists():
                    raise CommandError(f'Demo username already in use: {username}.')
                user = User(username=username, email=email, first_name=first,
                            last_name=last, role='patient')
                user.set_unusable_password()
                user.save()
            patient, created = Patient.objects.get_or_create(
                user=user,
                defaults={
                    'address': 'Fictional demo address', 'city': 'Demo City',
                    'country': 'India',
                    'medical_history': 'Synthetic demo record; not a real patient.',
                },
            )
            created_patients += created
            # Keep the initial assignment stable when this command is rerun.
            reason = f'Synthetic demo appointment HMS-DEMO-{number:02d}'
            appointment = Appointment.objects.filter(patient=patient, reason=reason).first()
            if not appointment:
                doctor = doctors[index % len(doctors)]
                chosen = None
                for offset in range(31):
                    day = today + timedelta(days=offset)
                    available = doctor.get_available_slots(day)
                    free = next((s for s in available['slots'] if not s['booked']), None)
                    if available['available'] and free:
                        chosen = day, free['time']
                        break
                if not chosen:
                    raise CommandError(f'No free slot in the next 31 days for doctor {doctor.pk}.')
                appointment = Appointment.objects.create(
                    patient=patient, doctor=doctor, appointment_date=chosen[0],
                    time_slot=chosen[1], department=doctor.department,
                    status='pending' if number % 3 == 0 else 'confirmed',
                    visit_type='new', reason=reason,
                    # Demo appointments should not enter the reminder email queue.
                    reminder_sent=True,
                )
                created_appointments += 1
            _, created = Billing.objects.get_or_create(
                appointment=appointment, patient=patient, bill_type='consultation',
                defaults={'amount': appointment.doctor.consultation_fee, 'status': 'pending'},
            )
            created_bills += created

        self.stdout.write(self.style.SUCCESS(
            f'Created {created_patients} demo patients, {created_appointments} appointments '
            f'and {created_bills} consultation bills across {len(doctors)} doctors. '
            'Existing records preserved. Demo accounts have no login password.'
        ))
