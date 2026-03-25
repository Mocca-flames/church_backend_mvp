#!/usr/bin/env python3
"""
Script to get new or modified contacts for a given date.
Default date is today's date.

Usage:
    python get_new_or_modified_contacts.py
    python get_new_or_modified_contacts.py 2025-03-25
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://35.238.27.155:8000"
USERNAME = "junior13@driver.com"
PASSWORD = "Maurice@12!"


def login():
    """Login to get access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_new_or_modified_contacts(token, date_str=None):
    """
    Get contacts that were created or modified on the given date.
    
    Args:
        token: Authentication token
        date_str: Date string in YYYY-MM-DD format. Defaults to today's date.
    
    Returns:
        Dictionary with new_contacts, modified_contacts, and all_new_or_modified
    """
    # Parse the date or use today's date
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        target_date = datetime.now()
    
    # Start of the day
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # End of the day
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
    
    print(f"\nSearching for contacts created or modified on: {start_of_day.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    # Get contacts created after start_of_day
    print("\n1. Fetching NEW contacts (created after start of day)...")
    response = requests.get(
        f"{BASE_URL}/contacts",
        params={"created_after": start_of_day.isoformat(), "limit": 6000},
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    new_contacts = response.json()
    print(f"   Found {len(new_contacts)} new contacts")
    
    # Get contacts updated after start_of_day
    print("\n2. Fetching MODIFIED contacts (updated after start of day)...")
    response = requests.get(
        f"{BASE_URL}/contacts",
        params={"updated_after": start_of_day.isoformat(), "limit": 6000},
        headers={"Authorization": f"Bearer {token}"}
    )
    response.raise_for_status()
    modified_contacts = response.json()
    print(f"   Found {len(modified_contacts)} modified contacts")
    
    # Combine and deduplicate
    all_contacts = {}
    for contact in new_contacts:
        all_contacts[contact['id']] = {**contact, 'change_type': 'new'}
    for contact in modified_contacts:
        if contact['id'] in all_contacts:
            all_contacts[contact['id']]['change_type'] = 'new_and_modified'
        else:
            all_contacts[contact['id']] = {**contact, 'change_type': 'modified'}
    
    all_new_or_modified = list(all_contacts.values())
    
    return {
        'new_contacts': new_contacts,
        'modified_contacts': modified_contacts,
        'all_new_or_modified': all_new_or_modified
    }


def print_contacts(contacts, title):
    """Pretty print contacts"""
    print(f"\n{title}")
    print("-" * 40)
    if not contacts:
        print("  No contacts found")
        return
    
    for contact in contacts:
        created = contact.get('created_at', 'N/A')
        updated = contact.get('updated_at', 'N/A')
        name = contact.get('name', 'N/A')
        phone = contact.get('phone', 'N/A')
        status = contact.get('status', 'active')
        tags = contact.get('tags', [])
        
        print(f"  ID: {contact['id']}")
        print(f"    Name: {name}")
        print(f"    Phone: {phone}")
        print(f"    Status: {status}")
        print(f"    Tags: {', '.join(tags) if tags else 'None'}")
        print(f"    Created: {created}")
        print(f"    Updated: {updated}")
        print()


if __name__ == "__main__":
    # Get date from command line argument or use today's date
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("Church Contact API - Get New or Modified Contacts")
    print("=" * 60)
    
    try:
        # Login
        token = login()
        print("Logged in successfully")
        
        # Get new or modified contacts
        result = get_new_or_modified_contacts(token, date_arg)
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total NEW contacts: {len(result['new_contacts'])}")
        print(f"Total MODIFIED contacts: {len(result['modified_contacts'])}")
        print(f"Total NEW or MODIFIED: {len(result['all_new_or_modified'])}")
        
        # Print details
        print_contacts(result['new_contacts'], "NEW CONTACTS")
        print_contacts(result['modified_contacts'], "MODIFIED CONTACTS (excluding new)")
        
        # Print combined list
        print_contacts(result['all_new_or_modified'], "ALL NEW OR MODIFIED CONTACTS")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
