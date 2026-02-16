#!/usr/bin/env python3
"""
Script to login to the system, fetch all contacts, and save them to contact_list.txt
"""

import requests
import json
import csv
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://172.209.208.53:8000"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"
OUTPUT_FILE = "contact_list.txt"

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

def save_contacts_to_file(contacts: List[Dict[str, Any]], filename: str) -> None:
    """Save contacts to a file with comma-separated values"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            # Collect all phone numbers
            phone_numbers = []
            for contact in contacts:
                phone = contact.get("phone", "").replace(",", ";") if contact.get("phone") else ""
                phone_numbers.append(phone)

            # Write header
            header = ["phone"]
            file.write(",".join(header) + "\n")

            # Write all phone numbers as a single comma-separated line
            file.write(",".join(phone_numbers) + "\n")

        print(f"Contacts saved to {filename}")

    except IOError as e:
        print(f"Failed to write to file: {e}")
        raise

def main():
    """Main function to execute the script"""
    try:
        print("Starting contact fetch process...")

        # Step 1: Login
        access_token = login()

        # Step 2: Fetch contacts
        contacts = fetch_contacts(access_token)

        # Step 3: Save to file
        save_contacts_to_file(contacts, OUTPUT_FILE)

        print("Process completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
