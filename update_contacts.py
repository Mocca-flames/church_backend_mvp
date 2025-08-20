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
PHONE_DATA_FILE = "phone_data_batch_2.json"
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

def read_phone_numbers(filename: str) -> List[str]:
    """Read phone numbers from a JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            phone_numbers = json.load(f)
        print(f"Read {len(phone_numbers)} phone numbers from {filename}")
        return phone_numbers
    except FileNotFoundError:
        print(f"Error: File not found at {filename}")
        raise
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filename}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        raise

def add_contacts_batch(access_token: str, phone_numbers: List[str]) -> Dict[str, Any]:
    """Add a list of contacts using the add-list endpoint"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Format contacts for the API
    contacts_payload = [{"phone": phone} for phone in phone_numbers]
    data = {"contacts": contacts_payload}

    try:
        response = requests.post(CONTACTS_ADD_LIST_URL, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        print(f"Contact batch add response: {result}")
        return result

    except requests.exceptions.RequestException as e:
        print(f"Failed to add contacts in batch: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during batch contact addition: {e}")
        raise

def main():
    """Main function to execute the script"""
    try:
        print("Starting contact update process...")

        # Step 1: Login
        access_token = login()

        # Step 2: Read phone numbers
        phone_numbers = read_phone_numbers(PHONE_DATA_FILE)

        # Step 3: Add contacts in batch
        if phone_numbers:
            add_contacts_batch(access_token, phone_numbers)
            print("Contact update process completed successfully!")
        else:
            print("No phone numbers found to add. Process completed.")

    except Exception as e:
        print(f"An error occurred during the process: {e}")

if __name__ == "__main__":
    main()
