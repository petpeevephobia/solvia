"""
Google Sheets database operations for Solvia authentication system.
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.config import settings
from app.auth.models import UserInDB, UserCreate
import uuid
import re


class GoogleSheetsDB:
    """Google Sheets database interface."""
    
    def __init__(self):
        """Initialize Google Sheets connection or demo mode."""
        self.demo_mode = False
        self.demo_users = []
        self.demo_metrics = []
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 60  # Cache for 60 seconds
        
        # Try to initialize Google Sheets connection
        try:
            self.scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
            self.credentials = Credentials.from_service_account_file(
                settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=self.scope
            )
            self.client = gspread.authorize(self.credentials)
            
            # Open sheets - use sheet1 for both since they're in the same spreadsheet
            self.users_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).sheet1
            self.sessions_sheet = self.client.open_by_key(settings.SESSIONS_SHEET_ID).sheet1
            
            # SEO metrics sheet
            try:
                self.seo_metrics_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet('seo-metrics')
            except gspread.WorksheetNotFound:
                # Create the sheet if it doesn't exist
                self.seo_metrics_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).add_worksheet(
                    title='seo-metrics', 
                    rows=10000, 
                    cols=9
                )
                # Add headers
                self.seo_metrics_sheet.append_row([
                    'email', 'website_url', 'date', 'organic_traffic', 'impressions', 
                    'avg_position', 'ctr', 'seo_score', 'created_at'
                ])
            
            print("Connected to Google Sheets successfully")
            
        except Exception as e:
            print(f"Failed to connect to Google Sheets: {e}")
            print("Running in DEMO MODE with in-memory storage")
            self.demo_mode = True
            
            # Initialize demo data
            self._init_demo_data()
            print(f"[DEBUG] Demo mode initialized with {len(self.demo_users)} users")
            for user in self.demo_users:
                print(f"[DEBUG] Demo user: {user['email']}")
    
    def _get_cached_data(self, key: str):
        """Get data from cache if it's still valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if (datetime.utcnow() - timestamp).seconds < self._cache_ttl:
                return data
            else:
                del self._cache[key]
        return None
    
    def _set_cached_data(self, key: str, data):
        """Store data in cache with timestamp."""
        self._cache[key] = (data, datetime.utcnow())
    
    def get_or_create_sheet(self, sheet_name: str, headers: List[str] = None) -> gspread.Worksheet:
        """Get a worksheet by name, or create it if it doesn't exist."""
        try:
            sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet(sheet_name)
            return sheet
        except gspread.WorksheetNotFound:
            print(f"Worksheet '{sheet_name}' not found, creating it.")
            sheet = self.client.open_by_key(settings.USERS_SHEET_ID).add_worksheet(
                title=sheet_name, 
                rows=1000, 
                cols=len(headers) if headers else 20
            )
            if headers:
                sheet.append_row(headers)
            return sheet
    
    def _init_demo_data(self):
        """Initialize demo data for testing."""
        # Create demo users
        demo_users = [
            {
                'email': 'solviapteltd@gmail.com',
                'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2O',  # "Password1"
                'created_at': '2024-01-01T00:00:00',
                'last_login': '',
                'is_verified': 'TRUE',
                'verification_token': '',
                'reset_token': ''
            }
        ]
        
        for demo_user in demo_users:
            self.demo_users.append(demo_user)
        
        # Create demo metrics
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            demo_metric = {
                'email': 'demo@example.com',
                'date': date.date().isoformat(),
                'organic_traffic': 1000 + (i * 50),
                'impressions': 5000 + (i * 200),
                'avg_position': 15.0 - (i * 0.1),
                'ctr': 2.5 + (i * 0.05),
                'seo_score': 75 + (i * 0.5),
                'created_at': date.isoformat()
            }
            self.demo_metrics.append(demo_metric)
    
    def _find_user_row(self, email: str) -> Optional[int]:
        """Find the row number for a user by email."""
        try:
            cell = self.users_sheet.find(email)
            return cell.row
        except gspread.CellNotFound:
            return None
    
    def create_user(self, user: UserCreate, password_hash: str, verification_token: str) -> bool:
        """Create a new user in the database."""
        if self.demo_mode:
            # Add to demo data
            demo_user = {
                'email': user.email,
                'password_hash': password_hash,
                'created_at': datetime.utcnow().isoformat(),
                'last_login': '',
                'is_verified': 'FALSE',
                'verification_token': verification_token,
                'reset_token': ''
            }
            self.demo_users.append(demo_user)
            return True
        
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
        print(f"[DEBUG] get_user_by_email called with email: '{email}'")
        print(f"[DEBUG] Demo mode: {self.demo_mode}")
        
        if self.demo_mode:
            # Use demo data
            print(f"[DEBUG] Searching in demo users: {[u['email'] for u in self.demo_users]}")
            for user_record in self.demo_users:
                if user_record.get('email') == email:
                    print(f"[DEBUG] Found user in demo data: {email}")
                    return UserInDB(
                        id=str(uuid.uuid4()),
                        email=user_record.get('email'),
                        password_hash=user_record.get('password_hash'),
                        created_at=user_record.get('created_at'),
                        is_verified=user_record.get('is_verified', '').upper() == "TRUE",
                        verification_token=user_record.get('verification_token'),
                        reset_token=user_record.get('reset_token')
                    )
            print(f"[DEBUG] User not found in demo data: {email}")
            return None
        
        try:
            # Check cache first
            cache_key = f"user_{email}"
            cached_user = self._get_cached_data(cache_key)
            if cached_user:
                print(f"[DEBUG] Returning cached user data for: {email}")
                return cached_user
            
            # Get all users as records (dictionary format)
            print(f"[DEBUG] Searching for email: '{email}'")
            all_users = self.users_sheet.get_all_records()
            print(f"[DEBUG] Emails in sheet:")
            for user_record in all_users:
                print(f"  - '{user_record.get('email')}'")
            # Find user by email
            for user_record in all_users:
                if user_record.get('email') == email:
                    print(f"[DEBUG] Match found for email: '{email}'")
                    user = UserInDB(
                        id=str(uuid.uuid4()),  # Generate a UUID for the user
                        email=user_record.get('email'),
                        password_hash=user_record.get('password_hash'),
                        created_at=user_record.get('created_at') if user_record.get('created_at') else datetime.utcnow().isoformat(),
                        is_verified=user_record.get('is_verified', '').upper() == "TRUE",
                        verification_token=user_record.get('verification_token'),
                        reset_token=user_record.get('reset_token')
                    )
                    # Cache the user data
                    self._set_cached_data(cache_key, user)
                    return user
            
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            # If it's a rate limit error, try to return cached data or fall back to demo mode
            if "429" in str(e) or "quota" in str(e).lower():
                print("[WARNING] Google Sheets rate limit exceeded, checking cache")
                cached_user = self._get_cached_data(f"user_{email}")
                if cached_user:
                    return cached_user
                print("[WARNING] No cached data available, switching to demo mode")
                # Switch to demo mode temporarily
                self.demo_mode = True
                return self.get_user_by_email(email)  # Recursive call with demo mode
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
        if self.demo_mode:
            # Update demo data
            for user in self.demo_users:
                if user['email'] == email:
                    user['last_login'] = datetime.utcnow().isoformat()
                    return True
            return False
        
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

    def validate_user_exists(self, email: str) -> bool:
        """Check if user exists in the database."""
        try:
            user = self.get_user_by_email(email)
            return user is not None
        except Exception as e:
            print(f"Error validating user: {e}")
            return False

    def get_user_metrics(self, email: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get user's metrics for last N days."""
        if self.demo_mode:
            # Use demo data
            user_metrics = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for metric in self.demo_metrics:
                if metric['email'] == email:
                    try:
                        metric_date = datetime.fromisoformat(metric['date'])
                        if metric_date >= cutoff_date:
                            user_metrics.append(metric)
                    except ValueError:
                        # Skip invalid dates
                        continue
            
            # Sort by date
            user_metrics.sort(key=lambda x: x['date'])
            return user_metrics
        
        try:
            metrics = self.seo_metrics_sheet.get_all_records()
            user_metrics = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for metric in metrics:
                if metric['email'] == email:
                    try:
                        metric_date = datetime.fromisoformat(metric['date'])
                        if metric_date >= cutoff_date:
                            user_metrics.append(metric)
                    except ValueError:
                        # Skip invalid dates
                        continue
            
            # Sort by date
            user_metrics.sort(key=lambda x: x['date'])
            return user_metrics
            
        except Exception as e:
            print(f"Error getting user metrics: {e}")
            return []

    def get_latest_metrics(self, email: str) -> Optional[Dict[str, Any]]:
        """Get the latest SEO metrics for user."""
        try:
            metrics = self.get_user_metrics(email, days=1)
            if metrics:
                return metrics[-1]  # Return the most recent
            return None
        except Exception as e:
            print(f"Error getting latest metrics: {e}")
            return None

    def get_dashboard_data(self, email: str) -> Dict[str, Any]:
        """Get all data needed for user dashboard."""
        try:
            print(f"[DEBUG] Getting dashboard data for: {email}")  # Debug log
            user = self.get_user_by_email(email)
            metrics = self.get_user_metrics(email, days=30)
            latest_metrics = self.get_latest_metrics(email)
            
            result = {
                'user': user,
                'metrics': metrics,
                'latest_metrics': latest_metrics,
                'total_metrics': len(metrics)
            }
            
            print(f"[DEBUG] Dashboard data result: {result}")  # Debug log
            return result
        except Exception as e:
            print(f"Error getting dashboard data: {e}")
            return {
                'user': None,
                'metrics': [],
                'latest_metrics': None,
                'total_metrics': 0
            }

    def add_user_website(self, email: str, website_url: str) -> bool:
        """Adds or updates a website for a user."""
        if self.demo_mode:
            # In demo mode, we can just assume this works
            return True
            
        try:
            # We can use the user's email to uniquely identify their row.
            # We will add the website to the 'users' sheet.
            # First, find the user's row.
            cell = self.users_sheet.find(email)
            if not cell:
                print(f"[ERROR] Could not find user '{email}' to add website.")
                return False
            
            # Check if 'website_url' column exists, if not, add it.
            headers = self.users_sheet.row_values(1)
            if 'website_url' not in headers:
                self.users_sheet.update_cell(1, len(headers) + 1, 'website_url')
                website_col = len(headers) + 1
            else:
                website_col = headers.index('website_url') + 1

            # Update the website_url for that user's row
            self.users_sheet.update_cell(cell.row, website_col, website_url)
            print(f"[SUCCESS] Added website '{website_url}' for user '{email}'.")
            return True
        except Exception as e:
            print(f"Error adding user website: {e}")
            return False

    def get_user_website(self, email: str) -> Optional[Dict[str, Any]]:
        """Gets the selected website for a user."""
        if self.demo_mode:
            return {"website_url": "https://demo-site.com"}

        try:
            all_users = self.users_sheet.get_all_records()
            for user_record in all_users:
                if user_record.get('email') == email:
                    if user_record.get('website_url'):
                        return {"website_url": user_record.get('website_url')}
                    else:
                        return None
            return None
        except Exception as e:
            print(f"Error getting user website: {e}")
            # If it's a rate limit error, return demo data
            if "429" in str(e) or "quota" in str(e).lower():
                print("[WARNING] Google Sheets rate limit exceeded, using demo data")
                return {"website_url": "https://demo-site.com"}
            return None

    def get_selected_gsc_property(self, email: str) -> str | None:
        """
        Returns the selected GSC property URL for the given user.
        """
        # Check cache first
        cache_key = f"gsc_property_{email}"
        cached_property = self._get_cached_data(cache_key)
        if cached_property:
            print(f"[DEBUG] Returning cached GSC property for: {email}")
            return cached_property
        
        website = self.get_user_website(email)
        if website and website.get("website_url"):
            # Cache the result
            self._set_cached_data(cache_key, website["website_url"])
            return website["website_url"]
        return None


# Create database instance
db = GoogleSheetsDB() 