import json
import os
import random
import time
from datetime import datetime

from dotenv import load_dotenv
from influxdb_client import Point
from loguru import logger

from utils import DB

load_dotenv()

VEHICLE_ID = os.getenv("VEHICLE_ID", "vehicle_001")


def mock_obd_data():
    """
    Mock OBD-II data for testing InfluxDB storage.
    Returns a dictionary with common vehicle parameters including DTCs.
    """

    # Common DTC codes for check engine light scenarios
    dtc_pool = [
        {"code": "P0300", "description": "Random/Multiple Cylinder Misfire Detected"},
        {"code": "P0420", "description": "Catalyst System Efficiency Below Threshold"},
        {"code": "P0171", "description": "System Too Lean (Bank 1)"},
        {
            "code": "P0128",
            "description": "Coolant Thermostat Temperature Below Regulating Temperature",
        },
        {"code": "P0442", "description": "EVAP System Leak Detected (small leak)"},
        {"code": "P0455", "description": "EVAP System Leak Detected (large leak)"},
        {"code": "P0301", "description": "Cylinder 1 Misfire Detected"},
        {"code": "P0401", "description": "EGR System Flow Insufficient"},
        {
            "code": "P0507",
            "description": "Idle Control System RPM Higher Than Expected",
        },
        {"code": "P0113", "description": "Intake Air Temperature Sensor Circuit High"},
    ]

    # Decide if there are any DTCs present
    has_dtc = random.choice([True, False, False])  # 33% chance of having DTCs
    dtc_count = random.randint(1, 3) if has_dtc else 0
    active_dtcs = random.sample(dtc_pool, dtc_count) if dtc_count > 0 else []

    # Simulate realistic ranges for various OBD parameters
    mock_data = {
        # Engine parameters
        "rpm": random.randint(700, 3500),  # Engine RPM
        "speed": random.randint(0, 120),  # Vehicle speed (km/h or mph)
        "throttle_position": round(random.uniform(0, 100), 2),  # Throttle %
        "engine_load": round(random.uniform(10, 90), 2),  # Engine load %
        # Temperature sensors
        "coolant_temp": random.randint(75, 105),  # Coolant temperature (°C)
        "intake_temp": random.randint(20, 60),  # Intake air temperature (°C)
        "oil_temp": random.randint(80, 110),  # Oil temperature (°C)
        # Fuel system
        "fuel_level": round(random.uniform(10, 95), 2),  # Fuel level %
        "fuel_pressure": round(random.uniform(200, 400), 2),  # Fuel pressure (kPa)
        "fuel_rate": round(random.uniform(0.5, 15), 2),  # Fuel consumption rate (L/h)
        # Air flow
        "maf": round(random.uniform(2, 25), 2),  # Mass air flow (grams/sec)
        "intake_pressure": round(
            random.uniform(30, 100), 2
        ),  # Intake manifold pressure (kPa)
        # Other sensors
        "battery_voltage": round(random.uniform(12.5, 14.5), 2),  # Battery voltage
        "ambient_temp": random.randint(15, 35),  # Ambient air temperature (°C)
        "barometric_pressure": round(
            random.uniform(95, 105), 2
        ),  # Barometric pressure (kPa)
        # Calculated values
        "distance": round(random.uniform(0, 50000), 1),  # Distance traveled (km)
        "runtime": random.randint(0, 10000),  # Engine runtime (seconds)
        # Diagnostic information
        "mil_status": has_dtc,  # Check engine light (MIL) - Malfunction Indicator Lamp
        "dtc_count": dtc_count,  # Diagnostic trouble codes count
        "dtcs": active_dtcs,  # List of active DTCs with codes and descriptions
        # Timestamp
        "timestamp": datetime.now().isoformat(),
        "unix_timestamp": int(time.time()),
    }

    return mock_data


def mock_obd_stream(duration_seconds=10, interval=1):
    """
    Generate a stream of mock OBD data for a specified duration.

    Args:
        duration_seconds: How long to generate data (seconds)
        interval: Time between readings (seconds)

    Yields:
        Dictionary of mock OBD data
    """
    end_time = time.time() + duration_seconds

    while time.time() < end_time:
        yield mock_obd_data()
        time.sleep(interval)


