import io
from datetime import datetime
from typing import List, Dict, Any
import json

from reportlab.lib import colors # type: ignore
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def extract_location_from_tags(tags: List[str]) -> str:
    """Extract location from tags, excluding 'member' tag.
    
    Valid locations: kanana, majaneng, mashemong, soshanguve, kekana
    """
    valid_locations = {'kanana', 'majaneng', 'mashemong', 'soshanguve', 'kekana'}
    
    if not tags:
        return ''
    
    for tag in tags:
        if tag.lower() in valid_locations:
            return tag.capitalize()
    
    return ''


def is_member(tags: List[str]) -> bool:
    """Check if tags contain 'member'"""
    if not tags:
        return False
    return 'member' in [tag.lower() for tag in tags]


def get_contact_tags(contact) -> List[str]:
    """Extract tags from contact model.
    
    Handles both the Contact schema (which has tags attribute) 
    and raw SQLAlchemy models (which have metadata_).
    """
    # If contact has tags attribute (from schema)
    if hasattr(contact, 'tags') and contact.tags:
        return contact.tags
    
    # If contact has metadata_ (raw SQLAlchemy model)
    if hasattr(contact, 'metadata_') and contact.metadata_:
        try:
            metadata = json.loads(contact.metadata_)
            return metadata.get('tags', [])
        except (json.JSONDecodeError, TypeError):
            return []
    
    return []


def format_phone_for_display(phone: str) -> str:
    """Format phone number for human-readable display.
    
    Converts +27XXXXXXXXX to 0XX XXX XXXX format.
    Examples:
        +27712345678 -> 071 234 5678
        +27811234567 -> 081 123 4567
    """
    if not phone:
        return ''
    
    # Remove any whitespace
    phone = phone.strip()
    
    # Remove +27 prefix if present (South African format)
    if phone.startswith('+27'):
        phone = phone[3:]  # Remove +27
    # Remove 27 prefix if present
    elif phone.startswith('27') and len(phone) > 10:
        phone = phone[2:]
    
    # Now we should have a 9-digit number starting with 7, 8, or 9
    # Add leading 0 and format with spaces
    if len(phone) == 9 and phone[0] in ['7', '8', '9']:
        # Format as 0XX XXX XXXX (add 0 prefix)
        return f"0{phone[:2]} {phone[2:5]} {phone[5:]}"
    
    # If already has leading 0, format with spaces
    if phone.startswith('0') and len(phone) >= 10:
        # Format as 0XX XXX XXXX
        return f"{phone[:3]} {phone[3:6]} {phone[6:]}"
    
    # Return original if we can't format it
    return phone


def generate_attendance_pdf(attendances: List[Any]) -> bytes:
    """Generate PDF with attendance data.
    
    Args:
        attendances: List of Attendance objects with contact relationship
        
    Returns:
        PDF bytes
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Extract data from attendances
    data = []
    for att in attendances:
        contact = att.contact
        
        logger.warning(f"[PDF EXPORT] Processing attendance ID={att.id}, contact={contact}")
        
        # Get tags from contact
        tags = get_contact_tags(contact)
        logger.warning(f"[PDF EXPORT] Contact ID={getattr(contact, 'id', None)} tags={tags}")
        
        # Extract location (excluding 'member')
        location = extract_location_from_tags(tags)
        
        # Check if member
        member = 'Yes' if is_member(tags) else 'No'
        
        # Get name (fallback to phone if name is None)
        name = contact.name if contact.name else contact.phone
        
        # Format phone number for display
        display_phone = format_phone_for_display(contact.phone)
        
        logger.warning(f"[PDF EXPORT] Row: name={name}, location={location}, phone={display_phone}, member={member}")
        
        data.append({
            'name': name,
            'location': location or 'N/A',
            'phone': display_phone,
            'member': member
        })
    
    # Create PDF document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=12,
    )
    
    # Add title
    elements.append(Paragraph("Church Attendance Report", title_style))
    
    # Add generation date
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 20))
    
    # Create table data (with header)
    table_data = [['Name', 'Location', 'Phone', 'Member']]
    for row in data:
        table_data.append([
            row['name'],
            row['location'],
            row['phone'],
            row['member']
        ])
    
    # Create and style table
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECF0F1')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ECF0F1'), colors.white]),
    ]))
    
    elements.append(table)
    
    # Add summary
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Total Records: {len(data)}",
        styles['Normal']
    ))
    
    # Build PDF
    doc.build(elements)
    
    return buffer.getvalue()
