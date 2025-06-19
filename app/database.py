"""
Google Sheets database operations for Solvia authentication system.
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings
from app.auth.models import UserInDB, UserCreate


class GoogleSheetsDB:
    """Google Sheets database interface."""
    
    def __init__(self):
        """Initialize Google Sheets connection."""
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        self.credentials = Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=self.scope
        )
        self.client = gspread.authorize(self.credentials)
        
        # Open sheets
        self.users_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet('users')
        self.sessions_sheet = self.client.open_by_key(settings.SESSIONS_SHEET_ID).worksheet('sessions')
    
    def _find_user_row(self, email: str) -> Optional[int]:
        """Find the row number for a user by email."""
        try:
            cell = self.users_sheet.find(email)
            return cell.row
        except gspread.CellNotFound:
            return None
    
    def create_user(self, user: UserCreate, password_hash: str, verification_token: str) -> bool:
        """Create a new user in the database."""
        try:
            now = datetime.utcnow().isoformat()
            user_data = [
                user.email,
                password_hash,
                now,  # created_at
                "",   # last_login
                "FALSE",  # is_verified
                verification_token,  # verification_token
                ""   # reset_token
            ]
            self.users_sheet.append_row(user_data)
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        try:
            row = self._find_user_row(email)
            if row is None:
                return None
            
            user_data = self.users_sheet.row_values(row)
            if len(user_data) < 7:
                return None
            
            return UserInDB(
                email=user_data[0],
                password_hash=user_data[1],
                created_at=datetime.fromisoformat(user_data[2]) if user_data[2] else datetime.utcnow(),
                last_login=datetime.fromisoformat(user_data[3]) if user_data[3] else None,
                is_verified=user_data[4].upper() == "TRUE",
                verification_token=user_data[5] if user_data[5] else None,
                reset_token=user_data[6] if user_data[6] else None
            )
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_user_verification(self, email: str, is_verified: bool = True) -> bool:
        """Update user verification status."""
        try:
            row = self._find_user_row(email)
            if row is None:
                return False
            
            # Update is_verified column (5th column, index 4)
            self.users_sheet.update_cell(row, 5, "TRUE" if is_verified else "FALSE")
            
            # Clear verification token
            self.users_sheet.update_cell(row, 6, "")
            return True
        except Exception as e:
            print(f"Error updating user verification: {e}")
            return False
    
    def update_last_login(self, email: str) -> bool:
        """Update user's last login timestamp."""
        try:
            row = self._find_user_row(email)
            if row is None:
                return False
            
            now = datetime.utcnow().isoformat()
            self.users_sheet.update_cell(row, 4, now)  # last_login column
            return True
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False
    
    def set_reset_token(self, email: str, reset_token: str) -> bool:
        """Set password reset token for user."""
        try:
            row = self._find_user_row(email)
            if row is None:
                return False
            
            self.users_sheet.update_cell(row, 7, reset_token)  # reset_token column
            return True
        except Exception as e:
            print(f"Error setting reset token: {e}")
            return False
    
    def update_password(self, email: str, new_password_hash: str) -> bool:
        """Update user's password."""
        try:
            row = self._find_user_row(email)
            if row is None:
                return False
            
            self.users_sheet.update_cell(row, 2, new_password_hash)  # password_hash column
            self.users_sheet.update_cell(row, 7, "")  # clear reset_token
            return True
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    
    def create_session(self, user_email: str, session_token: str, expires_at: datetime) -> bool:
        """Create a new session."""
        try:
            session_data = [
                user_email,
                session_token,
                datetime.utcnow().isoformat(),  # created_at
                expires_at.isoformat()  # expires_at
            ]
            self.sessions_sheet.append_row(session_data)
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def delete_session(self, session_token: str) -> bool:
        """Delete a session by token."""
        try:
            cell = self.sessions_sheet.find(session_token)
            self.sessions_sheet.delete_rows(cell.row)
            return True
        except gspread.CellNotFound:
            return False
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        try:
            now = datetime.utcnow()
            all_sessions = self.sessions_sheet.get_all_records()
            expired_rows = []
            
            for i, session in enumerate(all_sessions, start=2):  # Start from row 2 (skip header)
                try:
                    expires_at = datetime.fromisoformat(session['expires_at'])
                    if expires_at < now:
                        expired_rows.append(i)
                except (ValueError, KeyError):
                    # Invalid date format, remove the row
                    expired_rows.append(i)
            
            # Delete expired rows (in reverse order to maintain indices)
            for row in reversed(expired_rows):
                self.sessions_sheet.delete_rows(row)
            
            return len(expired_rows)
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            return 0


# Create database instance
db = GoogleSheetsDB() 