def store_to_db(db, obd_reading):
    """
    Store OBD reading to InfluxDB.

    Args:
        obd_reading: Dictionary containing OBD data
    """

    # Create point for raw sensor readings
    point = (
        Point("obd_readings")
        .tag("vehicle_id", VEHICLE_ID)
        .tag("mil_status", str(obd_reading["mil_status"]))
        .field("rpm", obd_reading["rpm"])
        .field("speed", obd_reading["speed"])
        .field("throttle_position", obd_reading["throttle_position"])
        .field("engine_load", obd_reading["engine_load"])
        .field("coolant_temp", obd_reading["coolant_temp"])
        .field("intake_temp", obd_reading["intake_temp"])
        .field("oil_temp", obd_reading["oil_temp"])
        .field("fuel_level", obd_reading["fuel_level"])
        .field("fuel_pressure", obd_reading["fuel_pressure"])
        .field("fuel_rate", obd_reading["fuel_rate"])
        .field("maf", obd_reading["maf"])
        .field("intake_pressure", obd_reading["intake_pressure"])
        .field("battery_voltage", obd_reading["battery_voltage"])
        .field("ambient_temp", obd_reading["ambient_temp"])
        .field("barometric_pressure", obd_reading["barometric_pressure"])
        .field("distance", obd_reading["distance"])
        .field("runtime", obd_reading["runtime"])
        .field("dtc_count", obd_reading["dtc_count"])
    )

    db.store_data(point)

    # If there are DTCs, store them as separate events for easier querying
    if obd_reading["dtc_count"] > 0:
        for dtc in obd_reading["dtcs"]:
            dtc_point = (
                Point("obd_dtc_events")
                .tag("vehicle_id", VEHICLE_ID)
                .tag("dtc_code", dtc["code"])
                .tag(
                    "severity",
                    "high" if "misfire" in dtc["description"].lower() else "medium",
                )
                .field("description", dtc["description"])
                .field("rpm", obd_reading["rpm"])
                .field("speed", obd_reading["speed"])
                .field("coolant_temp", obd_reading["coolant_temp"])
                .field("engine_load", obd_reading["engine_load"])
            )

            db.store_data(dtc_point)


def collect_and_store_obd_data(duration_seconds=60, interval=2):
    """
    Collect mock OBD data and store to InfluxDB using environment variables.

    Optional environment variables:
        OBD_DURATION: Duration to collect data in seconds (default: 60)
        OBD_INTERVAL: Interval between readings in seconds (default: 2)
    """

    duration = int(os.getenv("OBD_DURATION", duration_seconds))
    interval = float(os.getenv("OBD_INTERVAL", interval))

    try:
        logger.info(f"Starting data collection for {duration}s (interval: {interval}s)")
        logger.info("=" * 70)

        # Collect and store mock OBD data
        with DB() as db:
            reading_count = 0
            for obd_reading in mock_obd_stream(
                duration_seconds=duration, interval=interval
            ):
                reading_count += 1

                # Store to DB
                try:
                    store_to_db(db, obd_reading)
                except Exception as e:
                    logger.error(f"DB write error: {e}")
                    continue

                # Log summary
                dtc_info = (
                    f", DTCs: {obd_reading['dtc_count']}"
                    if obd_reading["dtc_count"] > 0
                    else ""
                )
                mil_status = "⚠️  CHECK ENGINE" if obd_reading["mil_status"] else "✓ OK"

                if obd_reading["mil_status"]:
                    logger.warning(
                        f"[{reading_count:03d}] [{mil_status}] RPM: {obd_reading['rpm']:4d}, "
                        f"Speed: {obd_reading['speed']:3d} km/h, "
                        f"Coolant: {obd_reading['coolant_temp']:3d}°C{dtc_info}"
                    )
                else:
                    logger.info(
                        f"[{reading_count:03d}] [{mil_status}] RPM: {obd_reading['rpm']:4d}, "
                        f"Speed: {obd_reading['speed']:3d} km/h, "
                        f"Coolant: {obd_reading['coolant_temp']:3d}°C{dtc_info}"
                    )

                if obd_reading["dtc_count"] > 0:
                    for dtc in obd_reading["dtcs"]:
                        logger.warning(f"      └─ {dtc['code']}: {dtc['description']}")

        logger.info("=" * 70)
        logger.success(f"Completed: {reading_count} readings stored to InfluxDB")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # Example: Single mock reading to see the data structure
    logger.info("Sample mock OBD reading:")
    logger.info("=" * 70)
    sample_data = mock_obd_data()
    print(json.dumps(sample_data, indent=2))
    logger.info("=" * 70)

    # Start collecting and storing to InfluxDB
    collect_and_store_obd_data()
