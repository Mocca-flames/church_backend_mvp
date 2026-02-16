# This makes the 'sms' directory a Python package.

from .twilio import TwilioSMSProvider
from .africastalking import AfricasTalkingSMSProvider
from .smsportal import SMSPortalSMSProvider
from .winsms import WinSMSService
from .bulksms import BulkSMSProvider
from .clicktel import ClickatelSMSProvider

SMS_PROVIDERS = {
    "twilio": TwilioSMSProvider,
    "africastalking": AfricasTalkingSMSProvider,
    "smsportal": SMSPortalSMSProvider,
    "winsms": WinSMSService,
    "bulksms": BulkSMSProvider,
    "clickatel": ClickatelSMSProvider,
}
