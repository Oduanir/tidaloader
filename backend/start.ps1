# Activate venv and start server on port 8001
.\venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8001