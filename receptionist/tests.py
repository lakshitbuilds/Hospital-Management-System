from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from doctor.models import Doctor
from patient.models import Appointment, Notification, Patient


class ReceptionistAppointmentActionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.receptionist = User.objects.create_user(
            username='frontdesk', email='frontdesk@example.com',
            password='TestPass123!', role='receptionist',
        )
        patient_user = User.objects.create_user(
            username='patient1', email='patient1@example.com',
            password='TestPass123!', role='patient',
        )
        doctor_user = User.objects.create_user(
            username='doctor1', email='doctor1@example.com',
            password='TestPass123!', role='doctor',
        )
        self.patient = Patient.objects.create(user=patient_user)
        self.doctor = Doctor.objects.create(user=doctor_user, department='general')
        self.appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, appointment_date=date.today(),
            time_slot='10:00 AM', reason='Checkup',
        )
        self.client.force_login(self.receptionist)

    def url(self, action):
        return reverse('receptionist_' + action + '_appointment', args=[self.appointment.id])

    def test_confirm_pending_appointment(self):
        response = self.client.post(self.url('confirm'))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')
        self.assertTrue(Notification.objects.filter(
            user=self.patient.user, notification_type='confirmed',
        ).exists())

    @patch('receptionist.views.send_appointment_cancelled_email', side_effect=RuntimeError('SMTP down'))
    def test_cancel_still_succeeds_when_email_fails(self, send_email):
        response = self.client.post(self.url('cancel'))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')
        self.assertTrue(Notification.objects.filter(
            user=self.patient.user, notification_type='cancelled',
        ).exists())

    def test_terminal_appointment_cannot_be_reconfirmed(self):
        self.appointment.status = 'cancelled'
        self.appointment.save()
        response = self.client.post(self.url('confirm'))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')

    def test_terminal_appointment_cannot_be_cancelled(self):
        self.appointment.status = 'completed'
        self.appointment.save()
        response = self.client.post(self.url('cancel'))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'completed')

    def test_get_does_not_change_status(self):
        self.client.get(self.url('confirm'))
        self.client.get(self.url('cancel'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')

    def test_patient_cannot_perform_staff_actions(self):
        self.client.force_login(self.patient.user)
        self.client.post(self.url('confirm'))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')
