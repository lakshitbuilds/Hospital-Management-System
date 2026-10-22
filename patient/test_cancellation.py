from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse

from doctor.models import Doctor
from .models import Appointment, Notification, Patient


class CancellationReasonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.users = {role: User.objects.create_user(username=role, email=f'{role}@example.com', role=role)
                     for role in ['patient', 'doctor', 'receptionist', 'admin']}
        cls.patient = Patient.objects.create(user=cls.users['patient'])
        cls.doctor = Doctor.objects.create(user=cls.users['doctor'], department='general')
        cls.other_patient_user = User.objects.create_user(username='other_patient', email='other_patient@example.com', role='patient')
        Patient.objects.create(user=cls.other_patient_user)
        cls.other_doctor_user = User.objects.create_user(username='other_doctor', email='other_doctor@example.com', role='doctor')
        Doctor.objects.create(user=cls.other_doctor_user, department='general')

    def setUp(self):
        self.appointment = Appointment.objects.create(patient=self.patient, doctor=self.doctor,
            appointment_date=date(2026, 10, 22), time_slot='10:00 AM', reason='Checkup', status='confirmed')

    routes = {'patient': 'cancel_appointment', 'doctor': 'doctor_cancel_appointment',
              'receptionist': 'receptionist_cancel_appointment', 'admin': 'admin_update_appointment_status'}

    def post(self, role, reason, explanation=""):
        self.client.force_login(self.users[role])
        return self.client.post(reverse(self.routes[role], args=[self.appointment.pk]),
            {'cancellation_reason': reason, 'cancellation_explanation': explanation, 'status': 'cancelled'}, HTTP_ACCEPT='application/json')

    def test_empty_and_whitespace_reasons_rejected_in_every_portal(self):
        for role in self.routes:
            for reason in ['', '   \t\n  ']:
                with self.subTest(role=role, reason=reason):
                    response = self.post(role, reason)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('reason', response.json()['error'])
                    self.appointment.refresh_from_db()
                    self.assertEqual(self.appointment.status, 'confirmed')
                    self.assertEqual(self.appointment.cancellation_reason, '')
        self.assertFalse(Notification.objects.exists())

    def test_valid_reason_saved_and_repeat_cancel_rejected(self):
        for role in self.routes:
            with self.subTest(role=role):
                self.appointment.status = 'confirmed'
                self.appointment.cancellation_reason = ''
                self.appointment.save()
                before = Notification.objects.count()
                response = self.post(role, '  Patient is unavailable  ')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['success'])
                self.appointment.refresh_from_db()
                self.assertEqual(self.appointment.status, 'cancelled')
                self.assertEqual(self.appointment.cancellation_reason, 'Patient is unavailable')
                self.assertEqual(Notification.objects.count(), before + 1)
                self.assertEqual(self.post(role, 'Doctor is unavailable').status_code, 409)
                self.appointment.refresh_from_db()
                self.assertEqual(self.appointment.cancellation_reason, 'Patient is unavailable')
                self.assertEqual(Notification.objects.count(), before + 1)

    def test_completed_and_no_show_cannot_be_cancelled(self):
        for status in ['completed', 'no_show']:
            self.appointment.status = status
            self.appointment.save()
            for role in self.routes:
                self.assertEqual(self.post(role, 'Doctor is unavailable').status_code, 409)
            self.appointment.refresh_from_db()
            self.assertEqual(self.appointment.status, status)

    def test_ownership_and_role_checks(self):
        for user, route in [(self.other_patient_user, 'cancel_appointment'), (self.other_doctor_user, 'doctor_cancel_appointment')]:
            self.client.force_login(user)
            self.assertEqual(self.client.post(reverse(route, args=[self.appointment.pk]),
                {'cancellation_reason': 'Not mine'}).status_code, 404)
        self.client.force_login(self.users['patient'])
        self.assertEqual(self.client.post(reverse('receptionist_cancel_appointment', args=[self.appointment.pk]),
            {'cancellation_reason': 'Wrong role'}).status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')

    def test_get_never_cancels(self):
        for role in ['patient', 'doctor', 'receptionist']:
            self.client.force_login(self.users[role])
            self.assertEqual(self.client.get(reverse(self.routes[role], args=[self.appointment.pk])).status_code, 405)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')

    def test_database_failure_rolls_back_status_and_reason(self):
        with self.assertLogs('patient.cancellation', level='ERROR'), patch('patient.cancellation.Notification.objects.create', side_effect=OperationalError('temporary error')):
            response = self.post('patient', 'Other', 'Keep my reason')
        self.assertEqual(response.status_code, 503)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')
        self.assertEqual(self.appointment.cancellation_reason, '')
        self.assertFalse(Notification.objects.exists())

    def test_non_ajax_failure_preserves_reason_and_escapes_markup(self):
        self.appointment.status = 'completed'
        self.appointment.save()
        self.client.force_login(self.users['patient'])
        response = self.client.post(reverse('cancel_appointment', args=[self.appointment.pk]), {'cancellation_reason': 'Other', 'cancellation_explanation': '<script>keep me</script>'})
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, '&lt;script&gt;keep me&lt;/script&gt;', status_code=409)

    def test_reason_visible_in_patient_history_and_staff_lists(self):
        self.post('patient', 'Other', 'Family emergency')
        for role, route in [('patient', 'my_appointments'), ('doctor', 'appointment_list'), ('admin', 'admin_appointment_list')]:
            self.client.force_login(self.users[role])
            self.assertContains(self.client.get(reverse(route)), 'Family emergency')

    def test_email_runs_only_after_successful_commit(self):
        with patch('patient.cancellation.send_appointment_cancelled_email') as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.post('patient', 'Other', 'Family emergency')
            send.assert_called_once()

    def test_every_choice_persists_in_every_portal(self):
        for role in self.routes:
            for reason in Appointment.CANCELLATION_REASONS:
                with self.subTest(role=role, reason=reason):
                    self.appointment.status = 'confirmed'
                    self.appointment.cancellation_reason = ''
                    self.appointment.cancellation_explanation = ''
                    self.appointment.save()
                    response = self.post(role, reason, '  A specific explanation  ')
                    self.assertEqual(response.status_code, 200)
                    self.appointment.refresh_from_db()
                    self.assertEqual(self.appointment.cancellation_reason, reason)
                    self.assertEqual(self.appointment.cancellation_explanation,
                                     'A specific explanation' if reason == 'Other' else '')
                    self.assertEqual(self.appointment.status, 'cancelled')

    def test_other_requires_nonblank_explanation(self):
        for role in self.routes:
            for explanation in ['', '  \t\n ']:
                response = self.post(role, 'Other', explanation)
                self.assertEqual(response.status_code, 400)
                self.assertIn('Other', response.json()['error'])
                self.appointment.refresh_from_db()
                self.assertEqual(self.appointment.status, 'confirmed')
                self.assertEqual(self.appointment.cancellation_explanation, '')

    def test_unknown_and_multiple_choices_are_rejected(self):
        self.assertEqual(self.post('patient', 'Invented reason').status_code, 400)
        response = self.client.post(reverse('cancel_appointment', args=[self.appointment.pk]), {
            'cancellation_reason': ['Patient is unavailable', 'Doctor is unavailable'],
        }, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 400)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')

    def test_modal_choices_and_other_explanation_in_history(self):
        self.client.force_login(self.users['patient'])
        response = self.client.get(reverse('my_appointments'))
        for reason in Appointment.CANCELLATION_REASONS:
            self.assertContains(response, f'value="{reason}"')
        self.assertContains(response, 'data-cancellation-other hidden')
        self.post('patient', 'Other', 'A family commitment')
        self.assertContains(self.client.get(reverse('my_appointments')), 'Other - A family commitment')
