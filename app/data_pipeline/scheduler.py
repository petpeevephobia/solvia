#!/usr/bin/env python3
"""
Data Pipeline Scheduler for automated and on-demand processing
Handles background tasks, rate limiting, and queue management
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

from app.database.supabase_db import SupabaseAuthDB
from app.data_pipeline.detailed_fetcher import DetailedGSCDataFetcher


class DataPipelineScheduler:
    """Manages data pipeline processing with rate limiting and scheduling"""
    
    def __init__(self):
        self.db = SupabaseAuthDB()
        self.fetcher = DetailedGSCDataFetcher(self.db)
        self.processing_queue = asyncio.Queue()
        self.active_jobs = {}  # Track running jobs
        self.rate_limiter = self._init_rate_limiter()
        self.max_concurrent_jobs = 3
        
    def _init_rate_limiter(self):
        """Initialize rate limiter for GSC API quotas"""
        return {
            'requests_per_minute': defaultdict(list),
            'requests_per_user': defaultdict(list),
            'global_requests': []
        }
    
    async def schedule_user_processing(self, user_email: str, website_url: str,
                                     priority: str = 'normal', 
                                     force_refresh: bool = False) -> str:
        """
        Schedule data processing for a specific user
        Returns job_id for tracking
        """
        
        job_id = f"{user_email}_{website_url}_{int(time.time())}"
        
        # Check if already processing
        existing_job_id = f"{user_email}_{website_url}"
        if existing_job_id in self.active_jobs:
            return self.active_jobs[existing_job_id]['job_id']
        
        # Add to queue
        job_data = {
            'job_id': job_id,
            'user_email': user_email,
            'website_url': website_url,
            'priority': priority,
            'force_refresh': force_refresh,
            'created_at': datetime.now(),
            'status': 'queued'
        }
        
        await self.processing_queue.put(job_data)
        self.active_jobs[existing_job_id] = job_data
        
        print(f"[SCHEDULER] Queued job {job_id} for {user_email}")
        return job_id
    
    async def process_all_users(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Process data pipeline for all users with GSC connections
        Useful for daily/weekly batch processing
        """
        
        try:
            # Get all users with GSC connections
            response = self.db.supabase.table('gsc_connections')\
                .select('email, property_url')\
                .execute()
            
            if not response.data:
                return {'message': 'No users found with GSC connections', 'processed': 0}
            
            results = []
            total_users = len(response.data)
            
            print(f"[BATCH] Starting batch processing for {total_users} users")
            
            # Schedule all users for processing
            for user_data in response.data:
                job_id = await self.schedule_user_processing(
                    user_data['email'],
                    user_data['property_url'],
                    priority='batch',
                    force_refresh=force_refresh
                )
                results.append({
                    'user': user_data['email'],
                    'job_id': job_id,
                    'status': 'scheduled'
                })
            
            return {
                'message': f'Scheduled {total_users} users for processing',
                'jobs': results,
                'total_scheduled': total_users
            }
            
        except Exception as e:
            print(f"[BATCH] Error scheduling batch processing: {e}")
            return {'error': str(e), 'processed': 0}
    
    async def start_queue_processor(self):
        """
        Start the background queue processor
        Runs continuously to process queued jobs
        """
        
        print("[SCHEDULER] Starting queue processor...")
        
        # Start worker tasks
        workers = []
        for i in range(self.max_concurrent_jobs):
            worker = asyncio.create_task(self._queue_worker(f"worker-{i}"))
            workers.append(worker)
        
        # Wait for all workers
        await asyncio.gather(*workers)
    
    async def _queue_worker(self, worker_name: str):
        """Background worker to process queued jobs"""
        
        print(f"[{worker_name.upper()}] Worker started")
        
        while True:
            try:
                # Get next job from queue
                job_data = await self.processing_queue.get()
                
                print(f"[{worker_name.upper()}] Processing job {job_data['job_id']}")
                
                # Update job status
                job_data['status'] = 'processing'
                job_data['started_at'] = datetime.now()
                
                # Check rate limits
                if not await self._check_rate_limits(job_data['user_email']):
                    print(f"[{worker_name.upper()}] Rate limited, requeueing job")
                    await asyncio.sleep(60)  # Wait 1 minute
                    await self.processing_queue.put(job_data)
                    continue
                
                # Process the job
                try:
                    result = await self.fetcher.fetch_complete_data_pipeline(
                        job_data['user_email'],
                        job_data['website_url'],
                        job_data['force_refresh']
                    )
                    
                    job_data['status'] = 'completed'
                    job_data['completed_at'] = datetime.now()
                    job_data['result'] = result
                    
                    print(f"[{worker_name.upper()}] Completed job {job_data['job_id']}: {result}")
                    
                except Exception as e:
                    job_data['status'] = 'failed'
                    job_data['error'] = str(e)
                    job_data['completed_at'] = datetime.now()
                    
                    print(f"[{worker_name.upper()}] Failed job {job_data['job_id']}: {e}")
                
                finally:
                    # Remove from active jobs
                    active_key = f"{job_data['user_email']}_{job_data['website_url']}"
                    if active_key in self.active_jobs:
                        del self.active_jobs[active_key]
                    
                    # Mark queue task as done
                    self.processing_queue.task_done()
                
                # Small delay between jobs
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[{worker_name.upper()}] Worker error: {e}")
                await asyncio.sleep(5)
    
    async def _check_rate_limits(self, user_email: str) -> bool:
        """Check if we can make requests for this user without hitting rate limits"""
        
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.rate_limiter['global_requests'] = [
            req_time for req_time in self.rate_limiter['global_requests']
            if req_time > minute_ago
        ]
        
        self.rate_limiter['requests_per_user'][user_email] = [
            req_time for req_time in self.rate_limiter['requests_per_user'][user_email]
            if req_time > minute_ago
        ]
        
        # Check global limit (1200 requests per minute)
        if len(self.rate_limiter['global_requests']) >= 1000:  # Leave buffer
            return False
        
        # Check per-user limit (100 requests per 100 seconds per user)
        hundred_seconds_ago = now - 100
        user_recent_requests = [
            req_time for req_time in self.rate_limiter['requests_per_user'][user_email]
            if req_time > hundred_seconds_ago
        ]
        
        if len(user_recent_requests) >= 80:  # Leave buffer
            return False
        
        # Record this request
        self.rate_limiter['global_requests'].append(now)
        self.rate_limiter['requests_per_user'][user_email].append(now)
        
        return True
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job"""
        
        # Check active jobs
        for job_data in self.active_jobs.values():
            if job_data['job_id'] == job_id:
                return job_data
        
        return None
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue and processing status"""
        
        return {
            'queue_size': self.processing_queue.qsize(),
            'active_jobs': len(self.active_jobs),
            'workers_running': self.max_concurrent_jobs,
            'active_job_details': list(self.active_jobs.values())
        }
    
    async def force_process_user(self, user_email: str, website_url: str) -> Dict[str, Any]:
        """
        Force immediate processing for a user (bypasses queue)
        Use sparingly to avoid rate limits
        """
        
        try:
            print(f"[FORCE] Starting immediate processing for {user_email}")
            
            # Check rate limits
            if not await self._check_rate_limits(user_email):
                return {
                    'error': 'Rate limited - please try again later',
                    'status': 'rate_limited'
                }
            
            # Process immediately
            result = await self.fetcher.fetch_complete_data_pipeline(
                user_email, website_url, force_full_refresh=False
            )
            
            return {
                'status': 'completed',
                'result': result,
                'processed_immediately': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    # Utility methods for external access
    
    async def get_user_pipeline_status(self, user_email: str, website_url: str) -> Dict[str, Any]:
        """Get comprehensive pipeline status for a user"""
        
        try:
            # Get database status
            db_status = await self.fetcher.get_pipeline_status(user_email, website_url)
            
            # Check if currently processing
            active_key = f"{user_email}_{website_url}"
            is_processing = active_key in self.active_jobs
            
            # Get last data freshness
            response = self.db.supabase.table('gsc_daily_summary')\
                .select('date')\
                .eq('user_email', user_email)\
                .eq('website_url', website_url)\
                .order('date', desc=True)\
                .limit(1)\
                .execute()
            
            last_data_date = None
            if response.data:
                last_data_date = response.data[0]['date']
            
            return {
                'database_status': db_status,
                'is_currently_processing': is_processing,
                'last_data_date': last_data_date,
                'data_freshness_days': (
                    (datetime.now().date() - datetime.strptime(last_data_date, '%Y-%m-%d').date()).days
                    if last_data_date else None
                )
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def cleanup_old_data(self, days_to_keep: int = 365) -> Dict[str, Any]:
        """Clean up old data beyond retention period"""
        
        try:
            cutoff_date = (datetime.now().date() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            
            # Clean old query data
            queries_deleted = self.db.supabase.table('gsc_queries')\
                .delete()\
                .lt('date', cutoff_date)\
                .execute()
            
            # Clean old page data
            pages_deleted = self.db.supabase.table('gsc_pages')\
                .delete()\
                .lt('date', cutoff_date)\
                .execute()
            
            # Clean old daily summaries
            summaries_deleted = self.db.supabase.table('gsc_daily_summary')\
                .delete()\
                .lt('date', cutoff_date)\
                .execute()
            
            return {
                'status': 'completed',
                'cutoff_date': cutoff_date,
                'queries_deleted': len(queries_deleted.data) if queries_deleted.data else 0,
                'pages_deleted': len(pages_deleted.data) if pages_deleted.data else 0,
                'summaries_deleted': len(summaries_deleted.data) if summaries_deleted.data else 0
            }
            
        except Exception as e:
            return {'error': str(e), 'status': 'failed'}


# Global scheduler instance
pipeline_scheduler = DataPipelineScheduler()