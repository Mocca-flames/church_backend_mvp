import requests
import json

# Configuration
BASE_URL = "https://a4dc-102-254-20-25.ngrok-free.app"
USERNAME = "pompi@gmail.com"
PASSWORD = "12345678"


def login():
    """Login to get access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    response.raise_for_status()
    return response.json()["access_token"]

def get_dashboard(token):
    """Test GET /dashboard to see the actual error response"""
    print("\n" + "="*60)
    print("TESTING: GET /dashboard")
    print("="*60)
    
    response = requests.get(
        f"{BASE_URL}/contacts/dashboard/statistics",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    try:
        token = login()
        print("logged in successfully, token obtained.")

        get_dashboard(token)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")