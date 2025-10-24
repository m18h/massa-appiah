import json
import os

import dspy
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from loguru import logger
from pydantic import BaseModel

load_dotenv()

INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
VEHICLE_ID = os.getenv("VEHICLE_ID", "vehicle_001")


# ============================================
# MODELS
# ============================================


class OBDMetric(BaseModel):
    # time: datetime
    rpm: int
    speed: int
    throttle_position: float
    engine_load: float
    coolant_temp: int
    intake_temp: int
    oil_temp: int
    fuel_level: float
    fuel_pressure: float
    fuel_rate: float
    intake_pressure: float
    battery_voltage: float
    ambient_temp: int
    barometric_pressure: float
    distance: float
    runtime: int
    mil_status: bool
    dtc_count: int


# ============================================
# DB SETUP
# ============================================


class DB:
    def __init__(self):
        self.__url = os.getenv("INFLUXDB_URL")
        self.__token = os.getenv("INFLUXDB_TOKEN")
        self.__org = os.getenv("INFLUXDB_ORG")
        self.__bucket = INFLUXDB_BUCKET
        self.__vehicle_id = VEHICLE_ID
        self.__client = None

        # Validate InfluxDB settings (required)
        if not self.__url:
            raise ValueError("INFLUXDB_URL environment variable is required")
        if not self.__token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")
        if not self.__org:
            raise ValueError("INFLUXDB_ORG environment variable is required")
        if not self.__bucket:
            raise ValueError("INFLUXDB_BUCKET environment variable is required")

    def __enter__(self):
        logger.debug(f"Connecting to InfluxDB: {self.__url}")
        self.__client = InfluxDBClient(
            url=self.__url, token=self.__token, org=self.__org
        )
        logger.success(f"InfluxDB Connection Opened. Bucket: {self.__bucket}")
        logger.debug(f"Vehicle ID: {self.__vehicle_id}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__client.close()
        logger.debug("InfluxDB Connection Closed")

    def store_data(self, data):
        write_api = self.__client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=self.__bucket, record=data)

    def get_data(self, query):
        query_api = self.__client.query_api()
        result = query_api.query(query=query, org=self.__org)
        return result

    def get_recent_data(self, hours=1, limit=100):
        """Get recent OBD data for vehicle"""

        query = f"""
        from(bucket: "{self.__bucket}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "obd_readings")
          |> filter(fn: (r) => r["vehicle_id"] == "{self.__vehicle_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> limit(n: {limit})
        """

        result = self.get_data(query=query)
        return self._parse_pivoted_results(result)

    def get_latest_reading(self):
        """Get the most recent OBD reading for a vehicle"""
        query = f"""
        from(bucket: "{self.__bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "obd_readings")
          |> filter(fn: (r) => r["vehicle_id"] == "{self.__vehicle_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 1)
        """

        result = self.get_data(query=query)
        data = self._parse_pivoted_results(result)
        return data[0] if data else None

    def get_field_stats(self, field, hours=24):
        """Get statistics (min, max, mean) for a specific field"""

        query = f"""
        from(bucket: "{self.__bucket}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "obd_readings")
          |> filter(fn: (r) => r["_field"] == "{field}")
          |> filter(fn: (r) => r["vehicle_id"] == "{self.__vehicle_id}")
        """

        result = self.get_data(query=query)
        values = [record.get_value() for table in result for record in table.records]

        if not values:
            return None

        return {
            "field": field,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "count": len(values),
        }

    def get_aggregated_data(self, field, hours=24, window="10m"):
        """Get aggregated data for a specific field over time"""

        query = f"""
        from(bucket: "{self.__bucket}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "obd_readings")
          |> filter(fn: (r) => r["_field"] == "{field}")
          |> filter(fn: (r) => r["vehicle_id"] == "{self.__vehicle_id}")
          |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
        """

        result = self.get_data(query=query)
        return [
            {"time": record.get_time().isoformat(), "value": record.get_value()}
            for table in result
            for record in table.records
        ]

    def get_mil_status_history(self, hours=24):
        """Get check engine light status history"""
        query = f"""
        from(bucket: "{self.__bucket}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "obd_readings")
          |> filter(fn: (r) => r["vehicle_id"] == "{self.__vehicle_id}")
          |> keep(columns: ["_time", "mil_status", "dtc_count"])
          |> group()
        """

        result = self.get_data(query=query)
        return self._parse_results(result)

    def _parse_pivoted_results(self, result):
        """Parse pivoted InfluxDB query results"""
        data_points = []
        for table in result:
            for record in table.records:
                point = {"time": record.get_time().isoformat()}

                # Add all fields from the record
                for key, value in record.values.items():
                    if not key.startswith("_") and key not in ["result", "table"]:
                        point[key] = value

                data_points.append(point)
        return data_points

    def _parse_results(self, result):
        """Parse standard InfluxDB query results"""
        data_points = []
        for table in result:
            for record in table.records:
                data_points.append(
                    {
                        "time": record.get_time().isoformat(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "measurement": record.get_measurement(),
                    }
                )
        return data_points


# ============================================
# DSPY SETUP
# ============================================


class OBDDataAnalysis(dspy.Signature):
    """Analyze OBD vehicle data and provide insights"""

    obd_data = dspy.InputField(desc="Raw OBD data from vehicle sensors")
    question = dspy.InputField(desc="Question about the vehicle data")
    analysis = dspy.OutputField(desc="Detailed analysis and answer to the question")


class VehicleDiagnostics(dspy.Signature):
    """Diagnose potential vehicle issues from OBD data"""

    current_reading = dspy.InputField(desc="Current OBD sensor readings")
    statistics = dspy.InputField(desc="Statistical summary of recent readings")
    diagnostics = dspy.OutputField(
        desc="Diagnostic assessment, potential issues, and recommendations"
    )


class TrendAnalysis(dspy.Signature):
    """Analyze trends in vehicle data over time"""

    field_name = dspy.InputField(desc="Name of the sensor/field being analyzed")
    statistics = dspy.InputField(desc="Min, max, mean values over time period")
    time_series = dspy.InputField(desc="Time-series data points")
    analysis = dspy.OutputField(desc="Trend analysis and insights")


class MaintenanceAdvisor(dspy.Signature):
    """Provide maintenance recommendations based on OBD data"""

    obd_readings = dspy.InputField(desc="Current vehicle sensor readings")
    dtc_info = dspy.InputField(desc="Diagnostic trouble code information")
    mileage = dspy.InputField(desc="Total distance traveled")
    recommendations = dspy.OutputField(
        desc="Maintenance recommendations based on OBD data"
    )


class OBDQueryModule(dspy.Module):
    """Module for querying and analyzing OBD data"""

    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(OBDDataAnalysis)

    def forward(self, obd_data, question):
        return self.analyze(obd_data=obd_data, question=question)


class DiagnosticsModule(dspy.Module):
    """Module for vehicle diagnostics"""

    def __init__(self):
        super().__init__()
        self.diagnose = dspy.ChainOfThought(VehicleDiagnostics)

    def forward(self, current_reading, statistics):
        return self.diagnose(current_reading=current_reading, statistics=statistics)


class TrendModule(dspy.Module):
    """Module for trend analysis"""

    def __init__(self):
        super().__init__()
        self.analyze_trend = dspy.ChainOfThought(TrendAnalysis)

    def forward(self, field_name, statistics, time_series):
        return self.analyze_trend(
            field_name=field_name, statistics=statistics, time_series=time_series
        )


class MaintenanceModule(dspy.Module):
    """Module for maintenance recommendations"""

    def __init__(self):
        super().__init__()
        self.advise = dspy.ChainOfThought(MaintenanceAdvisor)

    def forward(self, obd_readings, dtc_info, mileage):
        return self.advise(
            obd_readings=obd_readings, dtc_info=dtc_info, mileage=mileage
        )


# ============================================
# 5. MAIN APPLICATION CLASS
# ============================================


class LLM:
    """
    LLM engine for querying and analyzing OBD data
    """

    def __init__(self, model=None):
        # Setup InfluxDB
        self.__db = DB()

        # Setup DSPy with LLM
        lm = dspy.LM(
            model=os.getenv("LLM_API_MODEL", "ollama_chat/tinyllama"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
            api_base=os.getenv("LLM_API_BASE", "http://localhost:11434"),
        )
        dspy.settings.configure(lm=lm)

        # Initialize DSPy modules
        self.__query_module = OBDQueryModule()
        self.__diagnostics_module = DiagnosticsModule()
        self.__trend_module = TrendModule()
        self.__maintenance_module = MaintenanceModule()

    def __enter__(self):
        self.__db.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__db.__exit__(exc_type, exc_value, traceback)

    def query(self, question, hours=1):
        """Query OBD data"""
        # Retrieve recent data from InfluxDB
        data = self.__db.get_recent_data(vehicle_id=VEHICLE_ID, hours=hours)

        # Format data for DSPy
        formatted_data = self._format_readings(data)

        # print(data)

        # Get response from DSPy
        response = self.__query_module(obd_data=formatted_data, question=question)

        return response.analysis

    def diagnose(self, hours=24):
        """Get diagnostic assessment of vehicle health"""
        # Get latest reading
        latest = self.__db.get_latest_reading(VEHICLE_ID)

        # Get statistics for key parameters
        key_fields = [
            "rpm",
            "coolant_temp",
            "engine_load",
            "fuel_rate",
            "battery_voltage",
        ]
        stats = {}
        for field in key_fields:
            field_stats = self.__db.get_field_stats(field, VEHICLE_ID, hours)
            if field_stats:
                stats[field] = field_stats

        # Format for DSPy
        current_formatted = self._format_reading(latest)
        stats_formatted = json.dumps(stats, indent=2)

        response = self.__diagnostics_module(
            current_reading=current_formatted, statistics=stats_formatted
        )
        return response.diagnostics

    def analyze_trend(self, field_name, hours=24):
        """Analyze trends for a specific sensor/field"""
        # Get statistics
        stats = self.__db.get_field_stats(field_name, VEHICLE_ID, hours)

        # Get time series data
        time_series = self.__db.get_aggregated_data(
            field_name, VEHICLE_ID, hours, window="10m"
        )

        if not stats or not time_series:
            return f"No data available for {field_name}"

        response = self.__trend_module(
            field_name=field_name,
            statistics=json.dumps(stats, indent=2),
            time_series=json.dumps(
                time_series[:20], indent=2
            ),  # Limit to recent points
        )
        return response.analysis

    def get_maintenance_advice(self):
        """Get maintenance recommendations"""
        latest = self.__db.get_latest_reading(VEHICLE_ID)

        if not latest:
            return "No recent data available"

        # Format current readings
        readings_formatted = self._format_reading(latest)

        # Format DTC info
        dtc_info = f"MIL Status: {latest.get('mil_status', 'Unknown')}\n"
        dtc_info += f"DTC Count: {latest.get('dtc_count', 0)}"

        # Get mileage
        mileage = latest.get("distance", 0)

        response = self.__maintenance_module(
            obd_readings=readings_formatted, dtc_info=dtc_info, mileage=str(mileage)
        )
        return response.recommendations

    def _format_reading(self, reading):
        """Format a single OBD reading for LLM"""
        if not reading:
            return "No data available"

        formatted = "Current Vehicle Readings:\n"
        formatted += f"Time: {reading.get('time', 'Unknown')}\n"
        formatted += f"Vehicle ID: {reading.get('vehicle_id', VEHICLE_ID)}\n\n"

        # Engine parameters
        formatted += "Engine:\n"
        formatted += f"  - RPM: {reading.get('rpm')} rpm\n"
        formatted += f"  - Speed: {reading.get('speed')} km/h\n"
        formatted += f"  - Throttle Position: {reading.get('throttle_position')}%\n"
        formatted += f"  - Engine Load: {reading.get('engine_load')}%\n"
        formatted += f"  - Runtime: {reading.get('runtime')} seconds\n\n"

        # Temperature sensors
        formatted += "Temperatures:\n"
        formatted += f"  - Coolant: {reading.get('coolant_temp')}°C\n"
        formatted += f"  - Intake Air: {reading.get('intake_temp')}°C\n"
        formatted += f"  - Oil: {reading.get('oil_temp')}°C\n"
        formatted += f"  - Ambient: {reading.get('ambient_temp')}°C\n\n"

        # Fuel system
        formatted += "Fuel System:\n"
        formatted += f"  - Fuel Level: {reading.get('fuel_level')}%\n"
        formatted += f"  - Fuel Pressure: {reading.get('fuel_pressure')} kPa\n"
        formatted += f"  - Fuel Rate: {reading.get('fuel_rate')} L/h\n\n"

        # Air flow
        formatted += "Air Flow:\n"
        formatted += f"  - MAF: {reading.get('maf')} g/s\n"
        formatted += f"  - Intake Pressure: {reading.get('intake_pressure')} kPa\n"
        formatted += (
            f"  - Barometric Pressure: {reading.get('barometric_pressure')} kPa\n\n"
        )

        # Other sensors
        formatted += "Other:\n"
        formatted += f"  - Battery Voltage: {reading.get('battery_voltage')} V\n"
        formatted += f"  - Distance: {reading.get('distance')} km\n"
        formatted += f"  - MIL Status: {reading.get('mil_status')}\n"
        formatted += f"  - DTC Count: {reading.get('dtc_count')}\n"

        return formatted

    def _format_readings(self, readings):
        """Format multiple OBD readings for LLM"""
        if not readings:
            return "No data available"

        formatted = f"Vehicle Data ({len(readings)} readings):\n\n"

        # Show latest reading in detail
        if readings:
            formatted += "Latest Reading:\n"
            formatted += self._format_reading(readings[-1])

        return formatted
