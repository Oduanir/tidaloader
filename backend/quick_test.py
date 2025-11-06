"""Quick test to verify imports work"""
try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    import requests
    print("✓ All imports successful!")
    print("✓ Backend dependencies are ready")
except ImportError as e:
    print(f"✗ Import failed: {e}")