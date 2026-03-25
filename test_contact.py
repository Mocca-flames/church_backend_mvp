#!/usr/bin/env python3
"""
Test script to diagnose 400 Bad Request errors on contacts API endpoints.
This helps identify why external apps are stuck in sync.
"""

import requests
import json

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


def test_post_contacts(token):
    """Test POST /contacts to see the actual error response"""
    print("\n" + "="*60)
    print("TESTING: POST /contacts")
    print("="*60)
    
    # Test 1: Valid data
    valid_data = {
        "name": "Test User",
        "phone": "+27831234567",
        "status": "active",
        "opt_out_sms": False,
        "opt_out_whatsapp": False,
        "tags": ["member"]
    }
    
    print("\n1. Testing with valid data:")
    print(f"   Payload: {json.dumps(valid_data, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/contacts",
        json=valid_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test 2: Missing required fields
    print("\n2. Testing with missing name:")
    missing_name = {
        "phone": "+27831234567",
        "status": "active"
    }
    response = requests.post(
        f"{BASE_URL}/contacts",
        json=missing_name,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test 3: Missing phone
    print("\n3. Testing with missing phone:")
    missing_phone = {
        "name": "Test User",
        "status": "active"
    }
    response = requests.post(
        f"{BASE_URL}/contacts",
        json=missing_phone,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test 4: Invalid phone format
    print("\n4. Testing with invalid phone format:")
    invalid_phone = {
        "name": "Test User",
        "phone": "invalid-phone",
        "status": "active"
    }
    response = requests.post(
        f"{BASE_URL}/contacts",
        json=invalid_phone,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test 5: Duplicate contact (existing phone)
    print("\n5. Testing with duplicate phone (existing contact):")
    duplicate = {
        "name": "Another Test",
        "phone": "+27831234567",  # Same as test 1
        "status": "active"
    }
    response = requests.post(
        f"{BASE_URL}/contacts",
        json=duplicate,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")


def test_put_contacts(token, contact_id=3111):
    """Test PUT /contacts/{id} to see the actual error response"""
    print("\n" + "="*60)
    print(f"TESTING: PUT /contacts/{contact_id}")
    print("="*60)
    
    # First, let's try to get the contact to see if it exists
    print(f"\n1. First, checking if contact {contact_id} exists:")
    response = requests.get(
        f"{BASE_URL}/contacts?skip=0&limit=1",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        contacts = response.json()
        print(f"   Total contacts available: {len(contacts)}")
        if contacts:
            print(f"   First contact ID: {contacts[0].get('id')}")
    
    # Test PUT with valid data
    print(f"\n2. Testing PUT with valid data:")
    valid_data = {
        "name": "Updated Name",
        "phone": "+27831234567",
        "status": "active",
        "opt_out_sms": False,
        "opt_out_whatsapp": False,
        "tags": ["member", "updated"]
    }
    print(f"   Payload: {json.dumps(valid_data, indent=2)}")
    
    response = requests.put(
        f"{BASE_URL}/contacts/{contact_id}",
        json=valid_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test PUT with missing required fields
    print(f"\n3. Testing PUT with missing name:")
    missing_name = {
        "phone": "+27831234567",
        "status": "active"
    }
    response = requests.put(
        f"{BASE_URL}/contacts/{contact_id}",
        json=missing_name,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.text}")


def get_recent_contacts(token):
    """Get recent contacts to see what data format is being used"""
    print("\n" + "="*60)
    print("GETTING RECENT CONTACTS (to see actual data format)")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/contacts?limit=5&skip=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        contacts = response.json()
        print(f"\nFound {len(contacts)} contacts")
        for i, contact in enumerate(contacts):
            print(f"\n--- Contact {i+1} ---")
            print(json.dumps(contact, indent=2))
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    print("Testing Church Contact API Endpoints")
    print("="*60)
    
    try:
        # Login
        token = login()
        print("Logged in successfully")
        
        # Get recent contacts to see the data format
        get_recent_contacts(token)
        
        # Test POST /contacts
        test_post_contacts(token)
        
        # Test PUT /contacts/3111
        test_put_contacts(token, 3111)
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
