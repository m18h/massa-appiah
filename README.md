# Massa Appiah - OBD Diagnostics Dashboard

A real-time vehicle diagnostics TUI dashboard, powered by LLM.

> Currently built to work with Ollama. Support for OpenAI compatible APIs later.

## Features

- **Real-time OBD Data**: Live monitoring of engine performance, temperature sensors, fuel system, and more
- **TUI Dashboard**: Modern dark theme with responsive design
- **Settings Panel**: Configure temperature (°F/°C) and speed (MPH/KM/H) units [Coming Soon]
- **Diagnostic Assistant**: AI-powered chat assistant for vehicle diagnostics
- **Historical Charts**: Real-time metrics visualization [Coming Soon]
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

```bash
$ uv run app.py
```
