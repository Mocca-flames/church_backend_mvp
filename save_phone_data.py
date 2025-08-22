#!/usr/bin/env python3
"""
Script to login to the system, fetch all contacts, and save phone data as JSON
"""

import requests
import json
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://34.63.67.176:8000"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"
OUTPUT_FILE = "phone_data.json"

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

def fetch_contacts(access_token: str) -> List[Dict[str, Any]]:
    """Fetch all contacts using the provided access token"""
    contacts_url = f"{BASE_URL}/contacts"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    params = {
        "limit": 2000  # Fetch all 2000 contacts
    }

    try:
        response = requests.get(contacts_url, headers=headers, params=params)
        response.raise_for_status()

        contacts = response.json()
        print(f"Fetched {len(contacts)} contacts")
        return contacts

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch contacts: {e}")
        raise

def save_phone_data(contacts: List[Dict[str, Any]], filename: str) -> None:
    """Save phone data to a single JSON file"""
    phone_data = contacts
    
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(phone_data, file, indent=4)
        print(f"Saved {len(phone_data)} phone numbers to {filename}")
    except IOError as e:
        print(f"Failed to write to file: {e}")
        raise
    except TypeError as e:
        print(f"Failed to serialize data to JSON: {e}")
        raise

def main():
    """Main function to execute the script"""
    try:
        print("Starting phone data saving process...")

        # Step 1: Login
        access_token = login()

        # Step 2: Fetch contacts
        contacts = fetch_contacts(access_token)

        # Step 3: Save to JSON file
        save_phone_data(contacts, OUTPUT_FILE)

        print("Process completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()