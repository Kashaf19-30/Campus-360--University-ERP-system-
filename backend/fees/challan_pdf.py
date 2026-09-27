"""Semester fee challan PDF for enrolled students."""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

UNIVERSITY_NAME = 'Campus360 University'


def build_semester_challan_payload(challan) -> dict:
    student = challan.student
    program = student.program
    return {
        'challan_number': challan.challan_number,
        'student_name': student.user.username,
        'registration_number': student.registration_number,
        'program_name': program.program_name,
        'program_code': program.program_code,
        'semester_name': challan.semester.semester_name,
        'amount_display': f'Rs. {Decimal(challan.total_amount):,.2f}',
        'due_date': challan.due_date.isoformat() if challan.due_date else '',
        'issue_date': (challan.issue_date or date.today()).isoformat(),
        'status': challan.status,
    }


def generate_semester_challan_pdf(challan) -> bytes:
    payload = build_semester_challan_payload(challan)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f'<b>{UNIVERSITY_NAME}</b>', styles['Title']),
        Paragraph('Semester Fee Challan', styles['Heading2']),
        Spacer(1, 12),
    ]
    rows = [
        ['Challan No.', payload['challan_number']],
        ['Student', payload['student_name']],
        ['Registration No.', payload['registration_number']],
        ['Program', f"{payload['program_name']} ({payload['program_code']})"],
        ['Semester', payload['semester_name']],
        ['Amount', payload['amount_display']],
        ['Issue Date', payload['issue_date']],
        ['Due Date', payload['due_date']],
    ]
    table = Table(rows, colWidths=[45 * mm, 120 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2ff')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        '<b>Instructions:</b> Pay at the university finance office. '
        'Finance will confirm payment in the system — no upload required.',
        styles['Normal'],
    ))
    doc.build(story)
    return buffer.getvalue()
