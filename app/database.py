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
from uuid import uuid4
import os
from app.database.supabase_client import supabase


class GoogleSheetsDB:
    """Google Sheets database interface."""
    
    def __init__(self):
        
        """Initialize Google Sheets connection or demo mode."""
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
            print("[CRITICAL] Solvia requires Google Sheets connection. Demo mode is disabled.")
            raise Exception("Google Sheets connection required. Cannot start Solvia without proper configuration.")
        
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
        """Perform daily cleanup tasks."""
        today = datetime.utcnow().date().isoformat()
        lock_file = f"cleanup_lock_{today}.txt"
        
        # Check if cleanup was already performed today
        if os.path.exists(lock_file):
            try:
                # Check if lock file is from today
                lock_mtime = datetime.fromtimestamp(os.path.getmtime(lock_file)).date()
                if lock_mtime == datetime.utcnow().date():
                    return
            except (OSError, ValueError):
                # If we can't read the lock file, proceed with cleanup
                pass
        
        try:
            # Cleanup expired sessions
            sessions_cleaned = self.cleanup_expired_sessions()
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            
        try:
            # Cleanup expired dashboard cache (older than 7 days)  
            cache_cleaned = self.cleanup_dashboard_cache(days_old=7)
        except Exception as e:
            print(f"Warning: Could not cleanup expired dashboard cache: {e}")
            
        try:
            # Cleanup expired reports (older than 30 days)
            reports_cleaned = self.cleanup_expired_reports()
            print(f"[INFO] Cleaned up {reports_cleaned} expired SEO reports")
        except Exception as e:
            print(f"Warning: Could not cleanup expired reports: {e}")
            
        # Create lock file to mark cleanup as completed for today
        try:
            with open(lock_file, 'w') as f:
                f.write(f"Cleanup completed at {datetime.utcnow().isoformat()}")
        except Exception as e:
            print(f"Warning: Could not create cleanup lock file: {e}")
    
    def get_or_create_sheet(self, sheet_name: str, headers: List[str] = None) -> gspread.Worksheet:
        """Get a worksheet by name, or create it if it doesn't exist."""
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
        try:
            # Check if user already exists
            existing_user = self._find_user_row(user.email)
            if existing_user:
                print(f"User {user.email} already exists")
                return False
            
            # Add new user
            self.users_sheet.append_row([
                user.email,
                password_hash,
                datetime.utcnow().isoformat(),
                '',  # last_login
                'FALSE',  # is_verified
                verification_token,
                ''  # reset_token
            ])
            print(f"Created user: {user.email}")
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email from the database."""
        try:
            # Find user row
            user_row = self._find_user_row(email)
            if not user_row:
                return None
            
            # Get user data
            user_data = self.users_sheet.row_values(user_row)
            if len(user_data) < 7:
                print(f"Invalid user data for {email}: insufficient columns")
            return None
        
            return UserInDB(
                id=str(uuid4()),
                email=user_data[0],
                password_hash=user_data[1],
                created_at=user_data[2],
                last_login=user_data[3] if user_data[3] else None,
                is_verified=user_data[4].upper() == 'TRUE',
                verification_token=user_data[5] if user_data[5] else None,
                reset_token=user_data[6] if user_data[6] else None
            )
        except Exception as e:
            print(f"Error getting user by email: {e}")
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
        try:
            row = self._find_user_row(email)
            if row is None:
                return False
            self.users_sheet.update_cell(row, 4, datetime.utcnow().isoformat())
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
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        # Check if we're in demo mode or don't have sessions sheet
        if not hasattr(self, 'sessions_sheet'):
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
            
            return report_id
            
        except Exception as e:
            print(f"[ERROR] Failed to store SEO report: {e}")
            return None

    def get_user_reports(self, email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get all SEO reports for a user, ordered by most recent first.
        """
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
            
            return user_reports[:limit]
            
        except Exception as e:
            print(f"[ERROR] Failed to get user reports: {e}")
            return []

    def get_report_by_id(self, report_id: str, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific report by ID (with email verification for security).
        """
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


# sheets_db = GoogleSheetsDB()  # Uncomment if you need to use Google Sheets for other features 