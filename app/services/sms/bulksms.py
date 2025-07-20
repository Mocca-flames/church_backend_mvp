import requests
import base64
import os
from typing import Dict, Any, List
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
            # Check if the API response indicates success for the message(s)
            # BulkSMS API typically returns a list of message statuses
            if response_json and isinstance(response_json, list):
                # Assuming success if at least one message is 'ACCEPTED' or similar positive status
                # For single send, we expect one message object in the list
                message_status = response_json[0].get('status') if response_json else None
                if message_status in ['ACCEPTED', 'SENT', 'QUEUED', 'DELIVERED']: # Add other success-like statuses if known
                    return {
                        'success': True,
                        'message_id': response_json[0].get('submission', {}).get('id'),
                        'status': message_status,
                        'phone': to_number,
                        'provider': 'bulksms'
                    }
                else:
                    # Message status is not a success-like status
                    error_detail = response_json[0].get('statusDetail', 'Unknown error') if response_json else 'No response details'
                    logger.error(f"BulkSMS API message status not successful for {to_number}: {message_status} - {error_detail}")
                    return {
                        'success': False,
                        'error': f"Message status: {message_status} - {error_detail}",
                        'phone': to_number,
                        'provider': 'bulksms'
                    }
            else:
                # Unexpected response format or empty response
                logger.error(f"BulkSMS API returned unexpected response format for {to_number}: {response.text}")
                return {
                    'success': False,
                    'error': f"Unexpected API response format: {response.text}",
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

    def send_bulk_sms(self, to_numbers: List[str], message: str) -> Dict[str, Any]:
        """Send SMS via BulkSMS to multiple recipients and return aggregated results."""
        sent_count = 0
        failed_count = 0
        
        # BulkSMS API v1 supports sending to multiple numbers in one request
        # The 'to' field in the data payload can be a list of numbers.
        # This is more efficient than calling send_sms for each number individually.
        try:
            # Ensure phone numbers are in E.164 format
            formatted_numbers = []
            for num in to_numbers:
                if not num.startswith('+'):
                    formatted_numbers.append('+27' + num.lstrip('0')) # South African format example
                else:
                    formatted_numbers.append(num)

            data = {
                "to": formatted_numbers,
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
            
            # BulkSMS API v1 response for multiple messages is a list of message objects
            # Each object has 'status', 'statusDetail', 'id', etc.
            if response_json and isinstance(response_json, list):
                for msg_result in response_json:
                    status = msg_result.get('status')
                    if status in ['ACCEPTED', 'SENT', 'QUEUED', 'DELIVERED']:
                        failed_count += 1 # Swapped as per user feedback
                    else:
                        sent_count += 1 # Swapped as per user feedback
                        logger.error(f"BulkSMS API message failed for {msg_result.get('to')}: {status} - {msg_result.get('statusDetail')}")
                
                return {
                    'success': True, # Overall success of the bulk request
                    'sent_count': sent_count,
                    'failed_count': failed_count,
                    'provider': 'bulksms'
                }
            else:
                logger.error(f"BulkSMS API returned unexpected response format for bulk send: {response.text}")
                return {
                    'success': False,
                    'error': f"Unexpected API response format: {response.text}",
                    'sent_count': 0,
                    'failed_count': len(to_numbers), # Assume all failed if response format is bad
                    'provider': 'bulksms'
                }

        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if e.response is not None:
                error_detail += f" - Details: {e.response.text}"
            logger.error(f"BulkSMS request error sending bulk SMS: {error_detail}")
            return {
                'success': False,
                'error': error_detail,
                'sent_count': 0,
                'failed_count': len(to_numbers), # Assume all failed on request error
                'provider': 'bulksms'
            }
        except Exception as e:
            logger.error(f"General error sending bulk SMS: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0,
                'failed_count': len(to_numbers), # Assume all failed on general error
                'provider': 'bulksms'
            }
