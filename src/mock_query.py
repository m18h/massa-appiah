import json
import os
from loguru import logger

# from utils import LLM
from utils import DB
from llama_index.core import VectorStoreIndex
from llama_index.core import Settings
from llama_index.core.schema import Document
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

SYSTEM_PROMPT = """
You are an expert automotive diagnostic assistant analyzing OBD-II (On-Board Diagnostics) data.

## Your Task
Analyze the provided vehicle telemetry data and provide a comprehensive diagnostic report.

## Data Fields You'll Receive
The data contains time-series readings with these parameters:
- **Engine metrics**: RPM, load, runtime
- **Temperature readings**: coolant_temp, oil_temp, intake_temp, ambient_temp (in Celsius)
- **Fuel system**: fuel_level (%), fuel_pressure (kPa), fuel_rate (L/h)
- **Air intake**: intake_pressure (kPa), barometric_pressure (kPa), throttle_position (%)
- **Electrical**: battery_voltage (V)
- **Vehicle motion**: speed (km/h), distance (km)

## Normal Operating Ranges
- Engine RPM: 600-900 idle, 1500-3000 driving
- Coolant temp: 85-105°C (warning if >105°C)
- Oil temp: 90-110°C (warning if >120°C)
- Battery voltage: 12.6-14.4V (warning if <12V or >15V)
- Fuel pressure: 250-350 kPa
- Throttle position: 0% idle, varies with acceleration

## Analysis Structure
Provide your analysis in the following format:

### 1. Overall Health Status
- Quick summary: Healthy / Needs Attention / Critical
- Key findings (2-3 bullet points)

### 2. Trend Analysis
- Identify patterns over the time period (e.g., temperature trends, fuel consumption patterns)
- Note any progressive degradation or improvements
- Compare early vs. recent readings

### 3. Anomaly Detection
- Flag any readings outside normal ranges
- Identify sudden spikes or drops in values
- Note unusual correlations (e.g., high temp with low coolant)
- Assess severity: Minor / Moderate / Severe

### 4. Maintenance Recommendations
- Immediate actions required (if any)
- Preventive maintenance suggestions
- Monitoring recommendations
- Estimated urgency timeline

### 5. Additional Observations
- Driving patterns or behaviors detected
- Fuel efficiency assessment
- Any other relevant insights

## Guidelines
- Be specific with numbers and timestamps when citing anomalies
- Prioritize safety-critical issues (brakes, engine, electrical)
- Use clear, non-technical language when possible
- If data is insufficient, state what additional information would help
- Avoid false alarms - only flag genuine concerns
"""

VEHICLE_ID = os.getenv("VEHICLE_ID", "vehicle_001")

Settings.llm = Ollama(
    model=os.getenv("LLM_API_MODEL", "llama3.2:latest"),
    base_url=os.getenv("LLM_API_BASE", "http://localhost:11434"),
    request_timeout=120.0,
    # Manually set the context window to limit memory usage
    context_window=8000,
)

Settings.embed_model = OllamaEmbedding(
    model_name=os.getenv("LLM_API_EMBEDDING_MODEL", "embeddinggemma"),
    base_url=os.getenv("LLM_API_BASE", "http://localhost:11434"),
    # Can optionally pass additional kwargs to ollama
    # ollama_additional_kwargs={"mirostat": 0},
)


def main():
    with DB() as db:
        obd_data = db.get_recent_data(hours=24, limit=1000)

    logger.info(f"Retrieved {len(obd_data)} records")

    docs = [Document(text=json.dumps(record, indent=2)) for record in obd_data]
    index = VectorStoreIndex.from_documents(docs)
    query_engine = index.as_query_engine()

    PROMPT = """
    You're an expert mechanic who's able to gain insights on a vehicle from the OBD metrics.
    What can you tell me about this vehicle?
    """
    response = query_engine.query(
        PROMPT,
    )
    logger.success(str(response))


if __name__ == "__main__":
    logger.info("Mock Query")
    logger.info("=" * 70)

    main()
