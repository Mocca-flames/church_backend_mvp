import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

# Configuration
BASE_URL = "http://34.63.67.176:8000"
LOGIN_EMAIL = "admin@thunder.com"
LOGIN_PASSWORD = "admin@1234"
INPUT_FILE = "new_phone.json"

# Default contact data template
DEFAULT_STATUS = "Active"
DEFAULT_OPT_OUT_SMS = False
DEFAULT_OPT_OUT_WHATSAPP = False
DEFAULT_TAGS = ["majaneng"]

# Performance settings
BATCH_SIZE = 50  # Increased batch size for bulk operations
MAX_CONCURRENT_REQUESTS = 10
REQUEST_DELAY = 0.1  # Reduced delay for bulk operations

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# The script mass creates contacts and then updates their tags to ["majaneng"], overwriting any existing tags.
# It fetches all contacts once to map phone numbers to IDs for efficient updates.
# The update phase uses individual PUT requests to update each contact's metadata.
# Verification fetches all contacts with a high limit to accurately report success.
# This approach avoids bulk update endpoint issues and ensures all contacts are updated correctly.

@dataclass
class ContactData:
    """Data class for contact information."""
    phone: str
    name: Optional[str] = None
    status: str = DEFAULT_STATUS
    opt_out_sms: bool = DEFAULT_OPT_OUT_SMS
    opt_out_whatsapp: bool = DEFAULT_OPT_OUT_WHATSAPP
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = DEFAULT_TAGS.copy()
        if self.name is None:
            self.name = self.phone

