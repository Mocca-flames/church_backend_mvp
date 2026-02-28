from __future__ import annotations

import io
import os
from datetime import datetime
from typing import List, Dict, Any
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Brand Palette ────────────────────────────────────────────────────────────
NAVY        = colors.HexColor('#1A2B4A')   # deep navy  – headers / accents
GOLD        = colors.HexColor('#C9A84C')   # warm gold  – accent stripe
LIGHT_BLUE  = colors.HexColor('#EAF0F8')   # pale blue  – alternating row
WHITE       = colors.white
GREY_TEXT   = colors.HexColor('#4A4A4A')
BORDER      = colors.HexColor('#C5CDD8')
# ─────────────────────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm   # breathing room on each side
TABLE_W = PAGE_W - 2 * MARGIN


def extract_location_from_tags(tags: List[str]) -> str:
    valid_locations = {'kanana', 'majaneng', 'mashemong', 'soshanguve', 'kekana'}
    if not tags:
        return ''
    for tag in tags:
        if tag.lower() in valid_locations:
            return tag.capitalize()
    return ''


def is_member(tags: List[str]) -> bool:
    if not tags:
        return False
    return 'member' in [tag.lower() for tag in tags]


def get_contact_tags(contact) -> List[str]:
    if hasattr(contact, 'tags') and contact.tags:
        return contact.tags
    if hasattr(contact, 'metadata_') and contact.metadata_:
        try:
            metadata = json.loads(contact.metadata_)
            return metadata.get('tags', [])
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def format_phone_for_display(phone: str) -> str:
    if not phone:
        return ''
    phone = phone.strip()
    if phone.startswith('+27'):
        phone = phone[3:]
    elif phone.startswith('27') and len(phone) > 10:
        phone = phone[2:]
    if len(phone) == 9 and phone[0] in ['7', '8', '9']:
        return f"0{phone[:2]} {phone[2:5]} {phone[5:]}"
    if phone.startswith('0') and len(phone) >= 10:
        return f"{phone[:3]} {phone[3:6]} {phone[6:]}"
    return phone


