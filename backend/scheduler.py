import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

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
        
        for p in playlists:
            uuid = p['uuid']
            name = p['name']
            frequency = p.get('sync_frequency', 'manual')
            last_sync_str = p.get('last_sync')
            
            if frequency == 'manual':
                continue
                
            should_sync = False
            
            # Logic: 
            # - 'daily': sync every time scheduler runs (once a day)
            # - 'weekly': sync if it's Monday (ListenBrainz Weekly Jams usually out on Mon)
            # - 'yearly': sync if it's January 1st
            
            now = datetime.now()
            
            if frequency == 'daily':
                # Sync if > 1 day elapsed or never synced
                if not last_sync_str:
                    should_sync = True
                else:
                    try:
                        last_sync = datetime.strptime(last_sync_str, "%Y-%m-%d")
                        if (now - last_sync).days >= 1:
                            should_sync = True
                    except ValueError:
                        should_sync = True

            elif frequency == 'weekly':
                # Differentiate based on source
                source = p.get('source', '')
                is_listenbrainz = (source == 'listenbrainz')
                
                # If ListenBrainz: Prefer Tuesday (weekday=1)
                # Others: Strict 7 days
                
                if not last_sync_str:
                    should_sync = True
                else:
                    try:
                        last_sync = datetime.strptime(last_sync_str, "%Y-%m-%d")
                        days_diff = (now - last_sync).days
                        
                        if days_diff >= 7:
                            should_sync = True
                        elif is_listenbrainz and (now.weekday() == 1) and days_diff >= 1 and last_sync.date() != now.date():
                             # It's Tuesday, it's ListenBrainz, and we haven't synced today
                             should_sync = True
                    except ValueError:
                        should_sync = True

            elif frequency == 'monthly':
                # Sync if > 30 days elapsed OR moved to next month (roughly)
                # Let's say: Sync on the 1st of month OR if > 30 days
                
                if not last_sync_str:
                    should_sync = True
                else:
                    try:
                        last_sync = datetime.strptime(last_sync_str, "%Y-%m-%d")
                        days_diff = (now - last_sync).days
                        
                        if days_diff >= 30:
                            should_sync = True
                        elif now.day == 1 and last_sync.month != now.month:
                             should_sync = True
                    except ValueError:
                        should_sync = True

            elif frequency == 'yearly':
                # Sync if > 365 days elapsed OR Jan 1st
                is_jan_first = (now.month == 1 and now.day == 1)
                
                if not last_sync_str:
                    should_sync = True
                else:
                    try:
                        last_sync = datetime.strptime(last_sync_str, "%Y-%m-%d")
                        if (now - last_sync).days >= 365:
                            should_sync = True
                        elif is_jan_first and last_sync.date() != now.date():
                            should_sync = True
                    except ValueError:
                        should_sync = True
            
            if should_sync:
                logger.info(f"Triggering scheduled sync for playlist: {name} (Freq: {frequency}, Last: {last_sync_str})")
                try:
                    await playlist_manager.sync_playlist(uuid)
                except Exception as e:
                    logger.error(f"Scheduled sync failed for {name}: {e}")
            else:
                 logger.debug(f"Skipping sync for {name} (Freq: {frequency}, Last: {last_sync_str})")
