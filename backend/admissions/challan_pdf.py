"""
Generate admission fee challan PDF with applicant and program details.
"""
from __future__ import annotations

import io
from decimal import Decimal
from datetime import date, timedelta


UNIVERSITY_NAME = 'Campus360 University'
UNIVERSITY_TAGLINE = 'Excellence in Education'
ADMISSION_FEE_LABEL = 'Admission Fee'


def _fmt_amount(amount) -> str:
    val = Decimal(str(amount))
    return f'Rs. {val:,.2f}'


def build_challan_payload(application, applicant) -> dict:
    from admissions.models import ProgramPreference

    issue = application.submitted_at.date() if application.submitted_at else date.today()
    due = issue + timedelta(days=14)
    amount = application.admission_challan_amount or Decimal('15000')

    preferences = ProgramPreference.objects.filter(
        application=application,
    ).select_related('program', 'program__department').order_by('preference_order')

    preferences_list = [
        {
            'order': p.preference_order,
            'program_name': p.program.program_name,
            'program_code': p.program.program_code,
            'department_name': p.program.department.department_name if p.program.department_id else '—',
        }
        for p in preferences
    ]

    return {
        'university_name': UNIVERSITY_NAME,
        'university_tagline': UNIVERSITY_TAGLINE,
        'challan_number': application.admission_challan_number,
        'application_number': application.application_number,
        'applicant_name': f'{applicant.first_name} {applicant.last_name}'.strip(),
        'father_name': applicant.father_name or '—',
        'cnic': applicant.cnic or '—',
        'phone': applicant.phone or '—',
        'email': applicant.user.email if applicant.user_id else '—',
        'program_name': application.program.program_name if application.program_id else '—',
        'program_code': application.program.program_code if application.program_id else '—',
        'department_name': (
            application.program.department.department_name
            if application.program_id and application.program.department_id else '—'
        ),
        'degree_level': application.program.degree_level if application.program_id else '—',
        'fee_label': ADMISSION_FEE_LABEL,
        'amount': amount,
        'amount_display': _fmt_amount(amount),
        'issue_date': issue.isoformat(),
        'due_date': due.isoformat(),
        'preferences': preferences_list,
        'is_admission_challan': True,
        'instructions': [
            'This is your admission fee challan.',
            'Pay the amount at the university finance office.',
            'Finance will confirm payment in the system — no upload required.',
            'Keep your challan number for reference.',
        ],
    }


def _pdf_cell(text, style) -> 'Paragraph':
    from reportlab.platypus import Paragraph
    safe = str(text or '—').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(safe, style)


def generate_challan_pdf(payload: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    usable_w = doc.width

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ChallanTitle', parent=styles['Heading1'],
        fontSize=16, textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=4, alignment=1,
    )
    sub_style = ParagraphStyle(
        'ChallanSub', parent=styles['Normal'],
        fontSize=10, textColor=colors.grey, alignment=1, spaceAfter=12,
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        fontSize=11, textColor=colors.HexColor('#1e40af'), spaceBefore=8, spaceAfter=6,
    )
    normal = styles['Normal']
    cell_style = ParagraphStyle(
        'Cell', parent=normal, fontSize=8.5, leading=11, wordWrap='CJK',
    )
    label_style = ParagraphStyle(
        'CellLabel', parent=cell_style, fontName='Helvetica-Bold',
    )

    def label(text):
        return _pdf_cell(text, label_style)

    def value(text):
        return _pdf_cell(text, cell_style)

    label_w = usable_w * 0.24
    value_w = usable_w * 0.26
    four_col = [label_w, value_w, label_w, value_w]

    story = [
        Paragraph(payload['university_name'], title_style),
        Paragraph(payload['university_tagline'], sub_style),
        Paragraph('<b>ADMISSION FEE CHALLAN</b>', ParagraphStyle(
            'Banner', parent=normal, fontSize=13, alignment=1,
            backColor=colors.HexColor('#eff6ff'), borderPadding=8, spaceAfter=14,
        )),
    ]

    meta_rows = [
        [label('Challan No.'), value(payload['challan_number']), label('Application No.'), value(payload['application_number'])],
        [label('Issue Date'), value(payload['issue_date']), label('Due Date'), value(payload['due_date'])],
    ]
    meta_table = Table(meta_rows, colWidths=four_col, repeatRows=0)
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph('Applicant Details', section_style))
    applicant_rows = [
        [label('Full Name'), value(payload['applicant_name']), label('Father Name'), value(payload['father_name'])],
        [label('CNIC'), value(payload['cnic']), label('Phone'), value(payload['phone'])],
        [label('Email'), value(payload['email']), label('Fee Type'), value(payload['fee_label'])],
    ]
    app_table = Table(applicant_rows, colWidths=four_col)
    app_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(app_table)
    story.append(Spacer(1, 10))

    prefs = payload.get('preferences') or []
    if prefs:
        story.append(Paragraph('Program Preferences', section_style))
        pref_rows = [[label('Order'), label('Program'), label('Code'), label('Department')]]
        for p in prefs:
            pref_rows.append([
                value(str(p.get('order', ''))),
                value(p.get('program_name', '')),
                value(p.get('program_code', '')),
                value(p.get('department_name', '')),
            ])
        pref_table = Table(pref_rows, colWidths=four_col)
        pref_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef2ff')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(pref_table)
        story.append(Spacer(1, 10))

    amount_table = Table(
        [[Paragraph(
            f'<b>Amount Payable:</b> {payload["amount_display"]}',
            ParagraphStyle('Amount', parent=normal, fontSize=14, alignment=1, textColor=colors.white),
        )]],
        colWidths=[usable_w],
    )
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1e3a8a')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(amount_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph('Instructions', section_style))
    instr_style = ParagraphStyle('Instr', parent=normal, fontSize=9, leading=12, spaceAfter=4)
    for line in payload['instructions']:
        story.append(Paragraph(f'• {line}', instr_style))

    story.append(Spacer(1, 12))
    sig_w = usable_w / 2
    sig_table = Table([
        [label('Applicant Signature'), label('Finance Office')],
        ['', ''],
    ], colWidths=[sig_w, sig_w], rowHeights=[10 * mm, 20 * mm])
    sig_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()
