# OBD Diagnostics Dashboard

A real-time vehicle diagnostics dashboard built with FastAPI, TailwindCSS, and HTMX. Monitor your vehicle's OBD-II data with a modern, responsive web interface.

## Features

- **Real-time OBD Data**: Live monitoring of engine performance, temperature sensors, fuel system, and more
- **Interactive Dashboard**: Modern dark theme with responsive design
- **Settings Panel**: Configure temperature (°F/°C) and speed (MPH/KM/H) units
- **Diagnostic Assistant**: AI-powered chat assistant for vehicle diagnostics
- **Historical Charts**: Real-time metrics visualization with Chart.js
- **Check Engine Light**: MIL status monitoring with error code display
- **Connection Status**: Live connection indicator

## Prerequisites

- uv
- Docker (for InfluxDB)

## Getting Started

### Setup Environment

```bash
$ uv sync
```

### Start Database (Optional)

```bash
$ docker compose up -d db
```

### Run the Dashboard

#### Option 1: Using FastAPI CLI (Recommended)
```bash
$ fastapi dev main.py
```

#### Option 2: Using the run script
```bash
$ python run.py
```

#### Option 3: Using uvicorn directly
```bash
$ uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Accessing the Dashboard

Once running, open your browser and navigate to:
- **Local**: http://localhost:8000
- **Network**: http://0.0.0.0:8000

## Dashboard Sections

### Engine Performance
- Engine RPM
- Vehicle Speed
- Throttle Position
- Engine Load

### Temperature Sensors
- Coolant Temperature
- Oil Temperature
- Intake Air Temperature
- Ambient Temperature

### Fuel System
- Fuel Level
- Fuel Pressure
- Fuel Consumption Rate

### Air System
- Intake Manifold Pressure
- Barometric Pressure
- Battery Voltage

### System Status
- Battery Voltage
- Distance Traveled
- Engine Runtime

## API Endpoints

- `GET /` - Main dashboard page
- `GET /api/dashboard-content` - HTMX partial for dashboard content
- `GET /api/obd-data` - JSON OBD data
- `GET /api/chart-data` - Historical data for charts
- `GET /api/mil-status` - Check engine light status

## Configuration

The dashboard uses environment variables for InfluxDB connection:
- `INFLUXDB_URL`
- `INFLUXDB_TOKEN` 
- `INFLUXDB_ORG`
- `INFLUXDB_BUCKET`
- `VEHICLE_ID`

If no real OBD data is available, the dashboard will display mock data for demonstration purposes.

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: TailwindCSS, HTMX, Chart.js
- **Database**: InfluxDB (for real OBD data)
- **Real-time Updates**: HTMX polling every 2 seconds
