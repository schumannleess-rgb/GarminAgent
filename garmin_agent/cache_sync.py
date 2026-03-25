"""
Activity Classification Cache Synchronization

Handles syncing activity classifications to cache on login.
Supports incremental and full sync strategies.
"""

import logging
import time
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class CacheSyncManager:
    """
    Manages synchronization of activity classifications to cache.

    Sync Strategies:
    - Full sync: First time, fetches 365 days
    - Incremental sync: Fetches last 30-90 days based on cache age
    - Skip sync: Cache is fresh (<24h old)
    """

    # Sync thresholds
    FULL_SYNC_THRESHOLD_DAYS = 7  # Full sync if cache older than this
    INCREMENTAL_SYNC_DAYS_FRESH = 30  # Look back this many days for fresh cache
    INCREMENTAL_SYNC_DAYS_STALE = 90  # Look back this many days for stale cache
    FULL_SYNC_DAYS = 365  # Days to fetch for full sync
    MAX_WORKERS = 10  # Parallel workers

    def __init__(self, client, cache):
        """Initialize sync manager.

        Args:
            client: GarminClient instance
            cache: ActivityClassificationCache instance
        """
        self.client = client
        self.cache = cache

    def sync_on_login(self) -> Dict[str, Any]:
        """Main entry point - sync cache on login.

        Determines sync strategy based on cache state:
        - No cache → Full sync (365 days)
        - Cache < 24h → Skip sync
        - Cache 24h-7d → Incremental sync (30 days)
        - Cache > 7d → Incremental sync (90 days)

        Returns:
            Dict with sync results (status, count, time)
        """
        start_time = time.time()

        # Check if cache exists and is fresh
        if not self.cache.needs_sync(max_age_hours=24):
            logger.info("Cache is fresh (<24h), skipping sync")
            return {
                "status": "skipped",
                "reason": "cache_fresh",
                "cache_age_hours": self.cache.get_sync_age_hours(),
            }

        # Determine sync strategy
        cache_age_hours = self.cache.get_sync_age_hours()

        if cache_age_hours is None:
            # No cache - full sync
            logger.info("No cache found, performing full sync")
            result = self.full_sync()
        elif cache_age_hours > self.FULL_SYNC_THRESHOLD_DAYS * 24:
            # Stale cache - larger incremental
            logger.info(f"Cache is stale ({cache_age_hours:.1f}h old), performing extended incremental sync")
            result = self.incremental_sync(days=self.INCREMENTAL_SYNC_DAYS_STALE)
        else:
            # Recent cache - small incremental
            logger.info(f"Cache is recent ({cache_age_hours:.1f}h old), performing incremental sync")
            result = self.incremental_sync(days=self.INCREMENTAL_SYNC_DAYS_FRESH)

        result["total_time"] = time.time() - start_time
        return result

    def incremental_sync(self, days: int = 30) -> Dict[str, Any]:
        """Incremental sync - fetch recent activities and classify new ones.

        Args:
            days: Number of days to look back

        Returns:
            Dict with sync results
        """
        start_time = time.time()

        # Get last synced activity ID
        last_sync_id = self.cache.get_last_sync_activity_id()

        # Fetch recent activities
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Fetching activities from {start_date} to {end_date}")

        try:
            activities = self.client.get_activities_by_date(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            return {"status": "error", "error": str(e)}

        if not activities:
            logger.info("No activities found in date range")
            return {"status": "success", "new_count": 0, "total_count": 0}

        # Filter to only new activities
        if last_sync_id:
            new_activities = [a for a in activities if a.get("activityId", 0) > last_sync_id]
            logger.info(f"Found {len(new_activities)} new activities (of {len(activities)} total)")
        else:
            new_activities = activities
            logger.info(f"Processing {len(activities)} activities")

        if not new_activities:
            # Still update sync time
            self.cache.update_sync_metadata()
            self.cache.save()
            return {
                "status": "success",
                "new_count": 0,
                "total_count": len(self.cache.load()['activities']),
            }

        # Classify and cache
        results = self._classify_activities_parallel(new_activities)

        # Update cache
        new_count = 0
        for activity_id, entry in results.items():
            self.cache.set(
                activity_id=activity_id,
                classification_data=entry['classification'],
                basic_data=entry['basic_data']
            )
            new_count += 1

        # Update metadata
        self.cache.update_sync_metadata()
        self.cache.save()

        elapsed = time.time() - start_time
        logger.info(f"Incremental sync complete: {new_count} new activities in {elapsed:.2f}s")

        return {
            "status": "success",
            "new_count": new_count,
            "total_count": len(self.cache.load()['activities']),
            "elapsed_seconds": elapsed,
        }

    def full_sync(self, days: int = None) -> Dict[str, Any]:
        """Full sync - fetch all activities and rebuild cache.

        Args:
            days: Number of days to fetch (default: 365)

        Returns:
            Dict with sync results
        """
        start_time = time.time()
        days = days or self.FULL_SYNC_DAYS

        # Clear existing cache
        self.cache.clear()

        # Fetch all activities
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Full sync: fetching activities from {start_date} to {end_date}")

        try:
            activities = self.client.get_activities_by_date(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            return {"status": "error", "error": str(e)}

        if not activities:
            logger.info("No activities found")
            return {"status": "success", "new_count": 0, "total_count": 0}

        total = len(activities)
        logger.info(f"Found {total} activities to classify")

        # Process in batches for progress tracking
        batch_size = 50
        processed = 0

        for i in range(0, total, batch_size):
            batch = activities[i:i + batch_size]
            results = self._classify_activities_parallel(batch)

            for activity_id, entry in results.items():
                self.cache.set(
                    activity_id=activity_id,
                    classification_data=entry['classification'],
                    basic_data=entry['basic_data']
                )

            processed += len(batch)

            # Save progress periodically
            if processed % batch_size == 0:
                self.cache.save()
                logger.info(f"Progress: {processed}/{total} activities processed")

        # Final save
        self.cache.update_sync_metadata()
        self.cache.save()

        elapsed = time.time() - start_time
        logger.info(f"Full sync complete: {processed} activities in {elapsed:.2f}s")

        return {
            "status": "success",
            "new_count": processed,
            "total_count": processed,
            "elapsed_seconds": elapsed,
        }

    def _classify_activities_parallel(self, activities: List[Dict]) -> Dict[int, Dict]:
        """Classify multiple activities in parallel.

        Args:
            activities: List of activity dicts from API

        Returns:
            Dict mapping activity_id to classification result
        """
        results = {}

        def classify_single(a: Dict) -> tuple:
            """Classify a single activity."""
            activity_id = a.get("activityId")
            activity_type = a.get("activityType", {}).get("typeKey", "")
            event_type = a.get("eventType", {}).get("typeKey", "")
            distance = a.get("distance", 0) or 0
            name = a.get("activityName", "")
            start_time = a.get("startTimeLocal", "")

            # Get HR zones
            hr_zones = []
            try:
                hr_data = self.client.get_activity_hr_in_timezones(activity_id)
                # API returns a list directly, not a dict with 'timeInHeartRateZones' key
                if hr_data and isinstance(hr_data, list):
                    hr_zones = hr_data
                elif hr_data and isinstance(hr_data, dict):
                    hr_zones = hr_data.get("timeInHeartRateZones", [])
            except Exception as e:
                logger.debug(f"Failed to get HR zones for {activity_id}: {e}")

            # Get laps
            laps = []
            try:
                laps_data = self.client.get_activity_splits(activity_id)
                # API returns 'lapDTOs', not 'lapDTOList'
                if laps_data:
                    laps = laps_data.get("lapDTOs", [])
            except Exception as e:
                logger.debug(f"Failed to get laps for {activity_id}: {e}")

            # Import classifier here to avoid circular import
            from .classifier import classify_activity

            # Classify
            classification = classify_activity(
                activity_type=activity_type,
                event_type=event_type,
                total_distance=distance,
                laps=laps,
                hr_zones=hr_zones,
            )

            basic_data = {
                "activity_type": activity_type,
                "event_type": event_type,
                "distance": distance,
                "name": name,
                "start_time": start_time[:19] if start_time else "",  # Truncate to datetime
            }

            return activity_id, {
                "classification": classification,
                "basic_data": basic_data,
            }

        # Parallel execution
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {executor.submit(classify_single, a): a for a in activities}

            for future in as_completed(futures):
                try:
                    activity_id, entry = future.result()
                    if activity_id:
                        results[activity_id] = entry
                except Exception as e:
                    logger.error(f"Error classifying activity: {e}")

        return results

    def refresh_activity(self, activity_id: int) -> Optional[Dict]:
        """Refresh classification for a single activity.

        Args:
            activity_id: Garmin activity ID

        Returns:
            Updated classification or None on error
        """
        try:
            activity = self.client.get_activity(activity_id)
            results = self._classify_activities_parallel([activity])

            if activity_id in results:
                entry = results[activity_id]
                self.cache.set(
                    activity_id=activity_id,
                    classification_data=entry['classification'],
                    basic_data=entry['basic_data']
                )
                self.cache.save()
                return entry['classification']

        except Exception as e:
            logger.error(f"Error refreshing activity {activity_id}: {e}")

        return None
