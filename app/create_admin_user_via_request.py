import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@thunder.com"
ADMIN_PASSWORD = "admin@1234"

def create_admin_user(email: str, password: str, role: str = "super_admin"):
    url = f"{BASE_URL}/auth/register"
    payload = {
        "email": email,
        "password": password,
        "role": role,
        "is_active": True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200 or response.status_code == 201:
        print(f"Admin user '{email}' created successfully.")
        print("Response:", response.json())
    else:
        print(f"Failed to create admin user '{email}'. Status code: {response.status_code}")
        print("Response:", response.text)

if __name__ == "__main__":
    create_admin_user(ADMIN_EMAIL, ADMIN_PASSWORD)