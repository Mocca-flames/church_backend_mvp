import requests
import base64
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BulkSMSProvider:
    def __init__(self):
        self.username = os.getenv("BULKSMS_USERNAME")
        self.password = os.getenv("BULKSMS_PASSWORD")
        self.api_uri = os.getenv("BULKSMS_API_URI", "https://api.bulksms.com/v1/messages") # Default URI

        if not all([self.username, self.password]):
            raise ValueError("Missing BulkSMS credentials in environment variables")

        credentials = f"{self.username}:{self.password}"
        self.encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        logger.info("BulkSMS provider initialized.")

    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via BulkSMS to a single recipient"""
        try:
            # Ensure phone number is in E.164 format
            if not to_number.startswith('+'):
                to_number = '+27' + to_number.lstrip('0')  # South African format example

            data = {
                "to": [to_number],
                "body": message,
                "encoding": "UNICODE",
                "longMessageMaxParts": "30",
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {self.encoded_credentials}"
            }

            response = requests.post(
                self.api_uri,
                json=data,
                headers=headers
            )

            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

            response_json = response.json()
            # Assuming BulkSMS API returns a list of messages with status and id
            # Adjust parsing based on actual BulkSMS API response structure
            if response_json and isinstance(response_json, list) and response_json[0].get('status') == 'ACCEPTED':
                return {
                    'success': True,
                    'message_id': response_json[0].get('id'),
                    'status': response_json[0].get('status'),
                    'phone': to_number,
                    'provider': 'bulksms'
                }
            else:
                logger.error(f"BulkSMS API returned unexpected response for {to_number}: {response.text}")
                return {
                    'success': False,
                    'error': f"Unexpected API response: {response.text}",
                    'phone': to_number,
                    'provider': 'bulksms'
                }

        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if e.response is not None:
                error_detail += f" - Details: {e.response.text}"
            logger.error(f"BulkSMS request error sending to {to_number}: {error_detail}")
            return {
                'success': False,
                'error': error_detail,
                'phone': to_number,
                'provider': 'bulksms'
            }
        except Exception as e:
            logger.error(f"General error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number,
                'provider': 'bulksms'
            }
