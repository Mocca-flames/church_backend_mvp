#!/usr/bin/env python3
"""
Script to login to the system, fetch all contacts, and save phone data as JSON
"""

import requests
import json
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://172.209.208.53:8000"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"
OUTPUT_FILE = "phone_data.json" # Changed to .json

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

def save_phone_data_in_batches(contacts: List[Dict[str, Any]], base_filename: str, batch_size: int = 1000) -> None:
    """Save phone data to JSON files in batches"""
    num_contacts = len(contacts)
    num_batches = (num_contacts + batch_size - 1) // batch_size

    for i in range(num_batches):
        start_index = i * batch_size
        end_index = min((i + 1) * batch_size, num_contacts)
        batch_contacts = contacts[start_index:end_index]

        batch_filename = f"{base_filename.rsplit('.', 1)[0]}_batch_{i+1}.{base_filename.rsplit('.', 1)[1]}"

        try:
            with open(batch_filename, 'w', encoding='utf-8') as file:
                json.dump([contact.get("phone", "") for contact in batch_contacts], file, indent=4)
            print(f"Saved batch {i+1}/{num_batches} to {batch_filename}")
        except IOError as e:
            print(f"Failed to write batch {i+1} to file: {e}")
            raise
        except TypeError as e:
            print(f"Failed to serialize batch {i+1} to JSON: {e}")
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
        save_phone_data_in_batches(contacts, OUTPUT_FILE)

        print("Process completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
