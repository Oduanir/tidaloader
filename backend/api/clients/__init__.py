import sys
from pathlib import Path

# Add backend directory to path so we can import tidal_client
# __file__ = backend/api/clients/__init__.py
# parent = backend/api/clients
# parent.parent = backend/api
# parent.parent.parent = backend

backend_path = Path(__file__).parent.parent.parent
sys.path.append(str(backend_path))

try:
    from tidal_client import TidalAPIClient
except ImportError:
    # Fallback if running from root
    from backend.tidal_client import TidalAPIClient

tidal_client = TidalAPIClient()

# Export ListenBrainzClient for easier access
from .listenbrainz import ListenBrainzClient
