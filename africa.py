import requests
import json
from typing import Dict, Any, Optional, Union

class AfricasTalkingAPI:
    """
    A professional client for interacting with the Africa's Talking SMS API.
    """
    
    BASE_URL = "https://api.africastalking.com/version1/messaging/bulk"
    
    def __init__(self, api_key: str, username: str = "sandbox"):
        """
        Initialize the API client.
        
        Args:
            api_key: Your Africa's Talking API key
            username: Your Africa's Talking username (defaults to 'sandbox')
        """
        self.api_key = api_key
        self.username = username
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "apiKey": self.api_key
        }
    
    def send_sms(
        self,
        message: str,
        phone_numbers: Union[str, list],
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS message to one or more phone numbers.
        
        Args:
            message: The text message to send
            phone_numbers: A single phone number or list of phone numbers
            sender_id: Optional sender ID (defaults to None)
            
        Returns:
            Dictionary containing the API response
            
        Raises:
            ValueError: If input validation fails
            requests.exceptions.RequestException: For network/API errors
        """
        # Validate and format phone numbers
        if isinstance(phone_numbers, str):
            phone_numbers = [phone_numbers]
            
        if not isinstance(phone_numbers, list) or not phone_numbers:
            raise ValueError("phone_numbers must be a non-empty list or string")
            
        if not message or not isinstance(message, str):
            raise ValueError("message must be a non-empty string")
            
        # Prepare the request payload
        payload = {
            "username": self.username,
            "message": message,
            "phoneNumbers": phone_numbers
        }
        
        if sender_id:
            payload["senderId"] = sender_id
            
        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json=payload,
                timeout=10  # Add timeout to prevent hanging
            )
            
            # Handle different response formats
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(
                f"Failed to send SMS: {str(e)}"
            ) from e
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle the API response, supporting different content types.
        
        Args:
            response: The requests.Response object
            
        Returns:
            Parsed response data as a dictionary
            
        Raises:
            ValueError: If response parsing fails
            requests.exceptions.HTTPError: For non-2xx status codes
        """
        try:
            response.raise_for_status()  # Raises HTTPError for bad status codes
            
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'application/json' in content_type:
                return response.json()
            elif 'application/xml' in content_type or 'text/xml' in content_type:
                # You would need xmltodict or similar for production use
                return {"raw_xml": response.text}
            elif 'text/html' in content_type:
                return {"raw_html": response.text}
            else:
                return {"raw_response": response.text}
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON response: {str(e)}") from e
        except requests.exceptions.HTTPError as e:
            # Include response content in the error for debugging
            error_msg = f"HTTP Error {response.status_code}: {str(e)}"
            try:
                error_details = response.json()
                error_msg += f" - Details: {error_details}"
            except ValueError:
                error_msg += f" - Response: {response.text[:200]}"
            raise requests.exceptions.HTTPError(error_msg) from e


# Example usage
if __name__ == "__main__":
    try:
        # Initialize client
        client = AfricasTalkingAPI(
            api_key="atsk_59b251ba07aa752314e4106b0728c55bbe4f179cfd98a6deb85176ab164ce445fdf8cd3a",
            username="thunder"
        )
        
        # Send SMS
        response = client.send_sms(
            message="Hello Maurice.",
            phone_numbers="+27780707520",
            sender_id=""
        )
        
        print("SMS sent successfully!")
        print(f"Status Code: {response.get('status')}")
        print(f"Response: {json.dumps(response, indent=2)}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        # Here you would add your error logging/alerting in production
