from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Missing Twilio credentials in environment variables")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send SMS to a single recipient"""
        try:
            # Ensure phone number is in E.164 format
            if not to_number.startswith('+'):
                to_number = '+27' + to_number.lstrip('0')  # South African format
            
            message_instance = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            return {
                'success': True,
                'message_sid': message_instance.sid,
                'status': message_instance.status,
                'phone': to_number
            }
        except TwilioException as e:
            logger.error(f"Twilio error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number
            }
        except Exception as e:
            logger.error(f"General error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number
            }
    
    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> Dict[str, Any]:
        """Send SMS to multiple recipients"""
        results = []
        sent_count = 0
        failed_count = 0
        
        for phone in phone_numbers:
            result = self.send_sms(phone, message)
            results.append(result)
            
            if result['success']:
                sent_count += 1
            else:
                failed_count += 1
        
        return {
            'total_sent': sent_count,
            'total_failed': failed_count,
            'results': results
        }

# Global SMS service instance
sms_service = SMSService()
