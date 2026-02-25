#!/usr/bin/env python3
"""
Test script to generate sample PDF with random attendance data.
Run this to test the PDF layout and design.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import random


# Mock Contact class for testing
class MockContact:
    def __init__(self, id, name, phone, tags):
        self.id = id
        self.name = name
        self.phone = phone
        self.tags = tags
        self.metadata_ = None


# Mock Attendance class for testing
class MockAttendance:
    def __init__(self, id, contact, service_type, service_date):
        self.id = id
        self.contact = contact
        self.service_type = service_type
        self.service_date = service_date


# Sample data
first_names = [
    "John", "Mary", "Peter", "Sarah", "Joseph", "Grace", "David", "Elizabeth",
    "Michael", "Ruth", "James", "Hannah", "William", "Esther", "Robert", "Rebecca",
    "Thomas", "Rachel", "Charles", "Naomi", "Daniel", "Deborah", "Matthew", " Leah"
]

last_names = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin"
]

locations = ["kanana", "majaneng", "mashemong", "soshanguve", "kekana"]
service_types = ["Sunday", "Tuesday", "Wednesday", "Friday", "Special Event"]


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


def generate_mock_attendances(count=25):
    """Generate mock attendance data for testing"""
    attendances = []
    
    for i in range(count):
        # Random first and last name
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        name = f"{first_name} {last_name}"
        
        # Random phone number (South African format: +27 71 234 5678 = +27712345678)
        # Generate: +27 + 9 digits starting with 7, 8, or 9
        first = random.choice(['7', '8', '9'])
        rest = f"{random.randint(10000000, 99999999)}"  # 8 more digits
        full_number = f"{first}{rest}"  # 9 digit number like 712345678
        phone = f"+27{full_number}"  # +27712345678
        
        # Random location (80% chance of having one)
        tags = []
        if random.random() < 0.8:
            tags.append(random.choice(locations))
        
        # Random member status (70% chance of being a member)
        if random.random() < 0.7:
            tags.append("member")
        
        # Create mock contact
        contact = MockContact(
            id=i+1,
            name=name,
            phone=phone,
            tags=tags
        )
        
        # Random service date within last 30 days
        days_ago = random.randint(0, 30)
        service_date = datetime.now() - timedelta(days=days_ago)
        
        # Create mock attendance
        attendance = MockAttendance(
            id=i+1,
            contact=contact,
            service_type=random.choice(service_types),
            service_date=service_date
        )
        
        attendances.append(attendance)
    
    return attendances


def test_pdf_generation():
    """Test PDF generation with mock data"""
    print("Generating test PDF with sample data...")
    
    # Import the PDF service
    from app.services.pdf_service import generate_attendance_pdf
    
    # Generate mock attendances
    attendances = generate_mock_attendances(30)
    
    print(f"\nGenerated {len(attendances)} sample attendance records:")
    print("-" * 80)
    
    for att in attendances[:5]:  # Show first 5
        tags = att.contact.tags
        location = [t for t in tags if t not in ['member', 'member']][0] if any(t not in ['member'] for t in tags) else 'N/A'
        is_member = 'Yes' if 'member' in tags else 'No'
        formatted_phone = format_phone_for_display(att.contact.phone)
        print(f"  {att.contact.name:25s} | {location:12s} | {att.contact.phone:20s} -> {formatted_phone:15s} | Member: {is_member}")
    
    print(f"  ... and {len(attendances) - 5} more records")
    print("-" * 80)
    
    # Generate PDF
    pdf_bytes = generate_attendance_pdf(attendances)
    
    # Save to file
    output_path = "test_attendance_export.pdf"
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"\n✅ PDF generated successfully!")
    print(f"   Output file: {output_path}")
    print(f"   File size: {len(pdf_bytes):,} bytes")
    
    return output_path


if __name__ == "__main__":
    test_pdf_generation()
