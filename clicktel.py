import requests
import logging
from requests.exceptions import RequestException, HTTPError, Timeout, ConnectionError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
API_KEY = "kG9ImCIdQDOf5qQn3R_cBA=="
API_URL = "https://platform.clickatell.com/v1/message"

# Initialize session
session = requests.Session()
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": API_KEY
}

def send_sms(to_number: str, message: str) -> dict:
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
        logger.info(f"Sending SMS to {to_number}")
        response = session.post(API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        logger.info("SMS sent successfully")
        return response.json()

    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        return {"error": "HTTPError", "details": str(http_err), "response": response.text}
    
    except Timeout as timeout_err:
        logger.error(f"Request timed out: {timeout_err}")
        return {"error": "Timeout", "details": str(timeout_err)}
    
    except ConnectionError as conn_err:
        logger.error(f"Connection error: {conn_err}")
        return {"error": "ConnectionError", "details": str(conn_err)}

    except RequestException as req_err:
        logger.error(f"General request error: {req_err}")
        return {"error": "RequestException", "details": str(req_err)}
    
    except Exception as e:
        logger.exception("An unexpected error occurred")
        return {"error": "UnknownError", "details": str(e)}

# Example usage
if __name__ == "__main__":
    result = send_sms("+27762122008", "Test SMS Message Text")
    print(result)
