#!/usr/bin/env python3
"""
Script to update contacts in batches of 10 using the mass update endpoint
"""

import requests
import json
import time
from typing import List, Dict, Any

# Configuration
BASE_URL = "https://37fe59d75381.ngrok-free.app"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"
INPUT_FILE = "extracted_contacts.json"
BATCH_SIZE = 10
DELAY_BETWEEN_BATCHES = 1  # seconds

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

        print("✅ Login successful!")
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed: {e}")
        raise

def load_contacts(filename: str) -> List[Dict[str, Any]]:
    """Load contacts from a JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            contacts = json.load(file)
        print(f"📄 Loaded {len(contacts)} contacts from {filename}")
        return contacts
    except IOError as e:
        print(f"❌ Failed to read file: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        raise

def update_contact_batch(access_token: str, batch: List[Dict[str, Any]], batch_number: int) -> bool:
    """Update a batch of contacts and return success status"""
    mass_update_url = f"{BASE_URL}/contacts/mass-update"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.put(mass_update_url, headers=headers, json=batch)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Batch {batch_number}: Updated {len(result)} contacts successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Batch {batch_number} failed: {e}")
        if e.response:
            try:
                error_data = e.response.json()
                print(f"   Error details: {error_data}")
            except:
                print(f"   Error response: {e.response.text}")
        return False

def process_contacts_in_batches(access_token: str, contacts: List[Dict[str, Any]]) -> None:
    """Process all contacts in batches"""
    total_contacts = len(contacts)
    total_batches = (total_contacts + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division
    
    print(f"\n🔄 Processing {total_contacts} contacts in {total_batches} batches of {BATCH_SIZE}")
    print("=" * 60)
    
    successful_batches = 0
    failed_batches = 0
    processed_contacts = 0
    
    for i in range(0, total_contacts, BATCH_SIZE):
        batch_number = (i // BATCH_SIZE) + 1
        batch = contacts[i:i + BATCH_SIZE]
        batch_size = len(batch)
        
        print(f"\n📦 Processing batch {batch_number}/{total_batches} ({batch_size} contacts)")
        print(f"   Contacts {i + 1} to {i + batch_size} of {total_contacts}")
        
        # Show sample contacts in this batch
        sample_contacts = batch[:3]  # Show first 3 contacts
        for j, contact in enumerate(sample_contacts):
            phone = contact.get('phone', 'N/A')
            name = contact.get('name', 'N/A')
            print(f"   • {phone} - {name}")
        if len(batch) > 3:
            print(f"   • ... and {len(batch) - 3} more contacts")
        
        # Process the batch
        success = update_contact_batch(access_token, batch, batch_number)
        
        if success:
            successful_batches += 1
            processed_contacts += batch_size
            print(f"   ✅ Progress: {processed_contacts}/{total_contacts} contacts processed")
        else:
            failed_batches += 1
            print(f"   ❌ Batch failed - continuing with next batch")
        
        # Add delay between batches (except for the last batch)
        if i + BATCH_SIZE < total_contacts:
            print(f"   ⏳ Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY:")
    print(f"   Total contacts: {total_contacts}")
    print(f"   Total batches: {total_batches}")
    print(f"   Successful batches: {successful_batches}")
    print(f"   Failed batches: {failed_batches}")
    print(f"   Successfully processed contacts: {processed_contacts}")
    
    if failed_batches > 0:
        print(f"\n⚠️  {failed_batches} batches failed. You may want to retry the failed contacts.")
    else:
        print(f"\n🎉 All contacts processed successfully!")

def main():
    """Main function to execute the script"""
    try:
        print("🚀 Starting batch contact update...")
        print(f"Configuration:")
        print(f"  - Base URL: {BASE_URL}")
        print(f"  - Batch size: {BATCH_SIZE}")
        print(f"  - Delay between batches: {DELAY_BETWEEN_BATCHES}s")

        # Step 1: Login
        access_token = login()

        # Step 2: Load contacts
        contacts = load_contacts(INPUT_FILE)

        # Step 3: Process contacts in batches
        process_contacts_in_batches(access_token, contacts)

        print("\n✅ Script completed!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    main()