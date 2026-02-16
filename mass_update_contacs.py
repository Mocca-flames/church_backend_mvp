#!/usr/bin/env python3
"""
Script to add contacts from a batch file to the system.
"""

import requests
import json
from typing import List, Dict, Any

# Configuration - copied from fetch_contacts.py
BASE_URL = "http://localhost:8000"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"
CONTACTS_DATA_FILE = "phone_data.json"
CONTACTS_ADD_LIST_URL = f"{BASE_URL}/contacts/add-list"

def login() -> str:
    """Login to the system and return the access token"""
    login_url = f"{BASE_URL}/auth/login"
    login_data = {
        "username": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    }

    try:
        response = requests.post(login_url, data=login_data)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError("Login successful but no access token received")

        print("Login successful!")
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        raise

def read_contacts(filename: str) -> List[Dict[str, Any]]:
    """Read contacts from a JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            contacts = json.load(f)
        print(f"Read {len(contacts)} contacts from {filename}")
        return contacts
    except FileNotFoundError:
        print(f"Error: File not found at {filename}")
        raise
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filename}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        raise

def extract_tags_from_metadata(metadata_str: str) -> List[str]:
    """Extract tags from metadata JSON string"""
    try:
        if metadata_str:
            metadata = json.loads(metadata_str)
            return metadata.get("tags", [])
        return []
    except (json.JSONDecodeError, AttributeError):
        return []

def format_contacts_for_api(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format contacts for the API endpoint"""
    formatted_contacts = []
    
    for contact in contacts:
        # Extract tags from metadata
        tags = extract_tags_from_metadata(contact.get("metadata_", ""))
        
        # If contact already has tags field, merge them
        existing_tags = contact.get("tags", [])
        all_tags = list(set(tags + existing_tags))  # Remove duplicates
        
        formatted_contact = {
            "name": contact.get("name", ""),
            "phone": contact.get("phone", ""),
            "status": contact.get("status", "active").lower(),  # Ensure lowercase
            "opt_out_sms": contact.get("opt_out_sms", False),
            "opt_out_whatsapp": contact.get("opt_out_whatsapp", False),
            "metadata_": contact.get("metadata_", ""),
            "tags": all_tags
        }
        
        formatted_contacts.append(formatted_contact)
    
    return formatted_contacts

def add_contacts_batch(access_token: str, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Add a list of contacts using the add-list endpoint"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Format contacts for the API
    formatted_contacts = format_contacts_for_api(contacts)
    data = {"contacts": formatted_contacts}

    try:
        print(f"Sending {len(formatted_contacts)} contacts to API...")
        response = requests.post(CONTACTS_ADD_LIST_URL, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        print(f"Contact batch add response: {result}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"Failed to add contacts in batch: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {error_detail}")
            except json.JSONDecodeError:
                print(f"Response content: {e.response.text}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during batch contact addition: {e}")
        raise

def main():
    """Main function to execute the script"""
    try:
        print("Starting contact batch upload process...")

        # Step 1: Login
        access_token = login()

        # Step 2: Read contacts
        contacts = read_contacts(CONTACTS_DATA_FILE)

        # Step 3: Add contacts in batch
        if contacts:
            add_contacts_batch(access_token, contacts)
            print("Contact batch upload process completed successfully!")
        else:
            print("No contacts found to add. Process completed.")

    except Exception as e:
        print(f"An error occurred during the process: {e}")

if __name__ == "__main__":
    main()