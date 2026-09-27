"""Advanced report generation for the admin portal.

Kept separate from views.py so report filtering/export logic stays focused and easy to maintain.
"""
import csv
from io import BytesIO

from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render

from doctor.models import Doctor
from patient.models import Appointment, Billing, Patient
from .views import admin_required, DEPARTMENT_LABELS


def _pdf_escape(value):
    return str(value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _simple_pdf(title, headers, rows, filter_summary):
    """Create a dependency-free, printable PDF containing the filtered report."""
    lines = [title, filter_summary, '']
    # A compact text table is intentionally used so wide reports remain readable.
    lines.append(' | '.join(str(h) for h in headers))
    lines.append('-' * 105)
    for row in rows:
        lines.append(' | '.join(str(v) for v in row))
    if not rows:
        lines.append('No records found for the selected filters.')

    pages = [lines[i:i + 45] for i in range(0, len(lines), 45)] or [[]]
    objects = []
    font_id = 1
    objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    page_ids = []
    content_ids = []

    # Reserve IDs: font=1, pages root=2, catalog=3; page/content pairs start at 4.
    next_id = 4
    for _ in pages:
        page_ids.append(next_id)
        content_ids.append(next_id + 1)
        next_id += 2

    for page_index, page_lines in enumerate(pages):
        page_id = page_ids[page_index]
        content_id = content_ids[page_index]
        page_obj = (
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] '
            f'/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>'
        )
        commands = ['BT', '/F1 8 Tf', '30 560 Td', '11 TL']
        for line in page_lines:
            text = _pdf_escape(line)
            # Keep each row within a landscape A4 line.
            if len(text) > 170:
                text = text[:167] + '...'
            commands.append(f'({text}) Tj')
            commands.append('T*')
        commands.append('ET')
        stream = '\n'.join(commands).encode('latin-1', errors='replace')
        content_obj = f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream'
        objects.append((page_id, page_obj.encode()))
        objects.append((content_id, content_obj))

    kids = ' '.join(f'{pid} 0 R' for pid in page_ids)
    fixed = {
        1: objects[0].encode(),
        2: f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode(),
        3: b'<< /Type /Catalog /Pages 2 0 R >>',
    }
    for item in objects[1:]:
        fixed[item[0]] = item[1]

    buffer = BytesIO()
    buffer.write(b'%PDF-1.4\n')
    offsets = [0]
    for obj_id in range(1, next_id):
        offsets.append(buffer.tell())
        buffer.write(f'{obj_id} 0 obj\n'.encode())
        buffer.write(fixed[obj_id])
        buffer.write(b'\nendobj\n')
    xref = buffer.tell()
    buffer.write(f'xref\n0 {next_id}\n'.encode())
    buffer.write(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        buffer.write(f'{offset:010d} 00000 n \n'.encode())
    buffer.write(f'trailer\n<< /Size {next_id} /Root 3 0 R >>\nstartxref\n{xref}\n%%EOF'.encode())
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
    summary = {'total_records': 0, 'total_amount': None}

    if report_type == 'patients':
        qs = Patient.objects.select_related('user').order_by('-created_at', '-id')
        if start_date: qs = qs.filter(created_at__date__gte=start_date)
        if end_date: qs = qs.filter(created_at__date__lte=end_date)
        if search:
            qs = qs.filter(Q(patient_id__icontains=search) | Q(user__first_name__icontains=search) |
                           Q(user__last_name__icontains=search) | Q(user__email__icontains=search) |
                           Q(phone__icontains=search))
        headers = ['Patient ID', 'Patient Name', 'Email', 'Phone', 'Created At']
        rows = [[p.patient_id, p.user.get_full_name() or '-', p.user.email, p.phone or '-', p.created_at.strftime('%d-%m-%Y')] for p in qs]

    elif report_type == 'appointments':
        qs = Appointment.objects.select_related('patient__user', 'doctor__user').order_by('-appointment_date', '-id')
        if start_date: qs = qs.filter(appointment_date__gte=start_date)
        if end_date: qs = qs.filter(appointment_date__lte=end_date)
        if status: qs = qs.filter(status=status)
        if department: qs = qs.filter(department=department)
        if doctor_id: qs = qs.filter(doctor_id=doctor_id)
        if search:
            qs = qs.filter(Q(patient__patient_id__icontains=search) | Q(patient__user__first_name__icontains=search) |
                           Q(patient__user__last_name__icontains=search) | Q(doctor__user__first_name__icontains=search) |
                           Q(doctor__user__last_name__icontains=search) | Q(reason__icontains=search))
        headers = ['Patient', 'Doctor', 'Department', 'Date', 'Time', 'Visit Type', 'Status']
        rows = [[a.patient.user.get_full_name() or a.patient.patient_id,
                 f'Dr. {a.doctor.user.get_full_name()}', DEPARTMENT_LABELS.get(a.department, a.department),
                 a.appointment_date.strftime('%d-%m-%Y'), a.time_slot, a.get_visit_type_display(), a.get_status_display()] for a in qs]

    elif report_type == 'doctors':
        qs = Doctor.objects.select_related('user').order_by('user__first_name', 'id')
        if department: qs = qs.filter(department=department)
        if search:
            qs = qs.filter(Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) |
                           Q(user__email__icontains=search) | Q(specialization__icontains=search) |
                           Q(qualification__icontains=search))
        headers = ['Doctor Name', 'Department', 'Specialization', 'Qualification', 'Experience', 'Fee']
        rows = [[f'Dr. {d.user.get_full_name()}', d.get_department_display(), d.specialization or '-',
                 d.qualification or '-', f'{d.experience_years} years', d.consultation_fee] for d in qs]

    elif report_type == 'billing':
        qs = Billing.objects.select_related('patient__user', 'appointment__doctor__user').order_by('-created_at', '-id')
        if start_date: qs = qs.filter(appointment__appointment_date__gte=start_date)
        if end_date: qs = qs.filter(appointment__appointment_date__lte=end_date)
        if status: qs = qs.filter(status=status)
        if department: qs = qs.filter(appointment__department=department)
        if doctor_id: qs = qs.filter(appointment__doctor_id=doctor_id)
        if bill_type: qs = qs.filter(bill_type=bill_type)
        if search:
            qs = qs.filter(Q(patient__patient_id__icontains=search) | Q(patient__user__first_name__icontains=search) |
                           Q(patient__user__last_name__icontains=search) | Q(appointment__doctor__user__first_name__icontains=search) |
                           Q(appointment__doctor__user__last_name__icontains=search))
        total_amount = qs.aggregate(total=Sum('amount'))['total'] or 0
        summary['total_amount'] = total_amount
        headers = ['Patient', 'Patient ID', 'Bill Type', 'Doctor', 'Date', 'Amount', 'Status']
        rows = [[b.patient.user.get_full_name() or '-', b.patient.patient_id, b.get_bill_type_display(),
                 f'Dr. {b.appointment.doctor.user.get_full_name()}', b.appointment.appointment_date.strftime('%d-%m-%Y'),
                 f'Rs. {b.amount}', b.get_status_display()] for b in qs]
    else:
        messages.error(request, 'Invalid report type.')
        return redirect('generate_report')

    summary['total_records'] = len(rows)
    filter_parts = []
    if start_date or end_date: filter_parts.append(f'Date: {start_date or "Any"} to {end_date or "Any"}')
    if status: filter_parts.append(f'Status: {status}')
    if department: filter_parts.append(f'Department: {DEPARTMENT_LABELS.get(department, department)}')
    if doctor_id:
        doctor = doctors_for_filter.filter(id=doctor_id).first()
        if doctor: filter_parts.append(f'Doctor: Dr. {doctor.user.get_full_name()}')
    if bill_type: filter_parts.append(f'Bill type: {dict(Billing.BILL_TYPE_CHOICES).get(bill_type, bill_type)}')
    if search: filter_parts.append(f'Search: {search}')
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
        pdf = _simple_pdf(f'HMS - {report_type.title()} Report', headers, rows, filter_summary)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        return response

    context = {**base_context, 'headers': headers, 'rows': rows, 'total_records': len(rows),
               'total_amount': summary['total_amount'], 'filter_summary': filter_summary}
    return render(request, 'adminpanel/report_result.html', context)