# ── Custom canvas for header/footer on every page ────────────────────────────
def _make_page_decorator(logo_path: str | None, total_records: int, date_str: str = None, service_type_str: str = None):
    """Returns an onFirstPage / onLaterPages callable."""

    def draw_page(canvas, doc):
        canvas.saveState()
        w, h = A4

        # ── Top accent bar (gold stripe) ──────────────────────────────────
        bar_h = 5
        canvas.setFillColor(GOLD)
        canvas.rect(0, h - bar_h, w, bar_h, fill=1, stroke=0)

        # ── Header area ───────────────────────────────────────────────────
        header_top = h - bar_h
        header_bottom = h - 32 * mm

        canvas.setFillColor(NAVY)
        canvas.rect(0, header_bottom, w, header_top - header_bottom, fill=1, stroke=0)

        # Logo (left side)
        if logo_path and os.path.exists(logo_path):
            try:
                logo_w = 42 * mm
                logo_h = 22 * mm
                canvas.drawImage(
                    logo_path,
                    MARGIN, header_bottom + (header_top - header_bottom - logo_h) / 2,
                    width=logo_w, height=logo_h,
                    preserveAspectRatio=True, mask='auto'
                )
            except Exception:
                pass  # Logo failed gracefully

        # Title text (right side of header)
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 18)
        canvas.drawRightString(w - MARGIN, header_bottom + 22 * mm, "Fountain of Prayer Ministries Attendance")

        # Date and Service Type (below title, on right side)
        canvas.setFillColor(GOLD)
        canvas.setFont('Helvetica', 10)
        
        # Build the header info string
        if date_str and service_type_str:
            header_info = f"{date_str} | {service_type_str}"
        elif date_str:
            header_info = date_str
        elif service_type_str:
            header_info = service_type_str
        else:
            # Default: current date
            header_info = datetime.now().strftime('%d %B %Y')
        
        canvas.drawRightString(w - MARGIN, header_bottom + 14 * mm, header_info)

        # ── Thin gold rule below header ───────────────────────────────────
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(MARGIN, header_bottom - 2 * mm, w - MARGIN, header_bottom - 2 * mm)

        # ── Footer ────────────────────────────────────────────────────────
        footer_y = 10 * mm
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, footer_y + 5 * mm, w - MARGIN, footer_y + 5 * mm)

        canvas.setFillColor(GREY_TEXT)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(MARGIN, footer_y, f"Total Records: {total_records}")
        canvas.drawRightString(
            w - MARGIN, footer_y,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    return draw_page


def generate_attendance_pdf(
    attendances: List[Any],
    logo_path: str = "assets/logo.png",   # ← point this at your actual logo file
    date_str: str = None,
    service_type_str: str = None
) -> bytes:
    """Generate a polished attendance PDF.

    Args:
        attendances : List of Attendance ORM objects with .contact relationship.
        logo_path   : Path to logo.png (absolute or relative to cwd).
        date_str    : Date string for header (e.g., "21 February 2026" or "21 February 2026 - 26 March 2026")
        service_type_str : Service type string for header (e.g., "Sunday Service" or "Sunday Services only")

    Returns:
        PDF bytes.
    """
    import logging
    logger = logging.getLogger(__name__)

    # ── Collect row data ──────────────────────────────────────────────────────
    data = []
    for att in attendances:
        contact = att.contact
        tags    = get_contact_tags(contact)
        location = extract_location_from_tags(tags)
        member   = 'Yes' if is_member(tags) else 'No'
        name     = contact.name if contact.name else contact.phone
        phone    = format_phone_for_display(contact.phone)

        logger.debug(f"[PDF] name={name} location={location} phone={phone} member={member}")
        data.append({
            'name': name,
            'location': location or 'N/A',
            'phone': phone,
            'member': member
        })

    total = len(data)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    buffer = io.BytesIO()

    # Top margin must clear the custom header (≈52 mm) + rule (2 mm) + gap
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=36 * mm,    # clears the painted header
        bottomMargin=22 * mm, # clears the painted footer
    )

    page_fn = _make_page_decorator(logo_path, total, date_str, service_type_str)

    styles  = getSampleStyleSheet()

    # ── Table ─────────────────────────────────────────────────────────────────
    col_widths = [
        TABLE_W * 0.35,   # Name
        TABLE_W * 0.22,   # Location
        TABLE_W * 0.28,   # Phone
        TABLE_W * 0.15,   # Member
    ]

    header_para_style = ParagraphStyle(
        'TH',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=WHITE,
        leading=14,
    )
    cell_style = ParagraphStyle(
        'TD',
        fontName='Helvetica',
        fontSize=12,
        textColor=GREY_TEXT,
        leading=15,
    )

    headers = ['Name', 'Location', 'Phone', 'Member']
    table_data = [[Paragraph(h, header_para_style) for h in headers]]

    for row in data:
        table_data.append([
            Paragraph(row['name'],     cell_style),
            Paragraph(row['location'], cell_style),
            Paragraph(row['phone'],    cell_style),
            Paragraph(row['member'],   cell_style),
        ])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # ── Header ────────────────────────────────────────────────────────
        ('BACKGROUND',    (0, 0), (-1, 0),  NAVY),
        ('TOPPADDING',    (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  10),
        ('LEFTPADDING',   (0, 0), (-1, 0),  10),
        ('RIGHTPADDING',  (0, 0), (-1, 0),  10),

        # Left border accent on header
        ('LINEAFTER',     (0, 0), (0, 0),   1.5, GOLD),

        # ── Data rows ─────────────────────────────────────────────────────
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ('TOPPADDING',    (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 9),
        ('LEFTPADDING',   (0, 1), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 1), (-1, -1), 10),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),

        # ── Grid ──────────────────────────────────────────────────────────
        ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.5, GOLD),   # gold rule under header

        # ── "Member" column – colour-coded text via per-cell override ─────
        # (done via Python loop below)
    ]))

    # Colour-code the Member column
    for i, row in enumerate(data, start=1):
        color = colors.HexColor('#1E7B4B') if row['member'] == 'Yes' else colors.HexColor('#B03A2E')
        tbl.setStyle(TableStyle([
            ('TEXTCOLOR', (3, i), (3, i), color),
            ('FONTNAME',  (3, i), (3, i), 'Helvetica-Bold'),
        ]))

    elements = [tbl]

    doc.build(elements, onFirstPage=page_fn, onLaterPages=page_fn)
    return buffer.getvalue()