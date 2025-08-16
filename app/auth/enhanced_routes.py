#!/usr/bin/env python3
"""
Enhanced routes for detailed data pipeline integration
Adds new endpoints for query/page level analytics and background processing
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import asyncio

from app.auth.routes import get_current_user
from app.database.supabase_db import SupabaseAuthDB
from app.data_pipeline.detailed_fetcher import DetailedGSCDataFetcher
from app.data_pipeline.scheduler import pipeline_scheduler

# Create enhanced router
enhanced_router = APIRouter(prefix="/data-pipeline", tags=["Enhanced Data Pipeline"])

# Initialize components
db = SupabaseAuthDB()
fetcher = DetailedGSCDataFetcher(db)


@enhanced_router.post("/trigger-processing")
async def trigger_data_processing(
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: str = Depends(get_current_user)
):
    """
    Trigger detailed data pipeline processing for current user
    Can run in background or return immediately with job ID
    """
    try:
        # Get user's selected website
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected. Please select a domain first."
            )
        
        # Check if already processing
        status_info = await pipeline_scheduler.get_user_pipeline_status(
            current_user, user_website
        )
        
        if status_info.get('is_currently_processing'):
            return {
                "status": "already_processing",
                "message": "Data pipeline is already running for your website",
                "current_status": status_info
            }
        
        # Schedule processing
        job_id = await pipeline_scheduler.schedule_user_processing(
            current_user, user_website, 
            priority='user_request',
            force_refresh=force_refresh
        )
        
        return {
            "status": "scheduled",
            "job_id": job_id,
            "message": "Data processing scheduled. Check status with /data-pipeline/status",
            "estimated_completion": "5-15 minutes depending on website size"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger processing: {str(e)}"
        )


@enhanced_router.get("/status")
async def get_processing_status(current_user: str = Depends(get_current_user)):
    """Get current data pipeline status for user"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        status_info = await pipeline_scheduler.get_user_pipeline_status(
            current_user, user_website
        )
        
        return {
            "user_email": current_user,
            "website_url": user_website,
            "pipeline_status": status_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@enhanced_router.get("/top-queries")
async def get_top_queries(
    days: int = 30,
    limit: int = 50,
    current_user: str = Depends(get_current_user)
):
    """Get top performing queries for user's website"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        queries = await fetcher.get_top_queries(
            current_user, user_website, start_date, end_date, limit
        )
        
        return {
            "queries": queries,
            "date_range": f"{start_date} to {end_date}",
            "total_queries": len(queries)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top queries: {str(e)}"
        )


@enhanced_router.get("/top-pages")
async def get_top_pages(
    days: int = 30,
    limit: int = 50,
    current_user: str = Depends(get_current_user)
):
    """Get top performing pages for user's website"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        pages = await fetcher.get_top_pages(
            current_user, user_website, start_date, end_date, limit
        )
        
        return {
            "pages": pages,
            "date_range": f"{start_date} to {end_date}",
            "total_pages": len(pages)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top pages: {str(e)}"
        )


