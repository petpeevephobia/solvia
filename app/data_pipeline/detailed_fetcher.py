#!/usr/bin/env python3
"""
Enhanced GSC Data Fetcher for detailed query and page level analytics
Implements complete data pipeline with incremental fetching and normalization
"""

import os
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import math
import time

from app.database.supabase_db import SupabaseAuthDB


class DetailedGSCDataFetcher:
    """Enhanced GSC data fetcher for detailed analytics"""
    
    def __init__(self, db: SupabaseAuthDB = None):
        self.db = db or SupabaseAuthDB()
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.batch_size = 1000  # Process in batches to avoid memory issues
        
    async def fetch_complete_data_pipeline(self, user_email: str, website_url: str, 
                                         force_full_refresh: bool = False) -> Dict[str, Any]:
        """
        Main entry point - fetch complete GSC data pipeline
        Returns detailed processing results
        """
        try:
            # Update pipeline status to running
            await self._update_pipeline_status(user_email, website_url, 'running')
            
            # Determine date range for fetching
            start_date, end_date = await self._get_fetch_date_range(
                user_email, website_url, force_full_refresh
            )
            
            print(f"[DATA PIPELINE] Processing {user_email} from {start_date} to {end_date}")
            
            # Get user credentials
            credentials = await self._get_user_credentials(user_email)
            if not credentials:
                raise Exception(f"No GSC credentials found for {user_email}")
            
            # Process data in chunks to handle large datasets
            total_queries = 0
            total_pages = 0
            
            current_date = start_date
            while current_date <= end_date:
                # Process week chunks to manage API quotas
                chunk_end = min(current_date + timedelta(days=6), end_date)
                
                print(f"[DATA PIPELINE] Processing chunk: {current_date} to {chunk_end}")
                
                # Fetch and store query data
                query_count = await self._fetch_and_store_queries(
                    user_email, website_url, credentials, current_date, chunk_end
                )
                
                # Fetch and store page data
                page_count = await self._fetch_and_store_pages(
                    user_email, website_url, credentials, current_date, chunk_end
                )
                
                # Calculate daily aggregates for this chunk
                await self._calculate_daily_aggregates_range(
                    user_email, website_url, current_date, chunk_end
                )
                
                total_queries += query_count
                total_pages += page_count
                
                # Move to next chunk
                current_date = chunk_end + timedelta(days=1)
                
                # Small delay to respect API limits
                await asyncio.sleep(0.5)
            
            # Update pipeline status to completed
            await self._update_pipeline_status(
                user_email, website_url, 'completed',
                last_fetch_date=end_date,
                queries_processed=total_queries,
                pages_processed=total_pages
            )
            
            # Update legacy cache table for backward compatibility
            await self._update_legacy_cache(user_email, website_url, end_date)
            
            return {
                'status': 'completed',
                'date_range': f"{start_date} to {end_date}",
                'queries_processed': total_queries,
                'pages_processed': total_pages,
                'processing_time': time.time()
            }
            
        except Exception as e:
            # Update pipeline status to failed
            await self._update_pipeline_status(
                user_email, website_url, 'failed', error_message=str(e)
            )
            raise Exception(f"Data pipeline failed for {user_email}: {str(e)}")
    
    async def _fetch_and_store_queries(self, user_email: str, website_url: str, 
                                     credentials: Credentials, start_date: date, 
                                     end_date: date) -> int:
        """Fetch and store detailed query-level data"""
        
        try:
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Fetch query data with pagination
            all_queries = []
            start_row = 0
            row_limit = 25000  # Max GSC allows
            
            while True:
                request = {
                    'startDate': start_date.strftime('%Y-%m-%d'),
                    'endDate': end_date.strftime('%Y-%m-%d'),
                    'dimensions': ['query', 'date'],
                    'rowLimit': row_limit,
                    'startRow': start_row
                }
                
                response = await self._make_gsc_request(service, website_url, request)
                
                if not response or 'rows' not in response:
                    break
                
                rows = response['rows']
                if not rows:
                    break
                
                # Normalize and add to batch
                normalized_queries = self._normalize_query_data(
                    user_email, website_url, rows
                )
                all_queries.extend(normalized_queries)
                
                # If we got less than row_limit, we're done
                if len(rows) < row_limit:
                    break
                
                start_row += row_limit
                
                # Process in batches to avoid memory issues
                if len(all_queries) >= self.batch_size:
                    await self._store_query_batch(all_queries[:self.batch_size])
                    all_queries = all_queries[self.batch_size:]
            
            # Store remaining queries
            if all_queries:
                await self._store_query_batch(all_queries)
            
            total_processed = len(all_queries) + (start_row - len(all_queries))
            print(f"[QUERIES] Processed {total_processed} query records for {user_email}")
            
            return total_processed
            
        except Exception as e:
            print(f"[ERROR] Query fetching failed for {user_email}: {e}")
            return 0
    
    async def _fetch_and_store_pages(self, user_email: str, website_url: str,
                                   credentials: Credentials, start_date: date,
                                   end_date: date) -> int:
        """Fetch and store detailed page-level data"""
        
        try:
            service = build('webmasters', 'v3', credentials=credentials)
            
            # Fetch page data with pagination
            all_pages = []
            start_row = 0
            row_limit = 25000
            
            while True:
                request = {
                    'startDate': start_date.strftime('%Y-%m-%d'),
                    'endDate': end_date.strftime('%Y-%m-%d'),
                    'dimensions': ['page', 'date'],
                    'rowLimit': row_limit,
                    'startRow': start_row
                }
                
                response = await self._make_gsc_request(service, website_url, request)
                
                if not response or 'rows' not in response:
                    break
                
                rows = response['rows']
                if not rows:
                    break
                
                # Normalize and add to batch
                normalized_pages = self._normalize_page_data(
                    user_email, website_url, rows
                )
                all_pages.extend(normalized_pages)
                
                if len(rows) < row_limit:
                    break
                
                start_row += row_limit
                
                # Process in batches
                if len(all_pages) >= self.batch_size:
                    await self._store_page_batch(all_pages[:self.batch_size])
                    all_pages = all_pages[self.batch_size:]
            
            # Store remaining pages
            if all_pages:
                await self._store_page_batch(all_pages)
            
            total_processed = len(all_pages) + (start_row - len(all_pages))
            print(f"[PAGES] Processed {total_processed} page records for {user_email}")
            
            return total_processed
            
        except Exception as e:
            print(f"[ERROR] Page fetching failed for {user_email}: {e}")
            return 0
    
    def _normalize_query_data(self, user_email: str, website_url: str, 
                            rows: List[Dict]) -> List[Dict]:
        """Normalize raw GSC query data into database format"""
        
        normalized = []
        for row in rows:
            try:
                # Validate row structure
                if 'keys' not in row or len(row['keys']) < 2:
                    continue
                
                normalized_row = {
                    'user_email': user_email,
                    'website_url': website_url,
                    'query_text': str(row['keys'][0])[:500],  # Limit length
                    'date': datetime.strptime(row['keys'][1], '%Y-%m-%d').date(),
                    'clicks': max(0, int(row.get('clicks', 0))),
                    'impressions': max(0, int(row.get('impressions', 0))),
                    'ctr': max(0, min(1, float(row.get('ctr', 0)))),  # CTR between 0-1
                    'position': max(0.1, float(row.get('position', 0)))  # Position > 0
                }
                
                # Validate data quality
                if self._validate_query_data(normalized_row):
                    normalized.append(normalized_row)
                    
            except (ValueError, KeyError, TypeError) as e:
                print(f"[WARNING] Skipping invalid query row: {e}")
                continue
        
        return normalized
    
    def _normalize_page_data(self, user_email: str, website_url: str,
                           rows: List[Dict]) -> List[Dict]:
        """Normalize raw GSC page data into database format"""
        
        normalized = []
        for row in rows:
            try:
                if 'keys' not in row or len(row['keys']) < 2:
                    continue
                
                normalized_row = {
                    'user_email': user_email,
                    'website_url': website_url,
                    'page_url': str(row['keys'][0])[:2000],  # Limit URL length
                    'date': datetime.strptime(row['keys'][1], '%Y-%m-%d').date(),
                    'clicks': max(0, int(row.get('clicks', 0))),
                    'impressions': max(0, int(row.get('impressions', 0))),
                    'ctr': max(0, min(1, float(row.get('ctr', 0)))),
                    'position': max(0.1, float(row.get('position', 0)))
                }
                
                if self._validate_page_data(normalized_row):
                    normalized.append(normalized_row)
                    
            except (ValueError, KeyError, TypeError) as e:
                print(f"[WARNING] Skipping invalid page row: {e}")
                continue
        
        return normalized
    
    def _validate_query_data(self, data: Dict) -> bool:
        """Validate normalized query data"""
        return (
            data['query_text'] and len(data['query_text'].strip()) > 0 and
            data['date'] and
            data['clicks'] >= 0 and
            data['impressions'] >= 0 and
            0 <= data['ctr'] <= 1 and
            data['position'] > 0
        )
    
    def _validate_page_data(self, data: Dict) -> bool:
        """Validate normalized page data"""
        return (
            data['page_url'] and len(data['page_url'].strip()) > 0 and
            data['date'] and
            data['clicks'] >= 0 and
            data['impressions'] >= 0 and
            0 <= data['ctr'] <= 1 and
            data['position'] > 0
        )
    
    async def _store_query_batch(self, query_batch: List[Dict]) -> bool:
        """Store batch of normalized query data with conflict resolution"""
        
        try:
            if not query_batch:
                return True
            
            # Use upsert to handle conflicts
            response = self.db.supabase.table('gsc_queries')\
                .upsert(
                    query_batch, 
                    on_conflict=['user_email', 'website_url', 'query_text', 'date']
                )\
                .execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"[ERROR] Failed to store query batch: {e}")
            return False
    
    async def _store_page_batch(self, page_batch: List[Dict]) -> bool:
        """Store batch of normalized page data with conflict resolution"""
        
        try:
            if not page_batch:
                return True
            
            response = self.db.supabase.table('gsc_pages')\
                .upsert(
                    page_batch,
                    on_conflict=['user_email', 'website_url', 'page_url', 'date']
                )\
                .execute()
            
            return bool(response.data)
            
        except Exception as e:
            print(f"[ERROR] Failed to store page batch: {e}")
            return False
    
    async def _make_gsc_request(self, service, website_url: str, 
                              request: Dict) -> Optional[Dict]:
        """Make GSC API request with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                response = service.searchanalytics().query(
                    siteUrl=website_url, body=request
                ).execute()
                return response
                
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    wait_time = (2 ** attempt) * self.retry_delay
                    print(f"[API] Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.resp.status in [403, 404]:
                    print(f"[API] Permissions or not found error: {e.resp.status}")
                    return None
                else:
                    print(f"[API] HTTP Error {e.resp.status}: {e}")
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(self.retry_delay)
                    
            except Exception as e:
                print(f"[API] Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)
        
        return None
    
    async def _get_fetch_date_range(self, user_email: str, website_url: str,
                                  force_full_refresh: bool) -> Tuple[date, date]:
        """Determine optimal date range for fetching"""
        
        end_date = datetime.now().date() - timedelta(days=1)  # GSC data available within 1-2 days
        
        if force_full_refresh:
            # Full refresh: get last 16 months (GSC limit)
            start_date = end_date - timedelta(days=480)
            return start_date, end_date
        
        # Incremental: check last fetch date
        try:
            response = self.db.supabase.table('gsc_pipeline_status')\
                .select('last_fetch_date')\
                .eq('user_email', user_email)\
                .eq('website_url', website_url)\
                .execute()
            
            if response.data and response.data[0]['last_fetch_date']:
                last_fetch = datetime.strptime(
                    response.data[0]['last_fetch_date'], '%Y-%m-%d'
                ).date()
                start_date = last_fetch + timedelta(days=1)
                
                # Don't fetch if already up to date
                if start_date > end_date:
                    start_date = end_date
                    
                return start_date, end_date
        except:
            pass
        
        # Default: last 90 days for new users
        start_date = end_date - timedelta(days=90)
        return start_date, end_date
    
    async def _get_user_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get user's stored GSC credentials"""
        
        try:
            response = self.db.supabase.table('gsc_connections')\
                .select('credentials')\
                .eq('email', user_email)\
                .execute()
            
            if response.data and response.data[0]['credentials']:
                creds_data = response.data[0]['credentials']
                
                credentials = Credentials(
                    token=creds_data.get('token'),
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data.get('token_uri'),
                    client_id=creds_data.get('client_id'),
                    client_secret=creds_data.get('client_secret'),
                    scopes=creds_data.get('scopes')
                )
                
                return credentials
                
        except Exception as e:
            print(f"[CREDENTIALS] Failed to get credentials for {user_email}: {e}")
        
        return None
    
    async def _update_pipeline_status(self, user_email: str, website_url: str,
                                    status: str, last_fetch_date: date = None,
                                    queries_processed: int = 0,
                                    pages_processed: int = 0,
                                    error_message: str = None):
        """Update pipeline processing status"""
        
        try:
            update_data = {
                'user_email': user_email,
                'website_url': website_url,
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if last_fetch_date:
                update_data['last_fetch_date'] = last_fetch_date.strftime('%Y-%m-%d')
                if status == 'completed':
                    update_data['last_success_date'] = last_fetch_date.strftime('%Y-%m-%d')
            
            if queries_processed > 0:
                update_data['queries_processed'] = queries_processed
            
            if pages_processed > 0:
                update_data['pages_processed'] = pages_processed
            
            if error_message:
                update_data['error_message'] = error_message[:1000]  # Limit length
            
            self.db.supabase.table('gsc_pipeline_status')\
                .upsert(update_data, on_conflict=['user_email', 'website_url'])\
                .execute()
                
        except Exception as e:
            print(f"[STATUS] Failed to update pipeline status: {e}")
    
    async def _calculate_daily_aggregates_range(self, user_email: str, website_url: str,
                                              start_date: date, end_date: date):
        """Calculate daily aggregates for a date range"""
        
        current_date = start_date
        while current_date <= end_date:
            try:
                # Use the database function we created
                self.db.supabase.rpc('calculate_daily_aggregates', {
                    'p_user_email': user_email,
                    'p_website_url': website_url,
                    'p_date': current_date.strftime('%Y-%m-%d')
                }).execute()
                
            except Exception as e:
                print(f"[AGGREGATES] Failed for {current_date}: {e}")
            
            current_date += timedelta(days=1)
    
    async def _update_legacy_cache(self, user_email: str, website_url: str, 
                                 end_date: date):
        """Update legacy gsc_metrics_cache table for backward compatibility"""
        
        try:
            # Calculate summary from last 30 days
            start_date = end_date - timedelta(days=30)
            
            # Get aggregated data
            response = self.db.supabase.table('gsc_daily_summary')\
                .select('*')\
                .eq('user_email', user_email)\
                .eq('website_url', website_url)\
                .gte('date', start_date.strftime('%Y-%m-%d'))\
                .lte('date', end_date.strftime('%Y-%m-%d'))\
                .execute()
            
            if response.data:
                # Calculate totals
                total_clicks = sum(row['total_clicks'] for row in response.data)
                total_impressions = sum(row['total_impressions'] for row in response.data)

                # CRITICAL FIX: Calculate weighted averages (like GSC does)
                # CTR = total clicks / total impressions (not average of daily CTRs)
                avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0

                # Position = weighted average by impressions (not simple average of daily positions)
                weighted_position_sum = sum(
                    row['avg_position'] * row['total_impressions']
                    for row in response.data
                )
                avg_position = weighted_position_sum / total_impressions if total_impressions > 0 else 0

                # Calculate SEO score
                seo_score = self._calculate_seo_score(
                    total_clicks, total_impressions, avg_ctr, avg_position
                )
                
                # Update legacy cache
                cache_data = {
                    'user_email': user_email,
                    'website_url': website_url,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'seo_score': seo_score,
                    'impressions': total_impressions,
                    'clicks': total_clicks,
                    'ctr': round(avg_ctr, 4),
                    'avg_position': round(avg_position, 2),
                    'cache_date': end_date.strftime('%Y-%m-%d')
                }
                
                self.db.supabase.table('gsc_metrics_cache')\
                    .upsert(cache_data, on_conflict=['user_email', 'website_url', 'start_date', 'end_date'])\
                    .execute()
                
        except Exception as e:
            print(f"[LEGACY] Failed to update legacy cache: {e}")
    
    def _calculate_seo_score(self, clicks: int, impressions: int,
                           ctr: float, position: float) -> int:
        """Calculate SEO score using unified scoring engine"""
        # Import here to avoid circular dependency
        from app.core.seo_scoring import SEOScoringEngine

        # Use unified scoring engine for consistency
        score = SEOScoringEngine.calculate_score(
            clicks=clicks,
            impressions=impressions,
            ctr=ctr,
            position=position,
            historical_data=None  # No historical data for simple metrics
        )

        return score
    
    # Public methods for external access
    
    async def get_top_queries(self, user_email: str, website_url: str,
                            start_date: date, end_date: date, 
                            limit: int = 50) -> List[Dict]:
        """Get top performing queries for a date range"""
        
        try:
            response = self.db.supabase.rpc('get_top_queries', {
                'p_user_email': user_email,
                'p_website_url': website_url,
                'p_start_date': start_date.strftime('%Y-%m-%d'),
                'p_end_date': end_date.strftime('%Y-%m-%d'),
                'p_limit': limit
            }).execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"[TOP QUERIES] Error: {e}")
            return []
    
    async def get_top_pages(self, user_email: str, website_url: str,
                          start_date: date, end_date: date,
                          limit: int = 50) -> List[Dict]:
        """Get top performing pages for a date range"""
        
        try:
            response = self.db.supabase.rpc('get_top_pages', {
                'p_user_email': user_email,
                'p_website_url': website_url,
                'p_start_date': start_date.strftime('%Y-%m-%d'),
                'p_end_date': end_date.strftime('%Y-%m-%d'),
                'p_limit': limit
            }).execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"[TOP PAGES] Error: {e}")
            return []
    
    async def get_pipeline_status(self, user_email: str, website_url: str) -> Optional[Dict]:
        """Get current pipeline processing status"""
        
        try:
            response = self.db.supabase.table('gsc_pipeline_status')\
                .select('*')\
                .eq('user_email', user_email)\
                .eq('website_url', website_url)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            print(f"[PIPELINE STATUS] Error: {e}")
            return None