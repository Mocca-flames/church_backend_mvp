import requests
import base64
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SMSPortalSMSProvider:
    def __init__(self):
        self.api_key = os.getenv("SMSPORTAL_API_KEY")
        self.client_id = os.getenv("SMSPORTAL_CLIENT_ID") # Note: SMSPortal example uses api_secret, but .env has CLIENT_ID. I will use CLIENT_ID as per .env.
        self.test_mode = os.getenv("SMSPORTAL_TESTMODE", "False").lower() == "true"
        self.url = "https://rest.smsportal.com/BulkMessages"
        
        if not all([self.api_key, self.client_id]):
            raise ValueError("Missing SMSPortal credentials in environment variables")
        
        logger.info("SMSPortal SMS provider initialized.")
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via SMSPortal to a single recipient"""
        try:
            credentials = f"{self.api_key}:{self.client_id}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
            
            # Ensure phone number is in E.164 format for SMSPortal if needed, or adjust as per their specific requirements.
            # The example uses "YourTestPhoneNumber", assuming it's a direct number.
            # For South African numbers, typically '27' + number without leading '0'.
            if to_number.startswith('0'):
                to_number = '27' + to_number.lstrip('0')
            elif not to_number.startswith('27'):
                to_number = '27' + to_number # Assuming default to SA numbers if no country code

            data = {
                "messages": [
                    {
                        "content": message,
                        "destination": to_number
                    }
                ],
                "testMode": self.test_mode
            }

            response = requests.post(self.url, json=data, headers=headers)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            
            response_json = response.json()
            
            # SMSPortal API response structure might vary, adapting based on typical success/failure patterns
            # and the provided example's print(response.json())
            if response.status_code == 200 and response_json.get('messages') and response_json['messages'][0].get('status') == 'Accepted':
                return {
                    'success': True,
                    'status': response_json['messages'][0].get('status'),
                    'message_id': response_json['messages'][0].get('messageId'),
                    'phone': to_number,
                    'provider': 'smsportal'
                }
            else:
                # Handle cases where API returns 200 but indicates an error in the body
                error_message = response_json.get('error', 'Unknown error from SMSPortal')
                return {
                    'success': False,
                    'error': error_message,
                    'phone': to_number,
                    'provider': 'smsportal',
                    'raw_response': response_json
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"SMSPortal request error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number,
                'provider': 'smsportal'
            }
        except Exception as e:
            logger.error(f"General error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number,
                'provider': 'smsportal'
            }
