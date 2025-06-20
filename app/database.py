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
        
        # Open sheets - use sheet1 for both since they're in the same spreadsheet
        self.users_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).sheet1
        self.sessions_sheet = self.client.open_by_key(settings.SESSIONS_SHEET_ID).sheet1
        
        # New sheets for user websites and SEO metrics
        try:
            self.user_websites_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet('user-websites')
        except gspread.WorksheetNotFound:
            # Create the sheet if it doesn't exist
            self.user_websites_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).add_worksheet(
                title='user-websites', 
                rows=1000, 
                cols=6
            )
            # Add headers
            self.user_websites_sheet.append_row([
                'email', 'website_url', 'domain_name', 'is_active', 'created_at', 'updated_at'
            ])
        
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
                    return UserInDB(
                        id=str(uuid.uuid4()),  # Generate a UUID for the user
                        email=user_record.get('email'),
                        password_hash=user_record.get('password_hash'),
                        created_at=user_record.get('created_at') if user_record.get('created_at') else datetime.utcnow().isoformat(),
                        is_verified=user_record.get('is_verified', '').upper() == "TRUE",
                        verification_token=user_record.get('verification_token'),
                        reset_token=user_record.get('reset_token')
                    )
            
            return None
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

    # User-Website Relationship Functions
    def validate_user_exists(self, email: str) -> bool:
        """Check if user exists before adding related data."""
        try:
            user = self.get_user_by_email(email)
            return user is not None
        except Exception as e:
            print(f"Error validating user: {e}")
            return False

    def extract_domain(self, website_url: str) -> str:
        """Extract domain name from website URL."""
        try:
            # Remove protocol
            domain = website_url.replace('https://', '').replace('http://', '')
            # Remove path and query parameters
            domain = domain.split('/')[0]
            # Remove www. if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return website_url

    def validate_website_url(self, website_url: str) -> bool:
        """Validate website URL format."""
        try:
            # Basic URL validation
            pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
            return bool(re.match(pattern, website_url))
        except Exception:
            return False

    def add_user_website(self, email: str, website_url: str) -> bool:
        """Add website for user (relationship)."""
        try:
            # Validate user exists first
            if not self.validate_user_exists(email):
                print(f"User not found: {email}")
                return False
            
            # Validate URL format
            if not self.validate_website_url(website_url):
                print(f"Invalid website URL: {website_url}")
                return False
            
            # Check if user already has a website
            existing_website = self.get_user_website(email)
            if existing_website:
                print(f"User already has a website: {existing_website['website_url']}")
                return False
            
            # Extract domain name
            domain = self.extract_domain(website_url)
            
            # Add to user-websites sheet
            now = datetime.utcnow().isoformat()
            website_data = [
                email, website_url, domain, "TRUE", now, now
            ]
            self.user_websites_sheet.append_row(website_data)
            print(f"Added website {website_url} for user {email}")
            return True
            
        except Exception as e:
            print(f"Error adding user website: {e}")
            return False

    def get_user_website(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user's website (relationship query)."""
        try:
            print(f"[DEBUG] Checking for website for user: {email}")  # Debug log
            websites = self.user_websites_sheet.get_all_records()
            print(f"[DEBUG] Found {len(websites)} website records")  # Debug log
            
            for website in websites:
                print(f"[DEBUG] Checking website: {website}")  # Debug log
                if website['email'] == email and website['is_active'].upper() == "TRUE":
                    print(f"[DEBUG] Found active website for {email}: {website['website_url']}")  # Debug log
                    return website
            
            print(f"[DEBUG] No active website found for {email}")  # Debug log
            return None
        except Exception as e:
            print(f"Error getting user website: {e}")
            return None

    def update_user_website(self, email: str, website_url: str) -> bool:
        """Update user's website URL."""
        try:
            # Validate URL format
            if not self.validate_website_url(website_url):
                print(f"Invalid website URL: {website_url}")
                return False
            
            # Find existing website record
            websites = self.user_websites_sheet.get_all_records()
            for i, website in enumerate(websites, start=2):  # Start from row 2 (skip header)
                if website['email'] == email:
                    # Update website URL and domain
                    domain = self.extract_domain(website_url)
                    now = datetime.utcnow().isoformat()
                    
                    self.user_websites_sheet.update_cell(i, 2, website_url)  # website_url
                    self.user_websites_sheet.update_cell(i, 3, domain)       # domain_name
                    self.user_websites_sheet.update_cell(i, 6, now)          # updated_at
                    
                    print(f"Updated website to {website_url} for user {email}")
                    return True
            
            # If no existing website found, create new one
            return self.add_user_website(email, website_url)
            
        except Exception as e:
            print(f"Error updating user website: {e}")
            return False

    def delete_user_website(self, email: str) -> bool:
        """Delete user's website (soft delete by setting is_active to FALSE)."""
        try:
            websites = self.user_websites_sheet.get_all_records()
            for i, website in enumerate(websites, start=2):  # Start from row 2 (skip header)
                if website['email'] == email:
                    self.user_websites_sheet.update_cell(i, 4, "FALSE")  # is_active
                    print(f"Deleted website for user {email}")
                    return True
            return False
        except Exception as e:
            print(f"Error deleting user website: {e}")
            return False

    # Website-Metrics Relationship Functions
    def validate_website_exists(self, email: str, website_url: str) -> bool:
        """Check if website exists for user before adding metrics."""
        try:
            website = self.get_user_website(email)
            return website is not None and website['website_url'] == website_url
        except Exception as e:
            print(f"Error validating website: {e}")
            return False

    def add_seo_metrics(self, email: str, website_url: str, metrics_data: Dict[str, Any]) -> bool:
        """Add SEO metrics for user's website (relationship)."""
        try:
            # Validate website exists for user
            if not self.validate_website_exists(email, website_url):
                print(f"Website not found for user: {email} - {website_url}")
                return False
            
            # Add to seo-metrics sheet
            now = datetime.utcnow()
            metrics_row = [
                email, website_url, now.date().isoformat(),
                metrics_data.get('organic_traffic', 0),
                metrics_data.get('impressions', 0),
                metrics_data.get('avg_position', 0),
                metrics_data.get('ctr', 0),
                metrics_data.get('seo_score', 0),
                now.isoformat()
            ]
            self.seo_metrics_sheet.append_row(metrics_row)
            print(f"Added SEO metrics for {email} - {website_url}")
            return True
            
        except Exception as e:
            print(f"Error adding SEO metrics: {e}")
            return False

    def get_user_metrics(self, email: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get user's metrics for last N days (relationship query)."""
        try:
            website = self.get_user_website(email)
            if not website:
                return []
            
            metrics = self.seo_metrics_sheet.get_all_records()
            user_metrics = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for metric in metrics:
                if (metric['email'] == email and 
                    metric['website_url'] == website['website_url']):
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
            website = self.get_user_website(email)
            metrics = self.get_user_metrics(email, days=30)
            latest_metrics = self.get_latest_metrics(email)
            
            result = {
                'user': user,
                'website': website,
                'metrics': metrics,
                'latest_metrics': latest_metrics,
                'has_website': website is not None,
                'total_metrics': len(metrics)
            }
            
            print(f"[DEBUG] Dashboard data result: {result}")  # Debug log
            return result
        except Exception as e:
            print(f"Error getting dashboard data: {e}")
            return {
                'user': None,
                'website': None,
                'metrics': [],
                'latest_metrics': None,
                'has_website': False,
                'total_metrics': 0
            }


# Create database instance
db = GoogleSheetsDB() 