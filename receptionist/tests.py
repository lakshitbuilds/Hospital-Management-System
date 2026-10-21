from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from doctor.models import Doctor
from patient.models import Appointment, Billing, Notification, Patient
from receptionist.models import Receptionist
from safe_redirect import safe_next_redirect


class RedirectTests(SimpleTestCase):
    def test_named_routes_and_safe_urls(self):
        targets = {
            'receptionist_appointment_list': '/receptionist/appointments/',
            'receptionist_today_appointments': '/receptionist/appointments/today/',
            'appointment_list': '/doctor/appointments/',
            'today_appointments': '/doctor/appointments/today/',
            'receptionist_billing_list': '/receptionist/billing/',
            'admin_billing_list': reverse('admin_billing_list'),
            '/receptionist/appointments/?status=pending&page=2':
                '/receptionist/appointments/?status=pending&page=2',
        }
        for target, expected in targets.items():
            with self.subTest(target=target):
                request = RequestFactory().post('/', {'next': target})
                self.assertEqual(safe_next_redirect(request, 'home').url, expected)

    def test_invalid_and_external_targets_fall_back(self):
        for target in ('', 'unknown_route', 'relative/path', 'https://evil.example/',
                       '//evil.example/', '/\\evil.example/', 'javascript:alert(1)'):
            with self.subTest(target=target):
                request = RequestFactory().post('/', {'next': target})
                self.assertEqual(safe_next_redirect(request, 'home').url, reverse('home'))

    def test_https_does_not_redirect_to_http(self):
        request = RequestFactory().post('/', {'next': 'http://testserver/'}, secure=True)
        self.assertEqual(safe_next_redirect(request, 'home').url, reverse('home'))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PortalWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.users = {}
        for role in ('patient', 'doctor', 'receptionist', 'admin'):
            cls.users[role] = User.objects.create_user(
                username=role, email=f'{role}@example.com', password='TestPass123!', role=role)
        cls.patient = Patient.objects.create(user=cls.users['patient'])
        cls.doctor = Doctor.objects.create(user=cls.users['doctor'], department='general', consultation_fee=500)
        Receptionist.objects.create(user=cls.users['receptionist'])

    def setUp(self):
        self.appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, appointment_date=date.today(),
            time_slot='09:00 AM', reason='Checkup')
        self.bill = Billing.objects.create(
            appointment=self.appointment, patient=self.patient, amount=500)
        self.client.force_login(self.users['receptionist'])

    def test_receptionist_accept_from_both_lists(self):
        for target in ('receptionist_appointment_list', 'receptionist_today_appointments'):
            with self.subTest(target=target):
                self.appointment.status = 'pending'
                self.appointment.save()
                response = self.client.post(reverse('receptionist_confirm_appointment',
                    args=[self.appointment.pk]), {'next': target}, follow=True)
                self.assertEqual(response.redirect_chain, [(reverse(target), 302)])
                self.assertEqual(response.status_code, 200)
                self.appointment.refresh_from_db()
                self.assertEqual(self.appointment.status, 'confirmed')
        self.assertEqual(Notification.objects.filter(user=self.users['patient'],
            notification_type='confirmed').count(), 2)

    def test_receptionist_cancel_no_show_and_payment(self):
        for action, status in (('receptionist_cancel_appointment', 'cancelled'),
                               ('receptionist_mark_no_show', 'no_show')):
            with self.subTest(action=action):
                self.appointment.status = 'confirmed'
                self.appointment.save()
                response = self.client.post(reverse(action, args=[self.appointment.pk]),
                    {'next': 'receptionist_today_appointments'}, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.redirect_chain[0][0], reverse('receptionist_today_appointments'))
                self.appointment.refresh_from_db()
                self.assertEqual(self.appointment.status, status)
        self.assertEqual(self.appointment.bills.filter(bill_type='no_show_fee').count(), 1)
        self.client.post(reverse('receptionist_mark_no_show', args=[self.appointment.pk]))
        self.assertEqual(self.appointment.bills.filter(bill_type='no_show_fee').count(), 1)
        response = self.client.post(reverse('receptionist_mark_bill_paid', args=[self.bill.pk]),
            {'next': 'receptionist_billing_list'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0][0], reverse('receptionist_billing_list'))
        self.bill.refresh_from_db()
        self.assertEqual(self.bill.status, 'paid')
        self.assertIsNotNone(self.bill.paid_at)

    def test_get_and_wrong_role_cannot_accept(self):
        url = reverse('receptionist_confirm_appointment', args=[self.appointment.pk])
        self.client.get(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')
        self.client.force_login(self.users['patient'])
        self.client.post(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')
        self.assertFalse(Notification.objects.exists())

    def test_doctor_completion_and_cancellation(self):
        self.client.force_login(self.users['doctor'])
        for action, target, status in (
            ('mark_appointment_complete', 'today_appointments', 'completed'),
            ('doctor_cancel_appointment', 'appointment_list', 'cancelled'),
        ):
            with self.subTest(action=action):
                self.appointment.status = 'confirmed'
                self.appointment.save()
                response = self.client.post(reverse(action, args=[self.appointment.pk]),
                    {'next': target}, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.redirect_chain[0][0], reverse(target))
                self.appointment.refresh_from_db()
                self.assertEqual(self.appointment.status, status)

    def test_portal_pages(self):
        pages = {
            'receptionist': ['receptionist_dashboard', 'receptionist_patient_list',
                'receptionist_register_patient', 'receptionist_today_appointments',
                'receptionist_book_appointment', 'receptionist_appointment_list',
                'receptionist_billing_list', 'receptionist_doctor_list',
                'receptionist_notifications', 'receptionist_profile',
                'receptionist_edit_profile', 'receptionist_change_password'],
            'doctor': ['doctor_home', 'today_appointments', 'appointment_list',
                'patient_list', 'add_prescription', 'prescription_history', 'availability',
                'doctor_notifications', 'doctor_profile', 'edit_profile', 'change_password'],
            'admin': ['admin_dashboard', 'admin_doctor_list', 'admin_add_doctor',
                'admin_receptionist_list', 'admin_add_receptionist', 'admin_patient_list',
                'admin_appointment_list', 'admin_billing_list', 'admin_security_settings',
                'admin_notifications', 'admin_profile', 'admin_edit_profile', 'admin_change_password'],
            'patient': ['patient_dashboard', 'patient_profile',
                'book_appointment', 'my_appointments', 'my_billing', 'notifications'],
        }
        for role, names in pages.items():
            self.client.force_login(self.users[role])
            for name in names:
                with self.subTest(role=role, page=name):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_patient_password_form_redirect(self):
        self.client.force_login(self.users['patient'])
        response = self.client.get(reverse('patient_change_password'))
        self.assertEqual(response.url, reverse('patient_profile') + '#change-password')

    def test_booking_and_duplicate_slot_rejection(self):
        tomorrow = date.today() + timedelta(days=1)
        slots_url = reverse('receptionist_get_doctor_slots')
        response = self.client.get(slots_url, {'doctor': self.doctor.pk, 'date': tomorrow.isoformat()})
        self.assertEqual(response.status_code, 200)
        slot = response.json()['slots'][0]['time']
        payload = {'patient': self.patient.pk, 'doctor': self.doctor.pk,
                   'appointment_date': tomorrow.isoformat(), 'time_slot': slot, 'reason': 'Checkup'}
        response = self.client.post(reverse('receptionist_book_appointment'), payload, follow=True)
        self.assertEqual(response.status_code, 200)
        booked = Appointment.objects.get(appointment_date=tomorrow)
        self.assertEqual(booked.status, 'confirmed')
        self.assertEqual(booked.bills.get().amount, self.doctor.consultation_fee)
        self.assertTrue(Notification.objects.filter(user=self.users['patient']).exists())
        self.client.post(reverse('receptionist_book_appointment'), payload)
        self.assertEqual(Appointment.objects.filter(appointment_date=tomorrow).count(), 1)
        self.assertEqual(self.client.get(slots_url, {'doctor': self.doctor.pk, 'date': 'invalid'}).status_code, 400)

    def test_patient_registration_and_search(self):
        response = self.client.post(reverse('receptionist_register_patient'), {
            'full_name': 'Jane Smith', 'email': 'jane@example.com',
            'password': 'StrongWalkinPass837!', 'confirm_password': 'StrongWalkinPass837!',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        patient = Patient.objects.get(user__email='jane@example.com')
        self.assertEqual(patient.registered_by.user, self.users['receptionist'])
        response = self.client.get(reverse('receptionist_search_patients'), {'q': 'Jane'})
        self.assertEqual(response.json()['results'][0]['id'], patient.pk)

    def test_notification_actions(self):
        note = Notification.objects.create(user=self.users['receptionist'], message='Test notification')
        response = self.client.post(reverse('receptionist_mark_all_read'), follow=True)
        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertTrue(note.is_read)
        response = self.client.post(reverse('receptionist_dismiss_notification', args=[note.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notification.objects.filter(pk=note.pk).exists())

    def test_receipts_and_patient_details(self):
        for role, routes in {
            'receptionist': [('receptionist_patient_detail', self.patient.pk),
                             ('receptionist_billing_receipt', self.bill.pk)],
            'admin': [('admin_patient_detail', self.patient.pk),
                      ('admin_doctor_detail', self.doctor.pk), ('admin_billing_receipt', self.bill.pk)],
            'doctor': [('patient_details', self.patient.pk)],
            'patient': [('billing_receipt', self.bill.pk)],
        }.items():
            self.client.force_login(self.users[role])
            for name, pk in routes:
                with self.subTest(role=role, page=name):
                    self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 200)
