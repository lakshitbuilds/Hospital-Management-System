from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.http import QueryDict
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from doctor.models import Doctor, Prescription
from form_handling import BoundHTML
from patient.models import Appointment, ContactMessage, Patient
from receptionist.models import Receptionist


class BoundControlTests(SimpleTestCase):
    def test_all_control_types_and_safe_escaping(self):
        data = QueryDict('', mutable=True)
        data.update({'text': '"><script>alert(1)</script>', 'notes': '</textarea><script>x</script>',
                     'day': '2026-10-22', 'choice': 'b', 'radio': 'b', 'check': 'yes'})
        data.setlist('multi', ['a', 'b'])
        data.setlist('rows[]', ['first', 'second'])
        parser = BoundHTML(data)
        parser.feed('''<form method="post"><input name="text"><textarea name="notes">old</textarea>
        <input type="date" name="day"><select name="choice"><option value="a" selected>A</option><option value="b">B</option></select>
        <select name="multi" multiple><option value="a">A</option><option value="b">B</option></select>
        <input name="radio" type="radio" value="a" checked><input name="radio" type="radio" value="b">
        <input name="check" type="checkbox" value="yes"><input name="unchecked" type="checkbox" checked>
        <input name="rows[]"><input name="rows[]"><input name="csrfmiddlewaretoken" value="original"></form>''')
        result = ''.join(parser.output)
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('<script>', result)
        self.assertIn('value="2026-10-22"', result)
        self.assertIn('<option value="b" selected>', result)
        self.assertIn('name="radio" type="radio" value="b" checked', result)
        self.assertNotIn('name="unchecked" type="checkbox" checked', result)
        self.assertIn('value="first"', result)
        self.assertIn('value="second"', result)
        self.assertIn('value="original"', result)


class FormPersistenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='admin', email='admin@example.com', role='admin')
        cls.doctor_user = User.objects.create_user(username='doctor', email='doctor@example.com', role='doctor', first_name='Original', last_name='Doctor')
        cls.doctor = Doctor.objects.create(user=cls.doctor_user, department='general')
        cls.receptionist_user = User.objects.create_user(username='receptionist', email='reception@example.com', role='receptionist')
        Receptionist.objects.create(user=cls.receptionist_user)
        cls.patient_user = User.objects.create_user(username='patient', email='patient@example.com', role='patient')
        cls.patient = Patient.objects.create(user=cls.patient_user)
        Appointment.objects.create(patient=cls.patient, doctor=cls.doctor, appointment_date=date(2026, 10, 22), time_slot='10:00 AM', reason='Checkup')

    def test_admin_onboarding_error_preserves_fields_and_password(self):
        self.client.force_login(self.admin)
        for url in ['admin_add_doctor', 'admin_add_receptionist']:
            response = self.client.post(reverse(url), {'full_name': 'Jane Smith', 'email': 'jane@example.com', 'department': 'general',
                'password': 'Sample!Pass123', 'confirm_password': 'Mismatch!123', 'specialization': 'General practice', 'shift': 'night'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Passwords do not match.')
            for value in ['Jane Smith', 'jane@example.com', 'Sample!Pass123', 'Mismatch!123']:
                self.assertContains(response, f'value="{value}"')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertFalse(get_user_model().objects.filter(email='jane@example.com').exists())

    def test_patient_registration_error_preserves_select_date_and_textarea(self):
        self.client.force_login(self.receptionist_user)
        response = self.client.post(reverse('receptionist_register_patient'), {'full_name': 'Jane Smith', 'email': 'jane@example.com',
            'password': 'one', 'confirm_password': 'two', 'date_of_birth': '1995-04-03', 'gender': 'Female',
            'blood_group': 'O+', 'address': '21 Test Street', 'medical_history': 'Asthma & allergies'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="1995-04-03"')
        self.assertContains(response, 'value="Female" selected')
        self.assertContains(response, 'value="O+" selected')
        self.assertContains(response, '>21 Test Street</textarea>')
        self.assertContains(response, 'Asthma &amp; allergies</textarea>')

    def test_database_error_rolls_back_onboarding_and_preserves_input(self):
        self.client.force_login(self.admin)
        with self.assertLogs('form_handling', level='ERROR'), patch('adminpanel.views.Doctor.objects.create', side_effect=OperationalError('temporary failure')):
            response = self.client.post(reverse('admin_add_doctor'), {'full_name': 'Jane Smith', 'email': 'jane@example.com',
                'department': 'general', 'password': 'Sample!Pass123', 'confirm_password': 'Sample!Pass123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your changes could not be saved.')
        self.assertContains(response, 'value="jane@example.com"')
        self.assertFalse(get_user_model().objects.filter(email='jane@example.com').exists())

    def test_success_saves_and_redirects_to_fresh_form(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin_add_doctor'), {'full_name': 'Jane Smith', 'email': 'jane@example.com',
            'department': 'general', 'password': 'Sample!Pass123', 'confirm_password': 'Sample!Pass123'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Doctor.objects.filter(user__email='jane@example.com').exists())
        self.assertNotContains(self.client.get(reverse('admin_add_doctor')), 'value="jane@example.com"')

    def test_profile_save_failure_rolls_back_user_update(self):
        self.client.force_login(self.doctor_user)
        with self.assertLogs('form_handling', level='ERROR'), patch.object(Doctor, 'save', side_effect=OperationalError('temporary failure')):
            response = self.client.post(reverse('edit_profile'), {'first_name': 'Changed', 'last_name': 'Doctor',
                'email': 'changed@example.com', 'department': 'general', 'experience_years': '5', 'consultation_fee': '300', 'bio': 'Entered bio'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Changed"')
        self.assertContains(response, 'Entered bio</textarea>')
        self.doctor_user.refresh_from_db()
        self.assertEqual(self.doctor_user.first_name, 'Original')

    def test_dynamic_prescription_rows_survive_validation_error(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(reverse('add_prescription'), {'patient_id': self.patient.pk, 'diagnosis': '',
            'medicine_name[]': ['Medicine One', 'Medicine Two'], 'dosage[]': ['10 mg', '20 mg'],
            'frequency[]': ['once_a_day', 'twice_a_day'], 'duration[]': ['3 days', '4 days'],
            'instructions[]': ['After food', 'Before food'], 'advice': 'Rest and hydrate', 'follow_up_date': '2026-11-04'})
        self.assertEqual(response.status_code, 200)
        for value in ['Medicine One', 'Medicine Two', '10 mg', '20 mg', '2026-11-04']:
            self.assertContains(response, f'value="{value}"')
        self.assertContains(response, 'value="twice_a_day" selected')
        self.assertFalse(Prescription.objects.exists())

    def test_contact_error_and_success(self):
        data = {'full_name': 'Jane Smith', 'email': 'jane@example.com', 'phone': '1234567890', 'subject': 'general', 'message': ''}
        response = self.client.post(reverse('contact'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Jane Smith"')
        self.assertFalse(ContactMessage.objects.exists())
        data['message'] = 'Please call me'
        self.assertEqual(self.client.post(reverse('contact'), data).status_code, 302)
        self.assertTrue(ContactMessage.objects.filter(message='Please call me').exists())

    def test_public_registration_keeps_radio_and_checkbox(self):
        response = self.client.post(reverse('register'), {'full_name': 'Jane Smith', 'email': 'jane@example.com',
            'phone': '1234567890', 'date_of_birth': '1995-04-03', 'gender': 'female',
            'password': 'first', 'confirm_password': 'second', 'agree_terms': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="female" class="gender-input" checked')
        self.assertContains(response, 'name="agree_terms" required checked')
        self.assertContains(response, 'value="jane@example.com"')

    def test_patient_booking_keeps_values_and_dynamic_slot_hint(self):
        self.client.force_login(self.patient_user)
        with patch.object(Doctor, 'get_available_slots', return_value={'available': False, 'reason': 'No availability'}):
            response = self.client.post(reverse('book_appointment'), {'doctor': self.doctor.pk, 'department': 'general',
                'appointment_date': '2026-11-12', 'time_slot': '10:00 AM', 'visit_type': 'follow-up', 'reason': 'Keep this reason'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-11-12"')
        self.assertContains(response, 'data-selected-slot="10:00 AM"')
        self.assertContains(response, 'Keep this reason</textarea>')
        self.assertNotIn('pending_appointment', self.client.session)

    def test_availability_keeps_unsaved_blocked_rows_and_checkboxes(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(reverse('availability'), {'available_monday': 'on', 'start_monday': '17:00',
            'end_monday': '09:00', 'slot_duration': '30', 'blocked_date[]': ['2020-01-01', '2020-02-01'],
            'blocked_reason[]': ['Keep first reason', 'Keep second reason']})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="17:00"')
        self.assertContains(response, 'value="2020-01-01"')
        self.assertContains(response, 'value="2020-02-01"')
        self.assertContains(response, 'Keep second reason')

    def test_password_error_reopens_patient_password_tab(self):
        self.client.force_login(self.patient_user)
        response = self.client.post(reverse('patient_change_password'), {'current_password': 'Incorrect',
            'new_password': 'Sample!Pass123', 'confirm_new_password': 'Sample!Pass123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-tab="change-password"')
        self.assertContains(response, 'value="Sample!Pass123"')
        self.assertContains(response, 'Current password is incorrect.')

    def test_bad_login_keeps_email_role_and_password(self):
        response = self.client.post(reverse('login'), {'email': 'invalid@example.com', 'password': 'incorrect', 'role': 'doctor'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="invalid@example.com"')
        self.assertContains(response, 'value="incorrect"')
        self.assertContains(response, 'Invalid email or password.')
