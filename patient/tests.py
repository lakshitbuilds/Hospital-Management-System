from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from doctor.models import Doctor, Prescription, PrescriptionMedicine
from .models import Appointment, Patient


class PatientPrescriptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username='patient', email='patient@example.com', role='patient')
        cls.patient = Patient.objects.create(user=cls.user)
        cls.other_user = User.objects.create_user(username='other', email='other@example.com', role='patient')
        cls.other_patient = Patient.objects.create(user=cls.other_user)
        cls.doctor_user = User.objects.create_user(username='doctor', email='doctor@example.com', role='doctor', first_name='Alex', last_name='Smith')
        cls.doctor = Doctor.objects.create(user=cls.doctor_user, department='general')
        cls.appointment = Appointment.objects.create(patient=cls.patient, doctor=cls.doctor, appointment_date=date(2026, 10, 22), time_slot='10:00 AM', reason='Consultation')

    def test_doctor_created_prescription_is_visible_to_patient(self):
        self.client.force_login(self.doctor_user)
        response = self.client.post(reverse('add_prescription'), {
            'patient_id': self.patient.pk,
            'appointment_id': self.appointment.pk,
            'diagnosis': 'Seasonal allergy',
            'advice': 'Avoid dust',
            'follow_up_date': '2026-11-05',
            'medicine_name[]': ['Allergy medicine'],
            'dosage[]': ['10 mg'],
            'frequency[]': ['once_a_day'],
            'duration[]': ['5 days'],
            'instructions[]': ['After food'],
        })
        self.assertRedirects(response, reverse('prescription_history'), fetch_redirect_response=False)
        self.client.force_login(self.user)
        response = self.client.get(reverse('my_prescriptions'))
        for value in ['Alex Smith', 'Seasonal allergy', 'Avoid dust', 'Allergy medicine', '10 mg', 'Once a day', '5 days', 'After food', 'Nov 05, 2026']:
            self.assertContains(response, value)
        self.assertEqual(len(response.context['prescriptions']), 1)

    def test_only_own_prescriptions_including_without_appointment_are_shown(self):
        own = Prescription.objects.create(patient=self.patient, doctor=self.doctor, diagnosis='Own diagnosis')
        foreign = Prescription.objects.create(patient=self.other_patient, doctor=self.doctor, diagnosis='Private diagnosis')
        PrescriptionMedicine.objects.create(prescription=foreign, name='Private medicine')
        self.client.force_login(self.user)
        response = self.client.get(reverse('my_prescriptions'), {'patient_id': self.other_patient.pk})
        self.assertContains(response, 'Own diagnosis')
        self.assertNotContains(response, 'Private diagnosis')
        self.assertNotContains(response, 'Private medicine')
        self.assertEqual(list(response.context['prescriptions']), [own])

    def test_empty_state(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('my_prescriptions')), 'No prescriptions yet')

    def test_anonymous_and_non_patient_cannot_access(self):
        self.assertRedirects(self.client.get(reverse('my_prescriptions')), reverse('login') + '?next=' + reverse('my_prescriptions'), fetch_redirect_response=False)
        self.client.force_login(self.doctor_user)
        self.assertRedirects(self.client.get(reverse('my_prescriptions')), reverse('home'), fetch_redirect_response=False)

    def test_dashboard_and_profile_link_to_prescriptions(self):
        self.client.force_login(self.user)
        for name in ['patient_dashboard', 'patient_profile']:
            self.assertContains(self.client.get(reverse(name)), reverse('my_prescriptions'))
