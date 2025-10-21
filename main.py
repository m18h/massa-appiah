from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random
from datetime import datetime, timedelta
from utils import DB, VEHICLE_ID
import os

app = FastAPI(title="OBD Diagnostics Dashboard")

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/obd-data")
async def get_obd_data():
    """Get current OBD data"""
    try:
        with DB() as db:
            latest = db.get_latest_reading(VEHICLE_ID)
            if not latest:
                # Return mock data if no real data available
                return get_mock_data()
            return latest
    except Exception:
        # Return mock data on error
        return get_mock_data()

@app.get("/api/dashboard-content", response_class=HTMLResponse)
async def get_dashboard_content(request: Request):
    """Get dashboard content as HTML partial"""
    try:
        with DB() as db:
            latest = db.get_latest_reading(VEHICLE_ID)
            if not latest:
                latest = get_mock_data()
    except Exception:
        latest = get_mock_data()
    
    return templates.TemplateResponse("dashboard_content.html", {
        "request": request,
        "data": latest
    })

@app.get("/api/chart-data")
async def get_chart_data():
    """Get historical data for charts"""
    try:
        with DB() as db:
            # Get last 24 hours of data
            data = db.get_recent_data(VEHICLE_ID, hours=24, limit=100)
            return {"data": data}
    except Exception:
        # Return mock chart data
        now = datetime.now()
        mock_data = []
        for i in range(24):
            timestamp = now - timedelta(hours=23-i)
            mock_data.append({
                "time": timestamp.isoformat(),
                "rpm": random.randint(800, 3000),
                "speed": random.randint(0, 80),
                "coolant_temp": random.randint(80, 105),
                "fuel_level": random.randint(20, 100)
            })
        return {"data": mock_data}

@app.get("/api/mil-status")
async def get_mil_status():
    """Get MIL (Check Engine Light) status"""
    try:
        with DB() as db:
            history = db.get_mil_status_history(VEHICLE_ID, hours=24)
            current_status = history[-1] if history else {"status": False, "codes": []}
            return current_status
    except Exception:
        return {
            "status": True,
            "codes": ["P0113"],
            "description": "Intake Air Temperature Sensor Circuit High"
        }

def get_mock_data():
    """Generate mock OBD data for demonstration"""
    return {
        "timestamp": datetime.now().isoformat(),
        "vehicle_id": VEHICLE_ID,
        "engine_rpm": random.randint(800, 3000),
        "speed": random.randint(0, 80),
        "throttle_position": random.randint(0, 100),
        "engine_load": random.randint(20, 90),
        "coolant_temp": random.randint(80, 105),
        "oil_temp": random.randint(85, 110),
        "intake_temp": random.randint(15, 35),
        "ambient_temp": random.randint(10, 30),
        "fuel_level": random.randint(20, 100),
        "fuel_pressure": random.randint(250, 300),
        "fuel_rate": random.randint(5, 15),
        "intake_pressure": random.randint(20, 30),
        "barometric_pressure": random.randint(95, 105),
        "battery_voltage": round(random.uniform(12.0, 14.5), 1),
        "distance": random.randint(450, 500),
        "runtime": random.randint(180, 240)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)