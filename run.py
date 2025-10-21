#!/usr/bin/env python3
"""
Simple script to run the OBD Diagnostics Dashboard
"""
import uvicorn

from main import app

if __name__ == "__main__":
    print("Starting OBD Diagnostics Dashboard...")
    print("Dashboard will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")
