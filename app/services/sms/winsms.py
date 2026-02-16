import requests
import json
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class WinSMSService:
    BASE_URL = "https://api.winsms.co.za/api/rest/v1"
    
    def __init__(self):
        self.api_key = os.getenv("WINSMS_API_KEY")
        
        if not self.api_key:
            raise ValueError("Missing WinSMS API key in environment variables")
        
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info("WinSMS provider initialized.")
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via WinSMS API to a single recipient.
        This method is adapted to fit the CommunicationService's single send_sms call,
        but internally uses the WinSMS bulk API for consistency.
        """
        return self.send_bulk_sms([to_number], message)

    def send_bulk_sms(self, recipients: List[str], message: str) -> Dict[str, Any]:
        """Send bulk SMS via WinSMS API to multiple recipients"""
        try:
            # Prepare recipient details
            recipient_details = []
            for number in recipients:
                # Ensure phone number is in E.164 format (without + for WinSMS)
                if number.startswith('+'):
                    number = number[1:] # Remove '+' if present
                if not number.startswith('27'):
                    number = '27' + number.lstrip('0') # South African format
                recipient_details.append({"mobileNumber": number})

            # Prepare payload
            payload: Dict[str, Any] = {
                "message": message,
                "recipients": recipient_details,
                "maxSegments": 1 # Default to 1 segment for simplicity, can be made configurable
            }

            # Make API request
            url = f"{self.BASE_URL}/sms/outgoing/send"

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            response_data = response.json()

            # WinSMS API returns a list of results, even for single recipient
            # We need to aggregate results for the CommunicationService
            success_count = 0
            failed_count = 0
            messages_info = []

            if response_data and isinstance(response_data, list):
                for res in response_data:
                    if res.get('statusCode') == 0:
                        success_count += 1
                        messages_info.append({
                            'phone': res.get('mobileNumber'),
                            'message_id': res.get('apiMessageId'),
                            'status': 'sent'
                        })
                    else:
                        failed_count += 1
                        messages_info.append({
                            'phone': res.get('mobileNumber'),
                            'error': res.get('errorMessage', 'Unknown error'),
                            'status': 'failed'
                        })
            else:
                # Handle cases where response_data is not a list or empty
                error_detail = 'No specific error message from API'
                if response_data and isinstance(response_data, dict) and 'errorMessage' in response_data:
                    error_detail = response_data['errorMessage']
                logger.error(f"WinSMS error sending messages: {error_detail}")
                return {
                    'success': False,
                    'error': error_detail,
                    'provider': 'winsms',
                    'sent_count': 0,
                    'failed_count': len(recipients),
                    'messages': []
                }

            return {
                'success': success_count > 0, # Overall success if at least one message sent
                'sent_count': success_count,
                'failed_count': failed_count,
                'provider': 'winsms',
                'messages': messages_info # Detailed results for each message
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"WinSMS API request failed: {str(e)}"
            if e.response is not None:
                error_msg += f" - {e.response.text}"
            logger.error(f"WinSMS error sending messages: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'provider': 'winsms',
                'sent_count': 0,
                'failed_count': len(recipients),
                'messages': []
            }
        except json.JSONDecodeError as e:
            logger.error(f"WinSMS failed to decode API response: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to decode API response: {str(e)}",
                'provider': 'winsms',
                'sent_count': 0,
                'failed_count': len(recipients),
                'messages': []
            }
        except Exception as e:
            logger.error(f"General error sending messages: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'winsms',
                'sent_count': 0,
                'failed_count': len(recipients),
                'messages': []
            }
