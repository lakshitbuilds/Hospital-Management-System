"""Document-only PDF exports shared by the hospital portals."""
from html import escape
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def pdf_response(content, filename):
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response['Cache-Control'] = 'private, no-store'
    return response


class HospitalDocument:
    def __init__(self, title, reference):
        self.title = title
        self.reference = reference
        self.styles = getSampleStyleSheet()
        self.body_style = ParagraphStyle('DocumentBody', parent=self.styles['BodyText'],
                                         fontSize=10, leading=15, splitLongWords=True)
        self.heading_style = ParagraphStyle('DocumentHeading', parent=self.styles['Heading2'],
                                            textColor=colors.HexColor('#17365D'), spaceBefore=14)
        self.story = [Paragraph('MediCare Hospital', self.styles['Title']),
                      Paragraph(escape(title), self.styles['Heading1']),
                      self.text(reference), Spacer(1, 6 * mm)]

    def text(self, value):
        value = '-' if value in (None, '') else str(value)
        return Paragraph(escape(value).replace('\n', '<br/>'), self.body_style)

    def section(self, title, value):
        self.story.extend([Paragraph(escape(title), self.heading_style), self.text(value)])

    def table(self, headers, rows, proportions):
        header_style = ParagraphStyle('DocumentTableHeader', parent=self.body_style,
                                      fontName='Helvetica-Bold', textColor=colors.white)
        widths = [174 * mm * p / sum(proportions) for p in proportions]
        data = [[Paragraph(escape(h), header_style) for h in headers]]
        # Split exceptionally tall cells into continuation rows before pagination.
        # This keeps headings from repeating within the same page when ReportLab
        # repeatedly attempts to split one oversized medicine row.
        for row in rows:
            pending = [[self.text(value)] for value in row]
            while any(pending):
                cells = []
                for index, queue in enumerate(pending):
                    if not queue:
                        cells.append('')
                        continue
                    paragraph = queue.pop(0)
                    _, height = paragraph.wrap(widths[index] - 14, 350)
                    if height > 350:
                        parts = paragraph.split(widths[index] - 14, 350)
                        paragraph = parts[0]
                        queue[:0] = parts[1:]
                    cells.append(paragraph)
                data.append(cells)
        table = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17365D')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F3F6FA')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#CDD6E0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        self.story.extend([Spacer(1, 4 * mm), table])

    def build(self):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                                topMargin=18 * mm, bottomMargin=20 * mm,
                                title=f'{self.title} - {self.reference}', author='MediCare Hospital')

        def footer(canvas, document):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor('#CDD6E0'))
            canvas.line(18 * mm, 15 * mm, 192 * mm, 15 * mm)
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#586577'))
            canvas.drawString(18 * mm, 10 * mm, 'MediCare Hospital | Confidential')
            canvas.drawRightString(192 * mm, 10 * mm, f'Page {document.page}')
            canvas.restoreState()

        doc.build(self.story, onFirstPage=footer, onLaterPages=footer)
        return buffer.getvalue()


def prescription_pdf(rx):
    doc = HospitalDocument('Prescription', f'RX-{rx.pk:06d} | {timezone.localtime(rx.created_at):%d %b %Y}')
    doc.section('Patient', f'{rx.patient.user.get_full_name()} | {rx.patient.patient_id}')
    doc.section('Prescribing Doctor', f'Dr. {rx.doctor.user.get_full_name()} | {rx.doctor.get_department_display()}')
    if rx.appointment:
        doc.section('Appointment', f'{rx.appointment.appointment_date:%d %b %Y} | {rx.appointment.time_slot}')
    doc.section('Diagnosis', rx.diagnosis)
    medicines = list(rx.medicines.all())
    if medicines:
        doc.table(['Medicine', 'Dosage', 'Frequency', 'Duration', 'Instructions'],
                  [(m.name, m.dosage, m.get_frequency_display(), m.duration, m.instructions) for m in medicines],
                  [24, 14, 20, 16, 26])
    else:
        doc.section('Medicines', 'No medicines prescribed.')
    if rx.advice:
        doc.section("Doctor's Advice", rx.advice)
    if rx.follow_up_date:
        doc.section('Follow-up', rx.follow_up_date.strftime('%d %b %Y'))
    return doc.build()


def receipt_pdf(bill):
    doc = HospitalDocument('Billing Receipt', f'RCP-{bill.pk:06d} | {timezone.localtime(bill.created_at):%d %b %Y}')
    doc.section('Billed To', f'{bill.patient.user.get_full_name()} | {bill.patient.patient_id}\n{bill.patient.phone}')
    appointment = bill.appointment
    doc.section('Appointment', f'Dr. {appointment.doctor.user.get_full_name()}\n{appointment.get_department_display()} | {appointment.appointment_date:%d %b %Y} | {appointment.time_slot}')
    doc.section('Payment Status', bill.get_status_display())
    if bill.paid_at:
        doc.section('Paid On', timezone.localtime(bill.paid_at).strftime('%d %b %Y, %I:%M %p'))
    doc.table(['Description', 'Amount (INR)'], [(bill.get_bill_type_display(), f'{bill.amount:,.2f}'),
                                             ('Total', f'{bill.amount:,.2f}')], [75, 25])
    doc.section('Receipt Note', 'This is a computer-generated receipt and does not require a signature.')
    return doc.build()


def patient_summary_pdf(patient, doctor, history, prescriptions):
    doc = HospitalDocument('Patient Summary', f'{patient.patient_id} | Generated {timezone.localtime():%d %b %Y}')
    doc.section('Patient', f'{patient.user.get_full_name()}\n{patient.user.email} | {patient.phone}')
    doc.section('Treating Doctor', f'Dr. {doctor.user.get_full_name()}')
    doc.section('Personal Information', f'Date of birth: {patient.date_of_birth or "Not provided"}\nGender: {patient.gender or "Not provided"}\nBlood group: {patient.blood_group or "Not provided"}\nAddress: {patient.address}\n{patient.city} {patient.state} {patient.country} {patient.pincode}')
    doc.section('Emergency Contact', f'{patient.emergency_contact_name or "Not provided"}\n{patient.emergency_contact_number}')
    doc.section('Allergies', patient.allergies or 'No known allergies on record.')
    doc.section('Medical History', patient.medical_history or 'No medical history on record.')
    doc.section('Appointment History', 'Visits with this doctor')
    doc.table(['Date', 'Time', 'Visit Type', 'Status'],
              [(a.appointment_date.strftime('%d %b %Y'), a.time_slot, a.get_visit_type_display(), a.get_status_display()) for a in history], [25, 25, 25, 25])
    doc.section('Prescriptions', 'Prescriptions issued by this doctor')
    for rx in prescriptions:
        doc.section(rx.created_at.strftime('%d %b %Y'), rx.diagnosis)
        doc.table(['Medicine', 'Dosage', 'Frequency', 'Duration', 'Instructions'],
                  [(m.name, m.dosage, m.get_frequency_display(), m.duration, m.instructions) for m in rx.medicines.all()], [24, 14, 20, 16, 26])
        if rx.advice:
            doc.section('Advice', rx.advice)
        if rx.follow_up_date:
            doc.section('Follow-up', rx.follow_up_date.strftime('%d %b %Y'))
    return doc.build()
