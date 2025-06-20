#!/usr/bin/env python3
"""
Test script for Solvia authentication and dashboard flow.
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def test_health():
    """Test if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://localhost:8000")
        return False

def test_registration():
    """Test user registration."""
    email = f"testuser_{int(time.time())}@example.com"
    password = "TestPass123"
    
    data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/register", json=data)
        if response.status_code == 201:
            print(f"✅ Registration successful for {email}")
            return email, password
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None, None

def test_login(email, password):
    """Test user login."""
    data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{API_BASE}/auth/login", json=data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"✅ Login successful for {email}")
            return token
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_dashboard_access(token):
    """Test dashboard access with token."""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        if response.status_code == 200:
            print("✅ Dashboard access successful")
            return True
        else:
            print(f"❌ Dashboard access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard access error: {e}")
        return False

def test_user_info(token):
    """Test getting user info with token."""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{API_BASE}/auth/me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ User info retrieved: {user_data['email']}")
            return True
        else:
            print(f"❌ User info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ User info error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Solvia Authentication and Dashboard Flow")
    print("=" * 50)
    
    # Test 1: Server health
    if not test_health():
        return
    
    print("\n📝 Testing Registration and Login Flow")
    print("-" * 40)
    
    # Test 2: Registration
    email, password = test_registration()
    if not email:
        return
    
    # Test 3: Login
    token = test_login(email, password)
    if not token:
        return
    
    print("\n🔐 Testing Authenticated Endpoints")
    print("-" * 40)
    
    # Test 4: User info
    test_user_info(token)
    
    # Test 5: Dashboard access
    test_dashboard_access(token)
    
    print("\n🎉 All tests completed!")
    print("\n📋 Next steps:")
    print("1. Open http://localhost:8000/ui in your browser")
    print("2. Register with a new account or login with existing credentials")
    print("3. You'll be automatically redirected to the dashboard")
    print("4. Explore the dashboard features and UI")

if __name__ == "__main__":
    main() 