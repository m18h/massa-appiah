import os

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from loguru import logger

load_dotenv()


class DB:
    def __init__(self):
        self.__url = os.getenv("INFLUXDB_URL")
        self.__token = os.getenv("INFLUXDB_TOKEN")
        self.__org = os.getenv("INFLUXDB_ORG")
        self.__bucket = os.getenv("INFLUXDB_BUCKET")
        self.__vehicle_id = os.getenv("VEHICLE_ID", "vehicle_001")
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
        logger.info(f"Connecting to InfluxDB: {self.__url}")
        self.__client = InfluxDBClient(
            url=self.__url, token=self.__token, org=self.__org
        )
        logger.success(f"Connected to InfluxDB. Writing to bucket: {self.__bucket}")
        logger.info(f"Vehicle ID: {self.__vehicle_id}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__client.close()
        logger.info("Disconnected from InfluxDB")

    def store_data(self, data):
        write_api = self.__client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=self.__bucket, record=data)

    def get_data(self, query):
        query_api = self.__client.query_api()
        result = query_api.query(query=query)
        return result
