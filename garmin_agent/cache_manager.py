"""
Activity Classification Cache Manager

Provides CRUD operations for the activity classification cache.
Cache file: cache/activity_classification.json
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from .config import CACHE_DIR

logger = logging.getLogger(__name__)

# Default cache directory (private runtime state)
DEFAULT_CACHE_DIR = CACHE_DIR

# Current classifier version - increment when classification rules change
CLASSIFIER_VERSION = "1.0"


class ActivityClassificationCache:
    """
    Manages activity classification cache with atomic writes.

    Features:
    - Atomic writes via temp file + rename
    - Automatic backup before writes
    - Version tracking for cache invalidation
    """

    def __init__(self, cache_dir: Path = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache files (default: ./cache/)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_file = self.cache_dir / "activity_classification.json"
        self.backup_file = self.cache_dir / "activity_classification.json.bak"

        # Ensure directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._data: Dict[str, Any] = None

    def _get_empty_structure(self) -> Dict[str, Any]:
        """Return empty cache structure."""
        return {
            "metadata": {
                "version": "1.0",
                "last_sync": None,
                "last_activity_id": None,
                "total_count": 0,
                "classifier_version": CLASSIFIER_VERSION,
            },
            "activities": {}
        }

    def load(self) -> Dict[str, Any]:
        """Load cache from disk.

        Returns:
            Cache data dict with 'metadata' and 'activities' keys
        """
        if self._data is not None:
            return self._data

        if not self.cache_file.exists():
            logger.info("Cache file not found, creating new cache")
            self._data = self._get_empty_structure()
            return self._data

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self._data = json.load(f)

            # Validate structure
            if 'metadata' not in self._data or 'activities' not in self._data:
                logger.warning("Cache file has invalid structure, resetting")
                self._data = self._get_empty_structure()

            # Check classifier version - invalidate if outdated
            if self._data['metadata'].get('classifier_version') != CLASSIFIER_VERSION:
                logger.info(f"Classifier version changed ({self._data['metadata'].get('classifier_version')} -> {CLASSIFIER_VERSION}), clearing cache")
                self._data = self._get_empty_structure()

            logger.info(f"Loaded cache with {len(self._data['activities'])} activities")
            return self._data

        except json.JSONDecodeError as e:
            logger.error(f"Cache file corrupted: {e}, resetting")
            self._data = self._get_empty_structure()
            return self._data
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self._data = self._get_empty_structure()
            return self._data

    def save(self) -> None:
        """Save cache to disk atomically.

        Uses temp file + rename for atomic writes.
        Creates backup before overwriting.
        """
        if self._data is None:
            return

        try:
            # Create backup if file exists
            if self.cache_file.exists():
                shutil.copy2(self.cache_file, self.backup_file)

            # Write to temp file first
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

            # Atomic rename
            temp_file.replace(self.cache_file)

            logger.debug(f"Saved cache with {len(self._data['activities'])} activities")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            # Try to restore from backup
            if self.backup_file.exists():
                shutil.copy2(self.backup_file, self.cache_file)

    def get(self, activity_id: int) -> Optional[Dict[str, Any]]:
        """Get cached classification for an activity.

        Args:
            activity_id: Garmin activity ID

        Returns:
            Cached data dict or None if not found
        """
        data = self.load()
        return data['activities'].get(str(activity_id))

    def set(self, activity_id: int, classification_data: Dict[str, Any],
            basic_data: Dict[str, Any] = None) -> None:
        """Store classification for an activity.

        Args:
            activity_id: Garmin activity ID
            classification_data: Classification result with 'type', 'reason', 'zone_distribution'
            basic_data: Basic activity data (type, distance, name, start_time)
        """
        data = self.load()

        entry = {
            "activity_id": activity_id,
            "classification": classification_data,
            "basic_data": basic_data or {},
            "cached_at": datetime.now(timezone.utc).isoformat()
        }

        data['activities'][str(activity_id)] = entry
        data['metadata']['total_count'] = len(data['activities'])

        # Update last_activity_id if this is newer
        current_last = data['metadata'].get('last_activity_id')
        if current_last is None or activity_id > current_last:
            data['metadata']['last_activity_id'] = activity_id

    def get_all_by_type(self, training_type: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get all cached activities of a specific training type.

        Args:
            training_type: Training type (e.g., 'interval', 'tempo', 'easy')
            limit: Maximum number of results (None for all)

        Returns:
            List of activity entries, sorted by date (newest first)
        """
        data = self.load()

        results = []
        for entry in data['activities'].values():
            if entry.get('classification', {}).get('type') == training_type:
                results.append(entry)

        # Sort by start_time (newest first)
        def get_sort_key(entry):
            start_time = entry.get('basic_data', {}).get('start_time', '')
            return start_time or ''

        results.sort(key=get_sort_key, reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_last_sync_activity_id(self) -> Optional[int]:
        """Get the ID of the last synced activity.

        Returns:
            Activity ID or None if cache is empty
        """
        data = self.load()
        return data['metadata'].get('last_activity_id')

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last sync timestamp.

        Returns:
            datetime or None if never synced
        """
        data = self.load()
        last_sync = data['metadata'].get('last_sync')
        if last_sync:
            try:
                return datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning("Invalid last_sync date in cache: %s", last_sync)
                return None
        return None

    def needs_sync(self, max_age_hours: int = 24) -> bool:
        """Check if cache needs synchronization.

        Args:
            max_age_hours: Maximum age in hours before sync needed

        Returns:
            True if sync is needed
        """
        data = self.load()

        # No activities = needs full sync
        if not data['activities']:
            return True

        # Check last sync time
        last_sync = self.get_last_sync_time()
        if last_sync is None:
            return True

        # Check if cache is too old
        age = datetime.now(timezone.utc) - last_sync
        if age.total_seconds() > max_age_hours * 3600:
            return True

        return False

    def get_sync_age_hours(self) -> Optional[float]:
        """Get cache age in hours.

        Returns:
            Age in hours or None if never synced
        """
        last_sync = self.get_last_sync_time()
        if last_sync is None:
            return None

        age = datetime.now(timezone.utc) - last_sync
        return age.total_seconds() / 3600

    def update_sync_metadata(self) -> None:
        """Update metadata after sync completes."""
        data = self.load()
        data['metadata']['last_sync'] = datetime.now(timezone.utc).isoformat()
        data['metadata']['total_count'] = len(data['activities'])

    def clear(self) -> None:
        """Clear the entire cache."""
        self._data = self._get_empty_structure()

        # Remove files
        if self.cache_file.exists():
            self.cache_file.unlink()
        if self.backup_file.exists():
            self.backup_file.unlink()

        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with stats including count, type distribution, age
        """
        data = self.load()

        # Count by type
        type_counts = {}
        for entry in data['activities'].values():
            t = entry.get('classification', {}).get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_count": len(data['activities']),
            "type_distribution": type_counts,
            "last_sync": data['metadata'].get('last_sync'),
            "last_activity_id": data['metadata'].get('last_activity_id'),
            "classifier_version": data['metadata'].get('classifier_version'),
            "cache_age_hours": self.get_sync_age_hours(),
        }
