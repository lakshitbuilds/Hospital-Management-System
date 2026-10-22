from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from doctor.models import Doctor, Prescription, PrescriptionMedicine
from pdf_documents import prescription_pdf
from .models import Appointment, Billing, Patient


class PDFExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.users = {
            role: User.objects.create_user(username=role, email=f'{role}@example.com', role=role)
            for role in ['patient', 'doctor', 'admin', 'receptionist']
        }
        cls.patient = Patient.objects.create(user=cls.users['patient'])
        cls.doctor = Doctor.objects.create(user=cls.users['doctor'], department='general')
        cls.appointment = Appointment.objects.create(patient=cls.patient, doctor=cls.doctor,
                                                    appointment_date=date(2026, 10, 22), time_slot='10:00 AM', reason='Checkup')
        cls.bill = Billing.objects.create(patient=cls.patient, appointment=cls.appointment, amount='1250.00')
        cls.rx = Prescription.objects.create(patient=cls.patient, doctor=cls.doctor,
                                             diagnosis='Allergy <mild> & irritation', advice='Drink water')
        PrescriptionMedicine.objects.create(prescription=cls.rx, name='Medicine', dosage='10 mg',
                                             frequency='once_a_day', duration='5 days', instructions='After food')
        other_user = User.objects.create_user(username='other', email='other@example.com', role='patient')
        cls.other_patient = Patient.objects.create(user=other_user)
        other_doctor_user = User.objects.create_user(username='other_doctor', email='other_doctor@example.com', role='doctor')
        cls.other_doctor = Doctor.objects.create(user=other_doctor_user, department='general')

    def assert_pdf(self, response, filename):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(filename, response['Content-Disposition'])
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertTrue(response.content.rstrip().endswith(b'%%EOF'))

    def test_prescription_downloads_use_selected_record(self):
        for role, url in [('doctor', 'doctor_prescription_pdf'), ('patient', 'patient_prescription_pdf')]:
            self.client.force_login(self.users[role])
            with patch(f'{role}.views.prescription_pdf', wraps=prescription_pdf) as renderer:
                response = self.client.get(reverse(url, args=[self.rx.pk]))
                self.assertEqual(renderer.call_args.args[0].pk, self.rx.pk)
            self.assert_pdf(response, f'prescription-{self.rx.pk:06d}.pdf')

    def test_receipts_all_portals(self):
        for role, url in [('patient', 'billing_receipt'), ('admin', 'admin_billing_receipt'), ('receptionist', 'receptionist_billing_receipt')]:
            self.client.force_login(self.users[role])
            self.assert_pdf(self.client.get(reverse(url, args=[self.bill.pk]), {'format': 'pdf'}), f'receipt-{self.bill.pk:06d}.pdf')
            self.assertContains(self.client.get(reverse(url, args=[self.bill.pk])), 'Preview &amp; Print')

    def test_patient_cannot_download_other_patient_documents(self):
        self.client.force_login(self.other_patient.user)
        self.assertEqual(self.client.get(reverse('patient_prescription_pdf', args=[self.rx.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('billing_receipt', args=[self.bill.pk]), {'format': 'pdf'}).status_code, 404)

    def test_doctor_cannot_download_other_doctor_documents(self):
        self.client.force_login(self.other_doctor.user)
        self.assertEqual(self.client.get(reverse('doctor_prescription_pdf', args=[self.rx.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('patient_details', args=[self.patient.pk]), {'format': 'pdf'}).status_code, 404)

    def test_patient_summary(self):
        self.client.force_login(self.users['doctor'])
        self.assert_pdf(self.client.get(reverse('patient_details', args=[self.patient.pk]), {'format': 'pdf'}), f'patient-{self.patient.patient_id}.pdf')

    def test_report_exports(self):
        self.client.force_login(self.users['admin'])
        for report_type in ['patients', 'appointments', 'doctors', 'billing']:
            response = self.client.get(reverse('generate_report'), {'report_type': report_type, 'format': 'pdf', 'q': '<test> & sample'})
            self.assert_pdf(response, f'{report_type}_report.pdf')

    def test_anonymous_and_wrong_role_access(self):
        url = reverse('doctor_prescription_pdf', args=[self.rx.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.users['receptionist'])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.get(reverse('patient_prescription_pdf', args=[self.rx.pk])).status_code, 302)

    def test_long_prescription_can_span_pages(self):
        self.rx.advice = 'Long advice & <literal text>\n' * 200
        self.rx.diagnosis = 'Long diagnosis ' * 600
        self.rx.save()
        PrescriptionMedicine.objects.create(prescription=self.rx, name='Very long name ' * 100,
                                             instructions='Very long instructions ' * 500)
        self.client.force_login(self.users['doctor'])
        self.assert_pdf(self.client.get(reverse('doctor_prescription_pdf', args=[self.rx.pk])), f'prescription-{self.rx.pk:06d}.pdf')
