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

hours = 24


def main():
    with DB() as db:
        dtc_query = f"""
        from(bucket: "{os.getenv('INFLUXDB_BUCKET')}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r["_measurement"] == "obd_dtc_events")
        |> filter(fn: (r) => r["vehicle_id"] == "{VEHICLE_ID}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        dtc_res = db.get_data(dtc_query)

        # Query aggregate statistics
        stats_query = f"""
        from(bucket: "{os.getenv('INFLUXDB_BUCKET')}")
        |> range(start: -{hours}h)
        |> filter(fn: (r) => r["_measurement"] == "obd_readings")
        |> filter(fn: (r) => r["vehicle_id"] == "{VEHICLE_ID}")
        |> mean()
        """
        stats_res = db.get_data(stats_query)

        # Format for LLM
        context = f"Vehicle {VEHICLE_ID} - Last {hours} hours:\n\n"

        # Add statistics
        context += "Average Conditions:\n"
        for table in stats_res:
            for record in table.records:
                context += f"- {record.get_field()}: {record.get_value():.2f}\n"

        # Add DTCs
        if dtc_res:
            context += "\n⚠️ Diagnostic Events:\n"
            for table in dtc_res:
                for record in table.records:
                    context += f"- [{record.get_time()}] {record['dtc_code']}: {record['description']}\n"

        logger.info(context)


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    logger.info("Mock Query")
    logger.info("=" * 70)

    main()
