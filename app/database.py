"""
Google Sheets database operations for Solvia authentication system.
"""
import gspread
from gspread.exceptions import WorksheetNotFound
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
        self.demo_reports = []  # Initialize demo reports storage
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
            
            # Open sheets - users in Sheet1, sessions in separate worksheet
            self.users_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).sheet1
            
            # Sessions sheet - create if doesn't exist
            try:
                self.sessions_sheet = self.client.open_by_key(settings.SESSIONS_SHEET_ID).worksheet('sessions')
            except WorksheetNotFound:
                # Create the sessions sheet if it doesn't exist
                self.sessions_sheet = self.client.open_by_key(settings.SESSIONS_SHEET_ID).add_worksheet(
                    title='sessions', 
                    rows=10000, 
                    cols=4
                )
                # Add headers
                self.sessions_sheet.append_row([
                    'user_email', 'session_token', 'created_at', 'expires_at'
                ])
            
            # SEO metrics sheet
            try:
                self.seo_metrics_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet('seo-metrics')
            except WorksheetNotFound:
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
            
            # SEO reports sheet for storing generated reports
            try:
                self.seo_reports_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet('seo-reports')
            except WorksheetNotFound:
                # Create the sheet if it doesn't exist
                self.seo_reports_sheet = self.client.open_by_key(settings.USERS_SHEET_ID).add_worksheet(
                    title='seo-reports', 
                    rows=10000, 
                    cols=10
                )
                # Add headers
                self.seo_reports_sheet.append_row([
                    'report_id', 'email', 'website_url', 'business_model', 'report_data', 
                    'total_recommendations', 'quick_wins_count', 'avg_priority_score', 
                    'generated_at', 'expires_at'
                ])
            
            print("Connected to Google Sheets successfully")
            
        except Exception as e:
            print(f"Failed to connect to Google Sheets: {e}")
            print(f"[ERROR] Credentials file: {settings.GOOGLE_SHEETS_CREDENTIALS_FILE}")
            print(f"[ERROR] Users Sheet ID: {settings.USERS_SHEET_ID}")
            print(f"[ERROR] Sessions Sheet ID: {settings.SESSIONS_SHEET_ID}")
            print("Running in DEMO MODE with in-memory storage")
            self.demo_mode = True
            
            # Initialize demo data
            self._init_demo_data()
            print(f"[DEBUG] Demo mode initialized with {len(self.demo_users)} users")
            for user in self.demo_users:
                print(f"[DEBUG] Demo user: {user['email']}")
        
        # Perform periodic cleanup tasks
        self._perform_cleanup_tasks()
    
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
    
    def _perform_cleanup_tasks(self):
        """Perform periodic cleanup tasks - only once per day."""
        # Check if cleanup has already been performed today using a file-based lock
        import os
        import tempfile
        
        today = datetime.utcnow().date().isoformat()
        lock_file = os.path.join(tempfile.gettempdir(), f"solvia_cleanup_{today}.lock")
        
        # Check if cleanup already performed today
        if os.path.exists(lock_file):
            try:
                # Check if lock file is from today
                lock_mtime = datetime.fromtimestamp(os.path.getmtime(lock_file)).date()
                if lock_mtime == datetime.utcnow().date():
                    print(f"[DEBUG] Cleanup already performed today ({today}), skipping")
                    return
            except (OSError, ValueError):
                # If we can't read the lock file, proceed with cleanup
                pass
        
        print(f"[DEBUG] Performing daily cleanup tasks for {today}")
        
        try:
            # Cleanup expired sessions
            sessions_cleaned = self.cleanup_expired_sessions()
            print(f"[DEBUG] Cleaned {sessions_cleaned} expired sessions")
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            
        try:
            # Cleanup expired dashboard cache (older than 7 days)  
            cache_cleaned = self.cleanup_dashboard_cache(days_old=7)
            print(f"[DEBUG] Cleaned {cache_cleaned} expired dashboard cache entries")
        except Exception as e:
            print(f"[DEBUG] Warning: Could not cleanup expired dashboard cache: {e}")
            
        try:
            # Cleanup expired reports (older than 30 days)
            reports_cleaned = self.cleanup_expired_reports()
            print(f"[INFO] Cleaned up {reports_cleaned} expired SEO reports")
        except Exception as e:
            print(f"[DEBUG] Warning: Could not cleanup expired reports: {e}")
            
        # Create lock file to mark cleanup as completed for today
        try:
            with open(lock_file, 'w') as f:
                f.write(f"Cleanup completed at {datetime.utcnow().isoformat()}")
            print(f"[DEBUG] Daily cleanup completed for {today}")
        except Exception as e:
            print(f"[DEBUG] Warning: Could not create cleanup lock file: {e}")
    
    def get_or_create_sheet(self, sheet_name: str, headers: List[str] = None) -> gspread.Worksheet:
        """Get a worksheet by name, or create it if it doesn't exist."""
        if self.demo_mode:
            print(f"[DEBUG] Database in demo mode, cannot access sheet: {sheet_name}")
            return None
            
        try:
            sheet = self.client.open_by_key(settings.USERS_SHEET_ID).worksheet(sheet_name)
            return sheet
        except WorksheetNotFound:
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
                'password_hash': '$2b$12$kCnUogTNLWFUEgIgEu.5QOjqG3r96qKkBTXKFuAJT9TQc7lJ4JR4C',  # "Password1"
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
                'organic_traffic': 0,
                'impressions': 0,
                'avg_position': 0,
                'ctr': 0,
                'seo_score': 0,
                'created_at': date.isoformat()
            }
            self.demo_metrics.append(demo_metric)
    
    def _find_user_row(self, email: str) -> Optional[int]:
        """Find the row number for a user by email."""
        try:
            cell = self.users_sheet.find(email)
            if cell:
                return cell.row
                return None
        except Exception:
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
            
            # Use batch update for both columns instead of individual updates
            values = [["TRUE" if is_verified else "FALSE", ""]]  # is_verified, verification_token
            self.users_sheet.update(f'E{row}:F{row}', values)
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
            
            # Use batch update - update password hash and clear reset token
            self.users_sheet.batch_update([
                {'range': f'B{row}', 'values': [[new_password_hash]]},  # password_hash column
                {'range': f'G{row}', 'values': [[""]]}  # reset_token column
            ])
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
            if cell:
                self.sessions_sheet.delete_rows(cell.row)
                return True
                return False
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        # Check if we're in demo mode or don't have sessions sheet
        if self.demo_mode or not hasattr(self, 'sessions_sheet'):
            return 0
            
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
            
            # Use batch delete operation instead of individual deletes
            if expired_rows:
                # Group consecutive rows for batch deletion
                row_ranges = []
                start = expired_rows[0]
                end = expired_rows[0]
                
                for row in expired_rows[1:]:
                    if row == end + 1:
                        end = row
                    else:
                        row_ranges.append((start, end))
                        start = end = row
                row_ranges.append((start, end))
                
                # Delete in reverse order to maintain row indices
                for start, end in reversed(row_ranges):
                    if start == end:
                        self.sessions_sheet.delete_rows(start)
                    else:
                        self.sessions_sheet.delete_rows(start, end)
            
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
            # Return demo website for the demo user
            if email == 'solviapteltd@gmail.com':
                # Check if user has selected a specific GSC property format
                cache_key = f"gsc_property_{email}"
                cached_property = self._get_cached_data(cache_key)
                if cached_property:
                    return {"website_url": cached_property}
                # Default to the domain property format used in GSC
                return {"website_url": "sc-domain:thenadraagency.com"}
            return {"website_url": ""}

        try:
            # Check cache first
            cache_key = f"website_{email}"
            cached_website = self._get_cached_data(cache_key)
            if cached_website:
                return cached_website
            
            all_users = self.users_sheet.get_all_records()
            for user_record in all_users:
                if user_record.get('email') == email:
                    website_url = user_record.get('website_url', '').strip()
                    if website_url:
                        result = {"website_url": website_url}
                        # Cache the result
                        self._set_cached_data(cache_key, result)
                        return result
                    else:
                        # User exists but no website URL set
                        return None
            
            # User not found
            print(f"[WARNING] User not found in sheets: {email}")
            return None
            
        except Exception as e:
            print(f"Error getting user website: {e}")
            # If it's a rate limit error, return empty data
            if "429" in str(e) or "quota" in str(e).lower():
                print("[WARNING] Google Sheets rate limit exceeded, using empty data")
                return {"website_url": ""}
            return None

    def get_selected_gsc_property(self, email: str) -> str | None:
        """
        Returns the selected GSC property URL for the given user.
        """
        print(f"[DEBUG] get_selected_gsc_property called for: {email}")
        
        # Check cache first
        cache_key = f"gsc_property_{email}"
        cached_property = self._get_cached_data(cache_key)
        if cached_property:
            print(f"[DEBUG] Returning cached GSC property for {email}: {cached_property}")
            return cached_property
        
        website = self.get_user_website(email)
        print(f"[DEBUG] get_user_website returned for {email}: {website}")
        
        if website and website.get("website_url"):
            website_url = website["website_url"]
            print(f"[DEBUG] Caching GSC property for {email}: {website_url}")
            # Cache the result
            self._set_cached_data(cache_key, website_url)
            return website_url
        
        print(f"[DEBUG] No GSC property found for {email}")
        return None

    def store_seo_report(self, email: str, website_url: str, report_data: Dict[str, Any]) -> str:
        """
        Store a generated SEO report for a user.
        Returns the report_id for future retrieval.
        """
        import json
        
        # Generate unique report ID
        report_id = f"{email}_{website_url}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        report_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', report_id)  # Clean special chars
        
        # Extract summary data from report
        analysis = report_data.get('analysis', {})
        total_recommendations = len(analysis.get('prioritized_recommendations', []))
        quick_wins_count = len(analysis.get('quick_wins', []))
        
        # Calculate average priority score
        avg_priority_score = 0
        if analysis.get('prioritized_recommendations'):
            scores = [rec.get('priority_score', 0) for rec in analysis['prioritized_recommendations']]
            avg_priority_score = round(sum(scores) / len(scores), 2) if scores else 0
        
        # Set expiration (30 days from now)
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        if self.demo_mode:
            # Store in demo data
            demo_report = {
                'report_id': report_id,
                'email': email,
                'website_url': website_url,
                'business_model': report_data.get('business_model', ''),
                'report_data': json.dumps(report_data),
                'total_recommendations': total_recommendations,
                'quick_wins_count': quick_wins_count,
                'avg_priority_score': avg_priority_score,
                'generated_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at
            }
            self.demo_reports.append(demo_report)
            print(f"[DEBUG] Stored report in demo mode: {report_id}")
            return report_id
        
        try:
            # Store in Google Sheets
            report_row = [
                report_id,
                email,
                website_url,
                report_data.get('business_model', ''),
                json.dumps(report_data),  # Store entire report as JSON string
                total_recommendations,
                quick_wins_count,
                avg_priority_score,
                datetime.utcnow().isoformat(),
                expires_at
            ]
            
            self.seo_reports_sheet.append_row(report_row)
            print(f"[SUCCESS] Stored SEO report: {report_id} for user: {email}")
            
            # Clear cache for this user's reports
            cache_key = f"reports_{email}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            return report_id
            
        except Exception as e:
            print(f"[ERROR] Failed to store SEO report: {e}")
            return None

    def get_user_reports(self, email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get all SEO reports for a user, ordered by most recent first.
        """
        # Check cache first
        cache_key = f"reports_{email}"
        cached_reports = self._get_cached_data(cache_key)
        if cached_reports:
            return cached_reports[:limit]
        
        if self.demo_mode:
            # Use demo data
            user_reports = [report for report in self.demo_reports if report['email'] == email]
            user_reports.sort(key=lambda x: x['generated_at'], reverse=True)
            self._set_cached_data(cache_key, user_reports)
            return user_reports[:limit]
        
        try:
            all_reports = self.seo_reports_sheet.get_all_records()
            user_reports = []
            
            for report in all_reports:
                if report['email'] == email:
                    # Check if report is expired
                    try:
                        expires_at = datetime.fromisoformat(report['expires_at'])
                        if expires_at > datetime.utcnow():
                            user_reports.append(report)
                    except (ValueError, KeyError):
                        # Skip reports with invalid expiration dates
                        continue
            
            # Sort by generated_at (most recent first)
            user_reports.sort(key=lambda x: x['generated_at'], reverse=True)
            
            # Cache the results
            self._set_cached_data(cache_key, user_reports)
            
            return user_reports[:limit]
            
        except Exception as e:
            print(f"[ERROR] Failed to get user reports: {e}")
            return []

    def get_report_by_id(self, report_id: str, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific report by ID (with email verification for security).
        """
        if self.demo_mode:
            # Search demo data
            for report in self.demo_reports:
                if report['report_id'] == report_id and report['email'] == email:
                    # Check if expired
                    try:
                        expires_at = datetime.fromisoformat(report['expires_at'])
                        if expires_at > datetime.utcnow():
                            return report
                    except (ValueError, KeyError):
                        pass
            return None
        
        try:
            all_reports = self.seo_reports_sheet.get_all_records()
            
            for report in all_reports:
                if report['report_id'] == report_id and report['email'] == email:
                    # Check if expired
                    try:
                        expires_at = datetime.fromisoformat(report['expires_at'])
                        if expires_at > datetime.utcnow():
                            return report
                    except (ValueError, KeyError):
                        continue
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to get report by ID: {e}")
            return None

    def cleanup_expired_reports(self) -> int:
        """
        Remove expired SEO reports and return count of removed reports.
        """
        if self.demo_mode:
            # Clean demo data
            now = datetime.utcnow()
            initial_count = len(self.demo_reports)
            
            self.demo_reports = [
                report for report in self.demo_reports
                if datetime.fromisoformat(report['expires_at']) > now
            ]
            
            return initial_count - len(self.demo_reports)
        
        # Check if we have the reports sheet
        if not hasattr(self, 'seo_reports_sheet'):
            return 0
        
        try:
            now = datetime.utcnow()
            all_reports = self.seo_reports_sheet.get_all_records()
            expired_rows = []
            
            for i, report in enumerate(all_reports, start=2):  # Start from row 2 (skip header)
                try:
                    expires_at = datetime.fromisoformat(report['expires_at'])
                    if expires_at < now:
                        expired_rows.append(i)
                except (ValueError, KeyError):
                    # Invalid date format, remove the row
                    expired_rows.append(i)
            
            # Use batch delete operation instead of individual deletes
            if expired_rows:
                # Group consecutive rows for batch deletion
                row_ranges = []
                start = expired_rows[0]
                end = expired_rows[0]
                
                for row in expired_rows[1:]:
                    if row == end + 1:
                        end = row
                    else:
                        row_ranges.append((start, end))
                        start = end = row
                row_ranges.append((start, end))
                
                # Delete in reverse order to maintain row indices
                for start, end in reversed(row_ranges):
                    if start == end:
                        self.seo_reports_sheet.delete_rows(start)
                    else:
                        self.seo_reports_sheet.delete_rows(start, end)
            
            return len(expired_rows)
            
        except Exception as e:
            print(f"[ERROR] Failed to cleanup expired reports: {e}")
            return 0

    def store_temp_data(self, key: str, data: Dict[str, Any]) -> bool:
        """Store temporary data for 30-day comparisons."""
        if self.demo_mode:
            # Store in memory cache for demo mode
            self._set_cached_data(f"temp_{key}", data)
            return True
        
        try:
            # Get or create temp-data worksheet
            temp_sheet = self.get_or_create_sheet('temp-data', ['key', 'data', 'created_at'])
            
            # Convert data to JSON string
            import json
            data_json = json.dumps(data)
            current_time = datetime.utcnow().isoformat()
            
            # Check if key already exists
            cell = temp_sheet.find(key)
            if cell:
                # Update existing row
                temp_sheet.update(f'B{cell.row}:C{cell.row}', [[data_json, current_time]])
            else:
                # Add new row
                temp_sheet.append_row([key, data_json, current_time])
            
            return True
            
            
        except Exception as e:
            print(f"[ERROR] Error storing temp data: {e}")
            return False
    
    def get_temp_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get temporary data for 30-day comparisons."""
        if self.demo_mode:
            # Get from memory cache for demo mode
            return self._get_cached_data(f"temp_{key}")
        
        try:
            # Get temp-data worksheet
            temp_sheet = self.get_or_create_sheet('temp-data', ['key', 'data', 'created_at'])
            
            # Find the key
            cell = temp_sheet.find(key)
            if cell:
                row_data = temp_sheet.row_values(cell.row)
                if len(row_data) >= 2:
                    import json
                    return json.loads(row_data[1])  # data column
                
                return None
            
        except Exception as e:
            print(f"[ERROR] Error getting temp data: {e}")
            return None

    def store_dashboard_cache(self, email: str, website_url: str, dashboard_data: Dict[str, Any]) -> bool:
        """Store complete dashboard data cache for same-day retrieval."""
        import json
        import re

        # Ensure metrics includes a summary field
        metrics = dashboard_data.get('metrics', {})
        ai_insights = dashboard_data.get('ai_insights', {})
        summary = metrics.get('summary', {})

        # Copy key visibility metrics from ai_insights.visibility_performance.metrics
        vp_metrics = ai_insights.get('visibility_performance', {}).get('metrics', {})
        summary['total_impressions'] = vp_metrics.get('impressions', {}).get('current_value', 0)
        summary['total_clicks'] = vp_metrics.get('clicks', {}).get('current_value', 0)
        summary['avg_ctr'] = vp_metrics.get('ctr', {}).get('current_value', 0)
        summary['avg_position'] = vp_metrics.get('avg_position', {}).get('current_value', 0)

        # Fallback to zeros if still missing
        for k in ['total_impressions', 'total_clicks', 'avg_ctr', 'avg_position']:
            if summary.get(k) is None:
                summary[k] = 0
        metrics['summary'] = summary
        dashboard_data['metrics'] = metrics

        # Ensure ai_insights.visibility_performance.metrics always includes impressions, clicks, ctr, and avg_position fields, even if their values are zero
        vp = ai_insights.get('visibility_performance', {})
        vp_metrics = vp.get('metrics', {})
        for key in ['impressions', 'clicks', 'ctr', 'avg_position']:
            if key not in vp_metrics or not isinstance(vp_metrics[key], dict):
                vp_metrics[key] = {"current_value": 0}
        vp['metrics'] = vp_metrics
        ai_insights['visibility_performance'] = vp
        dashboard_data['ai_insights'] = ai_insights

        # Create cache key with today's date
        today = datetime.utcnow().strftime('%Y-%m-%d')
        cache_key = f"dashboard_{email}_{website_url}_{today}"
        cache_key = re.sub(r'[^a-zA-Z0-9_.-]', '_', cache_key)  # Clean special chars
        print(f"[DEBUG][STORE] email: {email}, website_url: {website_url}, today: {today}, cache_key: {cache_key}")
        print(f"[DEBUG][STORE] FULL cache_key: {cache_key}")
        
        # Add metadata to dashboard data
        cached_data = {
            'dashboard_data': dashboard_data,
            'cached_at': datetime.utcnow().isoformat(),
            'cache_date': today,
            'email': email,
            'website_url': website_url
        }
        
        if self.demo_mode:
            # Store in memory cache for demo mode
            self._set_cached_data(f"dashboard_cache_{cache_key}", cached_data)
            print(f"[DEBUG] Stored dashboard cache in demo mode: {cache_key}")
            return True
        
        try:
            # Get or create dashboard-cache worksheet
            cache_sheet = self.get_or_create_sheet('dashboard-cache', [
                'cache_key', 'email', 'website_url', 'cache_date', 'dashboard_data', 'cached_at'
            ])
            
            if not cache_sheet:  # Demo mode fallback
                self._set_cached_data(f"dashboard_cache_{cache_key}", cached_data)
                return True
            
            # Convert data to JSON string
            data_json = json.dumps(cached_data)
            current_time = datetime.utcnow().isoformat()
            
            # Check if cache key already exists (update existing)
            try:
                cell = cache_sheet.find(cache_key)
                if cell:
                    # Update existing row
                    cache_sheet.update(f'E{cell.row}:F{cell.row}', [[data_json, current_time]])
                    print(f"[DEBUG] Updated existing dashboard cache: {cache_key}")
                else:
                    # Add new row
                    cache_sheet.append_row([
                        cache_key, email, website_url, today, data_json, current_time
                    ])
                    print(f"[DEBUG] Created new dashboard cache: {cache_key}")
            except:
                # If find fails, just append new row
                cache_sheet.append_row([
                    cache_key, email, website_url, today, data_json, current_time
                ])
                print(f"[DEBUG] Created new dashboard cache: {cache_key}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error storing dashboard cache: {e}")
            return False

    def get_dashboard_cache(self, email: str, website_url: str) -> Optional[Dict[str, Any]]:
        """Get the most recent cached dashboard data for the user/property, regardless of date. Always ensure metrics.summary exists."""
        import json
        import re

        # Generate the base cache key prefix (without date)
        base_key = f"dashboard_{email}_{website_url}_"
        base_key = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_key)
        print(f"[DEBUG][LOOKUP] base_key: {base_key}")

        if self.demo_mode:
            # Find the most recent cache in memory
            matching = [
                (k, v) for k, v in self._cache.items()
                if k.startswith(f"dashboard_cache_{base_key}")
            ]
            if not matching:
                return None
            # Sort by cached_at if available, else by insertion order
            most_recent = max(matching, key=lambda item: item[1][0].get('cached_at', ''))
            return most_recent[1][0].get('dashboard_data')

        try:
            cache_sheet = self.get_or_create_sheet('dashboard-cache', [
                'cache_key', 'email', 'website_url', 'cache_date', 'dashboard_data', 'cached_at'
            ])
            if not cache_sheet:
                return None
            all_records = cache_sheet.get_all_records()
            matching_records = [
                record for record in all_records
                if record.get('cache_key', '').startswith(base_key)
            ]
            if not matching_records:
                print(f"[DEBUG][LOOKUP] No matching cache found for base_key: {base_key}")
                return None
            # Find the most recent by cache_date or cached_at
            def get_sort_key(r):
                return r.get('cache_date') or r.get('cached_at') or ''
            most_recent = max(matching_records, key=get_sort_key)
            print(f"[DEBUG][LOOKUP] Found most recent cache: {most_recent.get('cache_key')}")
            cached_data = json.loads(most_recent['dashboard_data'])
            
            # Ensure metrics.summary exists
            metrics = cached_data.get('metrics', {})
            if 'summary' not in metrics or not metrics['summary']:
                summary = None
                if 'originalApiData' in cached_data and cached_data['originalApiData']:
                    summary = cached_data['originalApiData'].get('summary')
                if not summary:
                    summary = {
                        'total_clicks': 0,
                        'total_impressions': 0,
                        'avg_ctr': 0,
                        'avg_position': 0
                    }
                metrics['summary'] = summary
                cached_data['metrics'] = metrics
            
            return cached_data.get('dashboard_data')
        except Exception as e:
            print(f"[ERROR] Error getting dashboard cache: {e}")
            return None

    def cleanup_dashboard_cache(self, days_old: int = 7) -> int:
        """Clean up dashboard cache entries older than specified days."""
        if self.demo_mode:
            # Clean demo cache
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            keys_to_remove = []
            
            for key in list(self._cache.keys()):
                if key.startswith('dashboard_cache_'):
                    cached_data, cached_time = self._cache[key]
                    if cached_time < cutoff_date:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._cache[key]
            
            return len(keys_to_remove)
        
        try:
            cache_sheet = self.get_or_create_sheet('dashboard-cache', [
                'cache_key', 'email', 'website_url', 'cache_date', 'dashboard_data', 'cached_at'
            ])
            
            if not cache_sheet:
                return 0
            
            # Get all records
            all_records = cache_sheet.get_all_records()
            rows_to_delete = []
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            for i, record in enumerate(all_records, start=2):  # Start at row 2 (after header)
                try:
                    cached_at = datetime.fromisoformat(record.get('cached_at', ''))
                    if cached_at < cutoff_date:
                        rows_to_delete.append(i)
                except (ValueError, TypeError):
                    # Invalid date format, consider it old
                    rows_to_delete.append(i)
            
            # Use batch delete operation instead of individual deletes
            if rows_to_delete:
                # Group consecutive rows for batch deletion
                row_ranges = []
                start = rows_to_delete[0]
                end = rows_to_delete[0]
                
                for row in rows_to_delete[1:]:
                    if row == end + 1:
                        end = row
                    else:
                        row_ranges.append((start, end))
                        start = end = row
                row_ranges.append((start, end))
                
                # Delete in reverse order to maintain row indices
                for start, end in reversed(row_ranges):
                    if start == end:
                        cache_sheet.delete_rows(start)
                    else:
                        cache_sheet.delete_rows(start, end)
            
            return len(rows_to_delete)
            
        except Exception as e:
            print(f"[ERROR] Error cleaning dashboard cache: {e}")
            return 0


# Create database instance
db = GoogleSheetsDB() 