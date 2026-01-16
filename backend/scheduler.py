import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from api.constants import SyncFrequency, PlaylistSource
from playlist_manager import playlist_manager
from api.settings import settings

logger = logging.getLogger(__name__)

class PlaylistScheduler:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
        
    def _setup_jobs(self):
        # Run check once daily at the configured time
        hour, minute = map(int, settings.sync_time.split(':'))
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            self.check_for_updates,
            trigger=trigger,
            id='playlist_sync_check',
            name='Check playlists for updates',
            replace_existing=True
        )
        logger.info(f"PlaylistScheduler jobs setup (Daily at {settings.sync_time})")

    def reschedule_job(self, new_time: str):
        if self.scheduler.get_job('playlist_sync_check'):
            hour, minute = map(int, new_time.split(':'))
            self.scheduler.reschedule_job(
                'playlist_sync_check',
                trigger=CronTrigger(hour=hour, minute=minute)
            )
            logger.info(f"PlaylistScheduler rescheduled to {new_time}")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("PlaylistScheduler started")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("PlaylistScheduler shutdown")

    async def check_for_updates(self):
        logger.info("Running scheduled playlist update check...")
        playlists = playlist_manager.get_monitored_playlists()
        
        now = datetime.now()

        for p in playlists:
            uuid = p['uuid']
            name = p['name']
            
            # Use MonitoredPlaylist object wrapper if dict is returned, or just access dict
            # playlist_manager returns dicts from get_monitored_playlists
            # Let's use the logic directly on the dict to match existing pattern, but use constants
            
            frequency = p.get('sync_frequency', SyncFrequency.MANUAL)
            last_sync_str = p.get('last_sync')
            source = p.get('source', PlaylistSource.TIDAL)
            
            should_sync, reason = self._should_sync(frequency, last_sync_str, source, now)
            
            if should_sync:
                logger.info(f"Triggering scheduled sync for playlist: {name} (Reason: {reason})")
                try:
                    await playlist_manager.sync_playlist(uuid)
                except Exception as e:
                    logger.error(f"Scheduled sync failed for {name}: {e}")
            else:
                 logger.debug(f"Skipping sync for {name} (Reason: {reason})")

    def _should_sync(self, frequency: str, last_sync_str: str, source: str, now: datetime) -> tuple[bool, str]:
        if frequency == SyncFrequency.MANUAL:
            return False, "Manual frequency"
            
        if not last_sync_str:
            return True, "Never synced"
            
        try:
            # Handle ISO timestamp if present (contains 'T')
            if 'T' in last_sync_str:
                last_sync_date = datetime.fromisoformat(last_sync_str).date()
            else:
                last_sync_date = datetime.strptime(last_sync_str, "%Y-%m-%d").date()
        except ValueError:
            return True, "Invalid last_sync date format"
            
        today = now.date()
        days_diff = (today - last_sync_date).days
        
        if frequency == SyncFrequency.DAILY:
            if days_diff >= 1:
                return True, f"Daily interval passed ({days_diff} days)"
                
        elif frequency == SyncFrequency.WEEKLY:
            # 1. Robust Backup: > 7 days
            if days_diff >= 7:
                return True, f"Weekly backup interval passed ({days_diff} days)"
            
            # 2. Preferred Day for ListenBrainz: Tuesday
            if source == PlaylistSource.LISTENBRAINZ:
                # Tuesday is weekday 1
                is_tuesday = (now.weekday() == 1)
                if is_tuesday and today != last_sync_date:
                    return True, "Tuesday preference for ListenBrainz"

        elif frequency == SyncFrequency.MONTHLY:
            # 1. Robust Backup: > 30 days
            if days_diff >= 30:
                return True, f"Monthly backup interval passed ({days_diff} days)"
            
            # 2. Preferred Day: 1st of month
            if now.day == 1 and today != last_sync_date:
                return True, "1st of month preference"

        elif frequency == SyncFrequency.YEARLY:
            # 1. Robust Backup: > 365 days
            if days_diff >= 365:
                return True, f"Yearly interval passed ({days_diff} days)"
            
            # 2. Preferred Day: Jan 1st
            is_jan_first = (now.month == 1 and now.day == 1)
            if is_jan_first and today != last_sync_date:
                return True, "Jan 1st preference"
                
        return False, "No condition met"
