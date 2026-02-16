import os
from typing import Dict, Any, List
import logging
import africastalking

logger = logging.getLogger(__name__)

class AfricasTalkingSMSProvider:
    def __init__(self):
        self.api_key = os.getenv("AFRICASTALKING_API_KEY")
        self.username = os.getenv("AFRICASTALKING_USERNAME")

        if not all([self.api_key, self.username]):
            raise ValueError("Missing Africa's Talking credentials in environment variables")
        
        africastalking.initialize(self.username, self.api_key)
        self.sms = africastalking.SMS
        logger.info("Africa's Talking SMS provider initialized.")

    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        try:
            response = self.sms.send(message, [to_number])
            result = response['SMSMessageData']['Recipients'][0]

            if result['status'] == 'Success':
                return {
                    'success': True,
                    'message_id': result['messageId'],
                    'status': result['status'],
                    'cost': result['cost'],
                    'phone': to_number,
                    'provider': 'africastalking'
                }
            else:
                logger.error(f"Africa's Talking error sending to {to_number}: {result['status']}")
                return {
                    'success': False,
                    'error': result['status'],
                    'phone': to_number,
                    'provider': 'africastalking'
            }

        except Exception as e:
            logger.error(f"Africa's Talking SDK error sending to {to_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'phone': to_number,
                'provider': 'africastalking'
            }

    def send_bulk_sms(self, to_numbers: List[str], message: str) -> List[Dict[str, Any]]:
        try:
            response = self.sms.send(message, to_numbers)
            results = []
            for recipient_data in response['SMSMessageData']['Recipients']:
                if recipient_data['status'] == 'Success':
                    results.append({
                        'success': True,
                        'message_id': recipient_data['messageId'],
                        'status': recipient_data['status'],
                        'cost': recipient_data['cost'],
                        'phone': recipient_data['number'],
                        'provider': 'africastalking'
                    })
                else:
                    logger.error(f"Africa's Talking error sending to {recipient_data['number']}: {recipient_data['status']}")
                    results.append({
                        'success': False,
                        'error': recipient_data['status'],
                        'phone': recipient_data['number'],
                        'provider': 'africastalking'
                    })
            return results
        except Exception as e:
            logger.error(f"Africa's Talking SDK error sending bulk SMS: {str(e)}")
            return [{'success': False, 'error': str(e), 'phone': num, 'provider': 'africastalking'} for num in to_numbers]
