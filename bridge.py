#!/usr/bin/env python3
"""
Simplified SMS Server using Flask
Install with: pip install flask requests flask-cors
Run with: python simple_sms_server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# BulkSMS API configuration
BULKSMS_URI = "https://api.bulksms.com/v1/messages"
USERNAME = "juniorflamebet"
PASSWORD = "Mauricesitwala@12!"

@app.route('/send-sms', methods=['POST'])
def send_sms():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        phone_number = data.get('to')
        message_body = data.get('body')
        
        if not phone_number or not message_body:
            return jsonify({
                "success": False, 
                "error": "Missing 'to' or 'body' parameter"
            }), 400
        
        # Prepare BulkSMS API request
        sms_data = {
            "to": [phone_number],  # BulkSMS expects an array
            "body": message_body,
            "encoding": "UNICODE",
            "longMessageMaxParts": "30",
        }
        
        # Encode credentials
        credentials = f"{USERNAME}:{PASSWORD}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        # Headers for BulkSMS API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        print(f"📱 Sending SMS to {phone_number}: {message_body[:50]}...")
        
        # Make request to BulkSMS API
        response = requests.post(
            BULKSMS_URI,
            json=sms_data,
            headers=headers,
            timeout=30
        )
        
        # Handle BulkSMS response
        if response.status_code in [200, 201]:
            print(f"✅ SMS sent successfully to {phone_number}")
            return jsonify({
                "success": True,
                "message": f"SMS sent successfully to {phone_number}",
                "bulksms_response": response.text
            })
        else:
            error_msg = f"BulkSMS API error: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Server is running", "endpoint": "/send-sms"})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SMS Server Starting with Flask...")
    print("📍 Server will run on http://localhost:8000")
    print("📱 SMS endpoint: http://localhost:8000/send-sms")
    print("🏥 Health check: http://localhost:8000/health")
    print("=" * 60)
    print("💡 Test with curl:")
    print('curl -X POST http://localhost:8000/send-sms \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"to": "+27817584591", "body": "Hello!"}\'')
    print("=" * 60)
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8000, debug=True)