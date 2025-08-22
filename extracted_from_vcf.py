import re
import json
from typing import List, Dict, Set
import urllib.parse


def _clean_and_validate_phone(phone: str) -> str:
    """
    Cleans and validates a South African phone number according to specified rules.
    Ensures it's in +27XXXXXXXXX format (12 characters).
    Raises ValueError for invalid formats.
    """
    original_phone = phone
    digits_only = re.sub(r'\D', '', phone)

    if not digits_only:
        raise ValueError("Phone number cannot be empty.")

    formatted_phone = None

    if original_phone.startswith('0'):
        if len(digits_only) == 10 and digits_only.startswith('0'):
            # Remove leading '0' and prepend '+27'
            formatted_phone = '+27' + digits_only[1:]
        else:
            raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '0' must be 10 digits long.")
    elif original_phone.startswith('27'):
        if len(digits_only) == 11 and digits_only.startswith('27'):
            # Prepend '+'
            formatted_phone = '+' + digits_only
        else:
            raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '27' must be 11 digits long.")
    elif original_phone.startswith('+27'):
        if len(digits_only) == 11 and digits_only.startswith('27'):
            formatted_phone = '+' + digits_only
        else:
            raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Numbers starting with '+27' must have 11 digits after the prefix (e.g., '+27721234567').")
    else:
        raise ValueError(f"Invalid South African phone number format: '{original_phone}'. Must start with '0', '27', or '+27'.")

    # Final check for the expected 12-character format (+27XXXXXXXXX)
    if len(formatted_phone) != 12:
        raise ValueError(f"Internal error: Formatted phone number '{formatted_phone}' has incorrect length. Expected 12 characters (+27XXXXXXXXX).")

    return formatted_phone


def decode_quoted_printable(text: str) -> str:
    """Decode quoted-printable encoded text."""
    try:
        return urllib.parse.unquote(text.replace('=', '%'), encoding='utf-8')
    except:
        return text


def parse_vcf_file(file_path: str) -> List[Dict[str, any]]:
    """
    Parse VCF file and extract phone numbers with contact names.
    Returns list of dictionaries in the specified JSON format.
    """
    contacts = []
    processed_phones: Set[str] = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        # Try with different encodings if UTF-8 fails
        with open(file_path, 'r', encoding='latin-1') as file:
            content = file.read()
    
    # Split content into individual vCards
    vcards = content.split('BEGIN:VCARD')
    
    for vcard in vcards:
        if not vcard.strip():
            continue
            
        # Extract contact name
        name = ""
        fn_match = re.search(r'FN(?:[^:]*)?:(.*?)(?:\r?\n)', vcard, re.IGNORECASE)
        if fn_match:
            name = fn_match.group(1).strip()
            # Handle quoted-printable encoding
            if 'QUOTED-PRINTABLE' in vcard and '=' in name:
                name = decode_quoted_printable(name)
        
        # Extract all phone numbers
        phone_matches = re.findall(r'TEL[^:]*:(.*?)(?:\r?\n)', vcard, re.IGNORECASE)
        
        for phone_raw in phone_matches:
            phone_raw = phone_raw.strip()
            if not phone_raw:
                continue
                
            try:
                # Try to validate and format as South African number
                formatted_phone = _clean_and_validate_phone(phone_raw)
                
                # Skip if we've already processed this phone number
                if formatted_phone in processed_phones:
                    continue
                    
                processed_phones.add(formatted_phone)
                
                contact_entry = {
                    "phone": formatted_phone,
                    "name": formatted_phone,  # Using phone number as name as per example
                    "status": "Active",
                    "metadata": "null",
                    "opt_out_sms": False,
                    "optOutWhatsapp": False,
                    "tags": ["kanana"]
                }
                
                contacts.append(contact_entry)
                
            except ValueError as e:
                # Skip invalid phone numbers (e.g., international numbers)
                print(f"Skipping invalid phone number '{phone_raw}': {e}")
                continue
    
    return contacts


def extract_phones_from_vcf(file_path: str, output_file: str = None) -> List[Dict[str, any]]:
    """
    Main function to extract phone numbers from VCF file.
    
    Args:
        file_path: Path to the VCF file
        output_file: Optional path to save JSON output
        
    Returns:
        List of contact dictionaries
    """
    contacts = parse_vcf_file(file_path)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        print(f"Extracted {len(contacts)} contacts and saved to {output_file}")
    
    return contacts


if __name__ == "__main__":
    # Example usage
    vcf_file_path = "allacts.vcf"  # Replace with your VCF file path
    output_json_path = "extracted_contacts.json"  # Optional output file
    
    try:
        contacts = extract_phones_from_vcf(vcf_file_path, output_json_path)
        
        # Print results
        print(f"\nExtracted {len(contacts)} valid South African phone numbers:")
        for contact in contacts:
            print(json.dumps(contact, indent=2))
            
    except FileNotFoundError:
        print(f"Error: Could not find VCF file '{vcf_file_path}'")
    except Exception as e:
        print(f"Error processing VCF file: {e}")