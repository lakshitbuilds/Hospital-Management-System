import csv
from io import BytesIO

from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from doctor.models import Doctor
from patient.models import Appointment, Billing, Patient
from .views import admin_required, DEPARTMENT_LABELS


def _pdf_text(value, style):
    text = str(value if value not in (None, '') else '-').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(text, style)


def _column_widths(report_type):
    widths = {
        'patients': [27, 42, 65, 35, 28],
        'appointments': [37, 37, 37, 25, 25, 28, 27],
        'doctors': [40, 37, 43, 48, 27, 25],
        'billing': [37, 27, 34, 42, 25, 28, 25],
    }
    return [value * mm for value in widths.get(report_type, [])]


def _build_pdf(report_type, headers, rows, filter_summary, total_amount=None):
    buffer = BytesIO()
    page_size = landscape(A4)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f'HMS {report_type.title()} Report',
        author='Hospital Management System',
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#17365D'),
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
    )
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#5B6573'),
        alignment=TA_CENTER,
    )
    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#263238'),
        alignment=TA_LEFT,
    )
    amount_style = ParagraphStyle(
        'AmountCell',
        parent=cell_style,
        alignment=TA_RIGHT,
    )
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#17365D'),
    )

    story = [
        Paragraph('Hospital Management System', title_style),
        Paragraph(f'{report_type.title()} Report', subtitle_style),
        Spacer(1, 3 * mm),
    ]

    info_data = [
        [Paragraph('<b>Filters</b>', cell_style), Paragraph(filter_summary, cell_style)],
        [Paragraph('<b>Generated</b>', cell_style), Paragraph(timezone.localtime().strftime('%d %b %Y, %I:%M %p'), cell_style)],
        [Paragraph('<b>Total Records</b>', cell_style), Paragraph(str(len(rows)), cell_style)],
    ]
    if total_amount is not None:
        info_data.append([
            Paragraph('<b>Total Amount</b>', cell_style),
            Paragraph(f'Rs. {total_amount}', summary_style),
        ])

    info_table = Table(info_data, colWidths=[32 * mm, 230 * mm], hAlign='LEFT')
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EAF2F8')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#C8D6E5')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#DCE6EF')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([info_table, Spacer(1, 5 * mm)])

    table_data = [[_pdf_text(header, header_style) for header in headers]]
    for row in rows:
        pdf_row = []
        for index, value in enumerate(row):
            style = amount_style if report_type == 'billing' and headers[index] == 'Amount' else cell_style
            pdf_row.append(_pdf_text(value, style))
        table_data.append(pdf_row)

    if not rows:
        table_data.append([Paragraph('No records found for the selected filters.', cell_style)] + [''] * (len(headers) - 1))

    report_table = Table(
        table_data,
        colWidths=_column_widths(report_type),
        repeatRows=1,
        hAlign='CENTER',
    )
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17365D')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.45, colors.HexColor('#B7C9D6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F8FA')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    if not rows:
        report_table.setStyle(TableStyle([('SPAN', (0, 1), (-1, 1)), ('ALIGN', (0, 1), (-1, 1), 'CENTER')]))

    story.append(report_table)

    def add_page_number(canvas, document):
        canvas.saveState()
        width, _ = page_size
        canvas.setStrokeColor(colors.HexColor('#D7E1EA'))
        canvas.line(12 * mm, 11 * mm, width - 12 * mm, 11 * mm)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#6B7280'))
        canvas.drawString(12 * mm, 7 * mm, 'Hospital Management System')
        canvas.drawRightString(width - 12 * mm, 7 * mm, f'Page {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return buffer.getvalue()


@admin_required
def generate_report(request):
    report_type = request.GET.get('report_type', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    status = request.GET.get('status', '').strip()
    department = request.GET.get('department', '').strip()
    doctor_id = request.GET.get('doctor', '').strip()
    bill_type = request.GET.get('bill_type', '').strip()
    search = request.GET.get('q', '').strip()
    export_format = request.GET.get('format', '').strip().lower()

    doctors_for_filter = Doctor.objects.select_related('user').order_by('user__first_name', 'user__last_name')
    base_context = {
        'departments': Doctor.DEPARTMENT_CHOICES,
        'doctors': doctors_for_filter,
        'appointment_statuses': Appointment.STATUS_CHOICES,
        'billing_statuses': Billing.STATUS_CHOICES,
        'bill_types': Billing.BILL_TYPE_CHOICES,
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'status': status,
        'department': department,
        'doctor_id': doctor_id,
        'bill_type': bill_type,
        'q': search,
    }

    if not report_type:
        return render(request, 'adminpanel/generate_report.html', base_context)

    if start_date and end_date and start_date > end_date:
        messages.error(request, 'Start date cannot be after end date.')
        return render(request, 'adminpanel/generate_report.html', base_context)

    headers, rows = [], []
    summary = {'total_amount': None}

    if report_type == 'patients':
        qs = Patient.objects.select_related('user').order_by('-created_at', '-id')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        if search:
            qs = qs.filter(
                Q(patient_id__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(phone__icontains=search)
            )
        headers = ['Patient ID', 'Patient Name', 'Email', 'Phone', 'Created At']
        rows = [[p.patient_id, p.user.get_full_name() or '-', p.user.email, p.phone or '-', p.created_at.strftime('%d-%m-%Y')] for p in qs]

    elif report_type == 'appointments':
        qs = Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-appointment_date', '-id')
        if start_date:
            qs = qs.filter(appointment_date__gte=start_date)
        if end_date:
            qs = qs.filter(appointment_date__lte=end_date)
        if status:
            qs = qs.filter(status=status)
        if department:
            qs = qs.filter(department=department)
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        if search:
            qs = qs.filter(
                Q(patient__patient_id__icontains=search) |
                Q(patient__user__first_name__icontains=search) |
                Q(patient__user__last_name__icontains=search) |
                Q(doctor__user__first_name__icontains=search) |
                Q(doctor__user__last_name__icontains=search) |
                Q(reason__icontains=search)
            )
        headers = ['Patient', 'Doctor', 'Department', 'Date', 'Time', 'Visit Type', 'Status']
        rows = [[
            a.patient.user.get_full_name() or a.patient.patient_id,
            f'Dr. {a.doctor.user.get_full_name()}',
            DEPARTMENT_LABELS.get(a.department, a.department),
            a.appointment_date.strftime('%d-%m-%Y'),
            a.time_slot,
            a.get_visit_type_display(),
            a.get_status_display(),
        ] for a in qs]

    elif report_type == 'doctors':
        qs = Doctor.objects.select_related('user').order_by('user__first_name', 'id')
        if department:
            qs = qs.filter(department=department)
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(specialization__icontains=search) |
                Q(qualification__icontains=search)
            )
        headers = ['Doctor Name', 'Department', 'Specialization', 'Qualification', 'Experience', 'Fee']
        rows = [[
            f'Dr. {d.user.get_full_name()}',
            d.get_department_display(),
            d.specialization or '-',
            d.qualification or '-',
            f'{d.experience_years} years',
            f'Rs. {d.consultation_fee}',
        ] for d in qs]

    elif report_type == 'billing':
        qs = Billing.objects.select_related('patient__user', 'appointment__doctor__user').order_by('-created_at', '-id')
        if start_date:
            qs = qs.filter(appointment__appointment_date__gte=start_date)
        if end_date:
            qs = qs.filter(appointment__appointment_date__lte=end_date)
        if status:
            qs = qs.filter(status=status)
        if department:
            qs = qs.filter(appointment__department=department)
        if doctor_id:
            qs = qs.filter(appointment__doctor_id=doctor_id)
        if bill_type:
            qs = qs.filter(bill_type=bill_type)
        if search:
            qs = qs.filter(
                Q(patient__patient_id__icontains=search) |
                Q(patient__user__first_name__icontains=search) |
                Q(patient__user__last_name__icontains=search) |
                Q(appointment__doctor__user__first_name__icontains=search) |
                Q(appointment__doctor__user__last_name__icontains=search)
            )
        summary['total_amount'] = qs.aggregate(total=Sum('amount'))['total'] or 0
        headers = ['Patient', 'Patient ID', 'Bill Type', 'Doctor', 'Date', 'Amount', 'Status']
        rows = [[
            b.patient.user.get_full_name() or '-',
            b.patient.patient_id,
            b.get_bill_type_display(),
            f'Dr. {b.appointment.doctor.user.get_full_name()}',
            b.appointment.appointment_date.strftime('%d-%m-%Y'),
            f'Rs. {b.amount}',
            b.get_status_display(),
        ] for b in qs]
    else:
        messages.error(request, 'Invalid report type.')
        return redirect('generate_report')

    filter_parts = []
    if start_date or end_date:
        filter_parts.append(f'Date: {start_date or "Any"} to {end_date or "Any"}')
    if status:
        filter_parts.append(f'Status: {status.title()}')
    if department:
        filter_parts.append(f'Department: {DEPARTMENT_LABELS.get(department, department)}')
    if doctor_id:
        doctor = doctors_for_filter.filter(id=doctor_id).first()
        if doctor:
            filter_parts.append(f'Doctor: Dr. {doctor.user.get_full_name()}')
    if bill_type:
        filter_parts.append(f'Bill type: {dict(Billing.BILL_TYPE_CHOICES).get(bill_type, bill_type)}')
    if search:
        filter_parts.append(f'Search: {search}')
    filter_summary = ' | '.join(filter_parts) if filter_parts else 'All records'

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(headers)
        writer.writerows(rows)
        return response

    if export_format == 'pdf':
        pdf = _build_pdf(report_type, headers, rows, filter_summary, summary['total_amount'])
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        return response

    context = {
        **base_context,
        'headers': headers,
        'rows': rows,
        'total_records': len(rows),
        'total_amount': summary['total_amount'],
        'filter_summary': filter_summary,
    }
    return render(request, 'adminpanel/report_result.html', context)
