import requests
import os
from typing import Dict, Any
import logging
from requests.exceptions import RequestException, HTTPError, Timeout, ConnectionError

logger = logging.getLogger(__name__)

class ClickatelSMSProvider:
    def __init__(self):
        self.api_key = os.getenv("CLICKATEL_API_KEY")
        self.api_url = "https://platform.clickatell.com/v1/message" # Default URL
        
        if not self.api_key:
            raise ValueError("Missing Clickatel API Key in environment variables")
        
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.api_key
        }
        logger.info("Clickatel SMS provider initialized.")
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Clickatel to a single recipient"""
        payload = {
            "messages": [
                {
                    "channel": "sms",
                    "to": to_number,
                    "content": message
                }
            ]
        }

        try:
            # Ensure phone number is in E.164 format (Clickatel usually expects this)
            if not to_number.startswith('+'):
                to_number = '+' + to_number.lstrip('0') # General E.164 format

            logger.info(f"Sending SMS to {to_number} via Clickatel")
            response = self.session.post(self.api_url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            
            response_json = response.json()
            # Clickatel response structure might vary, assuming a 'messages' list with status
            if response_json and response_json.get('messages') and response_json['messages'][0].get('accepted'):
                return {
                    'success': True,
                    'message_id': response_json['messages'][0].get('apiMessageId'),
                    'status': 'SENT' if response_json['messages'][0].get('accepted') else 'FAILED',
                    'phone': to_number,
                    'provider': 'clickatel'
                }
            else:
                logger.error(f"Clickatel API returned unexpected response for {to_number}: {response.text}")
                return {
                    'success': False,
                    'error': f"Unexpected API response: {response.text}",
                    'phone': to_number,
                    'provider': 'clickatel'
                }

        except HTTPError as http_err:
            error_detail = f"HTTP error occurred: {http_err}"
            if response is not None:
                error_detail += f" - Response: {response.text}"
            logger.error(f"Clickatel HTTP error sending to {to_number}: {error_detail}")
            return {"success": False, "error": error_detail, "phone": to_number, "provider": "clickatel"}
        
        except Timeout as timeout_err:
            logger.error(f"Clickatel request timed out sending to {to_number}: {timeout_err}")
            return {"success": False, "error": str(timeout_err), "phone": to_number, "provider": "clickatel"}
        
        except ConnectionError as conn_err:
            logger.error(f"Clickatel connection error sending to {to_number}: {conn_err}")
            return {"success": False, "error": str(conn_err), "phone": to_number, "provider": "clickatel"}

        except RequestException as req_err:
            logger.error(f"Clickatel general request error sending to {to_number}: {req_err}")
            return {"success": False, "error": str(req_err), "phone": to_number, "provider": "clickatel"}
        
        except Exception as e:
            logger.exception(f"An unexpected error occurred sending to {to_number}")
            return {"success": False, "error": str(e), "phone": to_number, "provider": "clickatel"}
