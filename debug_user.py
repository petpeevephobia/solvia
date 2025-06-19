#!/usr/bin/env python3
"""
Debug script to check user data and test password verification.
"""
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from app.auth.utils import verify_password, get_password_hash

# Load environment variables
load_dotenv()

def debug_user():
    """Debug user data and password verification."""
    try:
        # Get credentials file path
        credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
        users_sheet_id = os.getenv('USERS_SHEET_ID')
        
        print(f"🔍 Debugging user: solviapteltd@gmail.com")
        print(f"Credentials file: {credentials_file}")
        print(f"Users Sheet ID: {users_sheet_id}")
        
        # Check if credentials file exists
        if not os.path.exists(credentials_file):
            print(f"❌ Credentials file not found: {credentials_file}")
            return
        
        # Initialize Google Sheets
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        credentials = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Open users sheet
        users_spreadsheet = client.open_by_key(users_sheet_id)
        users_sheet = users_spreadsheet.sheet1
        
        print("✅ Google Sheets connection successful!")
        
        # Get all users
        all_users = users_sheet.get_all_records()
        print(f"📊 Total users in sheet: {len(all_users)}")
        
        # Find the specific user
        target_email = "solviapteltd@gmail.com"
        user_found = None
        row_num = None
        
        for idx, user in enumerate(all_users, start=2):  # start=2 for header row
            if user.get('email') == target_email:
                user_found = user
                row_num = idx
                break
        
        if not user_found:
            print(f"❌ User {target_email} not found in Google Sheets")
            return
        
        print(f"✅ User found at row {row_num}")
        print(f"📝 User data:")
        print(f"  Email: {user_found.get('email')}")
        print(f"  Password Hash: {user_found.get('password_hash')[:50]}...")
        print(f"  Created At: {user_found.get('created_at')}")
        print(f"  Last Login: {user_found.get('last_login')}")
        print(f"  Is Verified: {user_found.get('is_verified')}")
        print(f"  Verification Token: {user_found.get('verification_token')}")
        print(f"  Reset Token: {user_found.get('reset_token')}")
        
        # Test password verification
        test_password = "TestPassword123"
        stored_hash = user_found.get('password_hash')
        
        if not stored_hash:
            print("❌ No password hash found for user")
            return
        
        print(f"\n🔐 Testing password verification...")
        print(f"Test password: {test_password}")
        print(f"Stored hash: {stored_hash[:50]}...")
        
        # Test verification
        is_valid = verify_password(test_password, stored_hash)
        print(f"Password verification result: {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        # Test creating a new hash
        new_hash = get_password_hash(test_password)
        print(f"New hash for same password: {new_hash[:50]}...")
        
        # Test if new hash matches
        new_is_valid = verify_password(test_password, new_hash)
        print(f"New hash verification: {'✅ Valid' if new_is_valid else '❌ Invalid'}")
        
        # Check if verification is required
        is_verified = user_found.get('is_verified', '').upper() == 'TRUE'
        print(f"\n📧 Email verification status: {'✅ Verified' if is_verified else '❌ Not Verified'}")
        
        if not is_verified:
            print("💡 User needs to verify email before login")
        else:
            print("✅ User is verified and should be able to login")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_user() 