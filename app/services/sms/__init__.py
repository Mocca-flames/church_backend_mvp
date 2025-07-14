# This makes the 'sms' directory a Python package.

from .twilio import TwilioSMSProvider
from .africastalking import AfricasTalkingSMSProvider
from .smsportal import SMSPortalSMSProvider

SMS_PROVIDERS = {
    "twilio": TwilioSMSProvider,
    "africastalking": AfricasTalkingSMSProvider,
    "smsportal": SMSPortalSMSProvider,
}
