#!/usr/bin/env python3
"""
Test script to check what the registration endpoint returns.
"""
import requests
import json

def test_registration():
    """Test the registration endpoint."""
    url = "http://localhost:8000/auth/register"
    data = {
        "email": "solviapteltd@gmail.com",
        "password": "TestPassword123"
    }
    
    print(f"🔍 Testing registration endpoint...")
    print(f"URL: {url}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, json=data)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Response Text: {response.text[:500]}...")  # First 500 chars
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ Success!")
            try:
                json_data = response.json()
                print(f"JSON Response: {json_data}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
        else:
            print("❌ Error response")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")

if __name__ == "__main__":
    test_registration()