class OptimizedContactManager:
    """Optimized contact management with bulk operations."""
    
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.email = email
        self.password = password
        self.token = None
        
        # HTTP client configuration
        timeout = httpx.Timeout(60.0, connect=15.0)
        limits = httpx.Limits(
            max_connections=MAX_CONCURRENT_REQUESTS * 2,
            max_keepalive_connections=MAX_CONCURRENT_REQUESTS
        )
        self.client = httpx.AsyncClient(timeout=timeout, limits=limits)
    
    async def __aenter__(self):
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def login(self) -> None:
        """Authenticate and store the access token."""
        login_url = f"{self.base_url}/auth/login"
        data = {
            "username": self.email,
            "password": self.password,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            response = await self.client.post(login_url, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data["access_token"]
            logger.info("✅ Login successful")
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    async def get_all_contacts(self) -> List[Dict[str, Any]]:
        """Fetch all contacts from the system."""
        try:
            logger.info("📋 Fetching all existing contacts...")
            response = await self.client.get(
                f"{self.base_url}/contacts",
                headers=self._get_headers()
            )
            response.raise_for_status()
            contacts = response.json()
            logger.info(f"📊 Found {len(contacts)} existing contacts")
            return contacts
        except Exception as e:
            logger.error(f"❌ Error fetching contacts: {e}")
            return []
    
    async def create_contacts_bulk(self, contacts_data: List[ContactData]) -> Tuple[List[str], List[str]]:
        """Create multiple contacts using individual requests (since no bulk create endpoint)."""
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        successful_creates = []
        failed_creates = []
        
        async def create_single_contact(contact_data: ContactData) -> bool:
            async with semaphore:
                try:
                    contact_payload = {
                        "name": contact_data.name,
                        "phone": contact_data.phone,
                        "status": contact_data.status,
                        "opt_out_sms": contact_data.opt_out_sms,
                        "opt_out_whatsapp": contact_data.opt_out_whatsapp,
                        "metadata_": json.dumps({"tags": contact_data.tags}),
                    }
                    
                    response = await self.client.post(
                        f"{self.base_url}/contacts",
                        headers=self._get_headers(),
                        json=contact_payload
                    )
                    
                    if response.status_code == 201:
                        logger.debug(f"✅ Created: {contact_data.phone}")
                        return True
                    elif response.status_code == 400:
                        # Contact might already exist - this is expected
                        logger.debug(f"→ Contact {contact_data.phone} already exists")
                        return False
                    else:
                        response.raise_for_status()
                        
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 400:  # 400 means already exists
                        logger.error(f"❌ HTTP {e.response.status_code} creating {contact_data.phone}")
                    return False
                except Exception as e:
                    logger.error(f"❌ Error creating {contact_data.phone}: {e}")
                    return False
                
                await asyncio.sleep(REQUEST_DELAY)
        
        logger.info(f"🚀 Creating {len(contacts_data)} contacts...")
        
        # Process in batches
        for i in range(0, len(contacts_data), BATCH_SIZE):
            batch = contacts_data[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(contacts_data) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"📝 Processing creation batch {batch_num}/{total_batches} ({len(batch)} contacts)")
            
            tasks = [create_single_contact(contact) for contact in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for contact, result in zip(batch, results):
                if result is True:
                    successful_creates.append(contact.phone)
                else:
                    failed_creates.append(contact.phone)
            
            logger.info(f"✅ Batch {batch_num} complete: {sum(1 for r in results if r is True)} created")
            
            if i + BATCH_SIZE < len(contacts_data):
                await asyncio.sleep(0.5)  # Brief pause between batches
        
        logger.info(f"📊 Creation complete: {len(successful_creates)} new, {len(failed_creates)} existing")
        return successful_creates, failed_creates
    
    async def update_contacts_bulk(self, phone_numbers: List[str]) -> Tuple[List[str], List[str]]:
        """Update multiple contacts by fetching all contacts once and updating by ID, skipping if tags exist."""
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        successful_updates = []
        failed_updates = []
        
        # Fetch all contacts once
        try:
            response = await self.client.get(
                f"{self.base_url}/contacts?limit=10000",
                headers=self._get_headers()
            )
            response.raise_for_status()
            all_contacts = response.json()
            phone_to_contact = {contact.get('phone'): contact for contact in all_contacts}
            logger.info(f"📋 Fetched {len(all_contacts)} contacts for update mapping")
        except Exception as e:
            logger.error(f"❌ Failed to fetch contacts for update mapping: {e}")
            return [], phone_numbers
        
        async def update_single_contact_by_id(contact_id: int, phone: str) -> bool:
            async with semaphore:
                try:
                    # Check if contact already has tags
                    contact = phone_to_contact.get(phone)
                    if contact:
                        metadata_str = contact.get('metadata_', '{}')
                        metadata = json.loads(metadata_str) if metadata_str else {}
                        existing_tags = metadata.get('tags', [])
                        if existing_tags:
                            logger.info(f"ℹ️ Skipping update for {phone} as tags already exist")
                            return True
                    
                    update_data = {
                        "status": DEFAULT_STATUS,
                        "opt_out_sms": DEFAULT_OPT_OUT_SMS,
                        "opt_out_whatsapp": DEFAULT_OPT_OUT_WHATSAPP,
                        "metadata_": json.dumps({"tags": DEFAULT_TAGS})
                    }
                    
                    update_response = await self.client.put(
                        f"{self.base_url}/contacts/{contact_id}",
                        headers=self._get_headers(),
                        json=update_data
                    )
                    update_response.raise_for_status()
                    logger.debug(f"✅ Updated contact {phone}")
                    return True
                
                except Exception as e:
                    logger.error(f"❌ Error updating contact {phone}: {e}")
                    return False
                
                finally:
                    await asyncio.sleep(REQUEST_DELAY)
        
        logger.info(f"🔄 Updating {len(phone_numbers)} contacts individually by ID, skipping those with existing tags...")
        
        for i in range(0, len(phone_numbers), BATCH_SIZE):
            batch = phone_numbers[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(phone_numbers) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"🔄 Processing update batch {batch_num}/{total_batches} ({len(batch)} contacts)")
            
            tasks = []
            for phone in batch:
                contact = phone_to_contact.get(phone)
                if not contact:
                    logger.warning(f"⚠️ Contact with phone {phone} not found for update")
                    failed_updates.append(phone)
                else:
                    contact_id = contact.get('id')
                    tasks.append(update_single_contact_by_id(contact_id, phone))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for phone, result in zip([phone for phone in batch if phone in phone_to_contact], results):
                if result is True:
                    successful_updates.append(phone)
                else:
                    failed_updates.append(phone)
            
            await asyncio.sleep(0.2)
        
        logger.info(f"📊 Individual update complete: {len(successful_updates)} updated or skipped, {len(failed_updates)} failed")
        return successful_updates, failed_updates
    
    async def verify_contacts(self, phone_numbers: List[str]) -> Dict[str, Any]:
        """Verify the final state of contacts after processing."""
        try:
            logger.info("🔍 Verifying final contact state...")
            
            # Get all contacts with a high limit to include all
            response = await self.client.get(
                f"{self.base_url}/contacts?limit=10000",
                headers=self._get_headers()
            )
            response.raise_for_status()
            all_contacts = response.json()
            contacts_map = {contact.get('phone'): contact for contact in all_contacts}
            logger.info(f"📋 Fetched {len(all_contacts)} contacts for verification mapping")
            
            # Analyze results
            processed_contacts = []
            missing_contacts = []
            contacts_with_tags = []
            contacts_without_tags = []
            
            for phone in phone_numbers:
                if phone in contacts_map:
                    contact = contacts_map[phone]
                    processed_contacts.append(contact)
                    
                    # Check tags
                    try:
                        metadata = json.loads(contact.get('metadata_', '{}')) if contact.get('metadata_') else {}
                        tags = metadata.get('tags', [])
                        
                        if any(tag in DEFAULT_TAGS for tag in tags):
                            contacts_with_tags.append(phone)
                        else:
                            contacts_without_tags.append(phone)
                    except json.JSONDecodeError:
                        contacts_without_tags.append(phone)
                else:
                    missing_contacts.append(phone)
            
            results = {
                "total_processed": len(phone_numbers),
                "found_contacts": len(processed_contacts),
                "missing_contacts": len(missing_contacts),
                "contacts_with_tags": len(contacts_with_tags),
                "contacts_without_tags": len(contacts_without_tags),
                "success_rate": len(processed_contacts) / len(phone_numbers) * 100 if phone_numbers else 0,
                "tag_success_rate": len(contacts_with_tags) / len(processed_contacts) * 100 if processed_contacts else 0
            }
            
            # Log summary
            logger.info("📊 FINAL VERIFICATION RESULTS:")
            logger.info(f"   📱 Total phones processed: {results['total_processed']}")
            logger.info(f"   ✅ Contacts found: {results['found_contacts']}")
            logger.info(f"   ❌ Missing contacts: {results['missing_contacts']}")
            logger.info(f"   🏷️ Contacts with correct tags: {results['contacts_with_tags']}")
            logger.info(f"   ⚠️ Contacts without tags: {results['contacts_without_tags']}")
            logger.info(f"   📈 Contact success rate: {results['success_rate']:.1f}%")
            logger.info(f"   🎯 Tag success rate: {results['tag_success_rate']:.1f}%")
            
            # Show samples
            if missing_contacts:
                logger.warning(f"❌ Missing contacts (first 5): {missing_contacts[:5]}")
            
            if contacts_without_tags:
                logger.warning(f"⚠️ Contacts without tags (first 5): {contacts_without_tags[:5]}")
            
            if contacts_with_tags:
                logger.info(f"✅ Successfully tagged contacts (first 5): {contacts_with_tags[:5]}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during verification: {e}")
            return {}

async def load_phone_numbers(filename: str) -> List[str]:
    """Load and validate phone numbers from JSON file."""
    try:
        logger.info(f"📂 Loading phone numbers from {filename}")
        with open(filename, "r") as f:
            phones = json.load(f)
        
        # Validate phone numbers
        valid_phones = []
        invalid_phones = []
        
        for phone in phones:
            if isinstance(phone, str) and phone.startswith('+27') and len(phone) == 12:
                valid_phones.append(phone)
            else:
                invalid_phones.append(phone)
        
        if invalid_phones:
            logger.warning(f"⚠️ Found {len(invalid_phones)} invalid phone numbers: {invalid_phones[:5]}...")
        
        logger.info(f"📱 Loaded {len(valid_phones)} valid phone numbers")
        return valid_phones
        
    except FileNotFoundError:
        logger.error(f"❌ Input file {filename} not found")
        raise
    except json.JSONDecodeError:
        logger.error(f"❌ Error decoding JSON from {filename}")
        raise

async def main():
    """Main execution function with optimized processing."""
    try:
        # Load phone numbers
        phone_numbers = await load_phone_numbers(INPUT_FILE)
        if not phone_numbers:
            logger.error("❌ No valid phone numbers to process")
            return
        
        # Create contact data objects
        contacts_data = [ContactData(phone=phone) for phone in phone_numbers]
        
        async with OptimizedContactManager(BASE_URL, LOGIN_EMAIL, LOGIN_PASSWORD) as manager:
            
            # Phase 1: Create contacts (those that don't exist)
            logger.info("\n" + "="*60)
            logger.info("🚀 PHASE 1: CREATING NEW CONTACTS")
            logger.info("="*60)
            
            created_contacts, existing_contacts = await manager.create_contacts_bulk(contacts_data)
            
            # Phase 2: Update all contacts with tags using bulk update
            logger.info("\n" + "="*60)
            logger.info("🔄 PHASE 2: BULK UPDATING CONTACT TAGS")
            logger.info("="*60)
            
            # Wait a moment for database consistency
            if created_contacts:
                logger.info("⏳ Waiting 2 seconds for database consistency...")
                await asyncio.sleep(2)
            
            updated_contacts, failed_updates = await manager.update_contacts_bulk(phone_numbers)
            
            # Phase 3: Verify results
            logger.info("\n" + "="*60)
            logger.info("🔍 PHASE 3: VERIFICATION & SUMMARY")
            logger.info("="*60)
            
            results = await manager.verify_contacts(phone_numbers)
            
            # Final summary
            logger.info("\n" + "🎉" + "="*58 + "🎉")
            logger.info("🏁 PROCESSING COMPLETE - FINAL SUMMARY")
            logger.info("🎉" + "="*58 + "🎉")
            logger.info(f"📊 New contacts created: {len(created_contacts)}")
            logger.info(f"📊 Existing contacts found: {len(existing_contacts)}")
            logger.info(f"📊 Contacts updated with tags: {len(updated_contacts)}")
            logger.info(f"📊 Failed updates: {len(failed_updates)}")
            
            if results:
                logger.info(f"🎯 Overall success rate: {results.get('success_rate', 0):.1f}%")
                logger.info(f"🏷️ Tag application success rate: {results.get('tag_success_rate', 0):.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())