@enhanced_router.get("/query-trends/{query_text}")
async def get_query_trends(
    query_text: str,
    days: int = 90,
    current_user: str = Depends(get_current_user)
):
    """Get performance trends for a specific query"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get query trend data
        response = db.supabase.table('gsc_queries')\
            .select('date, clicks, impressions, ctr, position')\
            .eq('user_email', current_user)\
            .eq('website_url', user_website)\
            .eq('query_text', query_text)\
            .gte('date', start_date.strftime('%Y-%m-%d'))\
            .lte('date', end_date.strftime('%Y-%m-%d'))\
            .order('date')\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for query: {query_text}"
            )
        
        # Calculate trend analysis
        data_points = response.data
        
        # Calculate averages
        avg_clicks = sum(d['clicks'] for d in data_points) / len(data_points)
        avg_impressions = sum(d['impressions'] for d in data_points) / len(data_points)
        avg_position = sum(d['position'] for d in data_points) / len(data_points)
        avg_ctr = sum(d['ctr'] for d in data_points) / len(data_points)
        
        # Calculate trends (compare first week vs last week)
        if len(data_points) >= 14:
            first_week = data_points[:7]
            last_week = data_points[-7:]
            
            first_week_avg_clicks = sum(d['clicks'] for d in first_week) / 7
            last_week_avg_clicks = sum(d['clicks'] for d in last_week) / 7
            
            clicks_trend = (
                ((last_week_avg_clicks - first_week_avg_clicks) / max(first_week_avg_clicks, 1)) * 100
            )
        else:
            clicks_trend = 0
        
        return {
            "query": query_text,
            "date_range": f"{start_date} to {end_date}",
            "data_points": data_points,
            "summary": {
                "avg_clicks": round(avg_clicks, 2),
                "avg_impressions": round(avg_impressions, 2),
                "avg_position": round(avg_position, 2),
                "avg_ctr": round(avg_ctr, 4),
                "clicks_trend_percent": round(clicks_trend, 2)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query trends: {str(e)}"
        )


@enhanced_router.get("/page-trends")
async def get_page_trends(
    page_url: str,
    days: int = 90,
    current_user: str = Depends(get_current_user)
):
    """Get performance trends for a specific page"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get page trend data
        response = db.supabase.table('gsc_pages')\
            .select('date, clicks, impressions, ctr, position')\
            .eq('user_email', current_user)\
            .eq('website_url', user_website)\
            .eq('page_url', page_url)\
            .gte('date', start_date.strftime('%Y-%m-%d'))\
            .lte('date', end_date.strftime('%Y-%m-%d'))\
            .order('date')\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for page: {page_url}"
            )
        
        return {
            "page_url": page_url,
            "date_range": f"{start_date} to {end_date}",
            "data_points": response.data,
            "total_data_points": len(response.data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get page trends: {str(e)}"
        )


@enhanced_router.get("/daily-summary")
async def get_daily_summary(
    days: int = 30,
    current_user: str = Depends(get_current_user)
):
    """Get daily aggregated metrics for dashboard"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily summary data
        response = db.supabase.table('gsc_daily_summary')\
            .select('*')\
            .eq('user_email', current_user)\
            .eq('website_url', user_website)\
            .gte('date', start_date.strftime('%Y-%m-%d'))\
            .lte('date', end_date.strftime('%Y-%m-%d'))\
            .order('date')\
            .execute()
        
        if not response.data:
            # If no data, trigger processing
            job_id = await pipeline_scheduler.schedule_user_processing(
                current_user, user_website, priority='dashboard_request'
            )
            
            return {
                "message": "No data available. Processing has been triggered.",
                "job_id": job_id,
                "check_status_endpoint": "/data-pipeline/status"
            }
        
        # Calculate totals and averages
        data_points = response.data
        total_clicks = sum(d['total_clicks'] for d in data_points)
        total_impressions = sum(d['total_impressions'] for d in data_points)
        avg_ctr = sum(d['avg_ctr'] for d in data_points) / len(data_points)
        avg_position = sum(d['avg_position'] for d in data_points) / len(data_points)
        
        return {
            "date_range": f"{start_date} to {end_date}",
            "daily_data": data_points,
            "summary": {
                "total_clicks": total_clicks,
                "total_impressions": total_impressions,
                "avg_ctr": round(avg_ctr, 4),
                "avg_position": round(avg_position, 2),
                "data_points": len(data_points)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily summary: {str(e)}"
        )


@enhanced_router.post("/force-refresh")
async def force_refresh_data(current_user: str = Depends(get_current_user)):
    """Force immediate data refresh (bypasses queue, use sparingly)"""
    
    try:
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected"
            )
        
        result = await pipeline_scheduler.force_process_user(current_user, user_website)
        
        if result.get('status') == 'rate_limited':
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=result['error']
            )
        elif result.get('status') == 'failed':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force refresh: {str(e)}"
        )


# Admin endpoints (for debugging and monitoring)

@enhanced_router.get("/admin/queue-status")
async def get_queue_status():
    """Get current processing queue status (admin only)"""
    
    try:
        status = await pipeline_scheduler.get_queue_status()
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@enhanced_router.post("/admin/process-all-users")
async def process_all_users(force_refresh: bool = False):
    """Trigger processing for all users (admin only)"""
    
    try:
        result = await pipeline_scheduler.process_all_users(force_refresh)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process all users: {str(e)}"
        )


@enhanced_router.post("/admin/cleanup-old-data")
async def cleanup_old_data(days_to_keep: int = 365):
    """Clean up old data beyond retention period (admin only)"""
    
    try:
        result = await pipeline_scheduler.cleanup_old_data(days_to_keep)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup data: {str(e)}"
        )