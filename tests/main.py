import os
from time import sleep

import obd
from consolemenu import ConsoleMenu
from consolemenu.items import FunctionItem
from dotenv import load_dotenv
from loguru import logger
from obd import OBDStatus
from openai import OpenAI

load_dotenv()


OBD_DEVICE_PORT = os.getenv("OBD_DEVICE_PORT")


def _run_obd_command(conn, cmd):
    try:
        logger.debug(f"OBD :: CMD :: {cmd}")

        res = conn.query(cmd)
        return res.value
    except Exception as e:
        logger.error("OBD :: CMD ERROR :: {cmd} - {e}")


def _run_llm_query(query):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    completion = client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": query}],
    )
    return completion.choices[0].message.content


def menu_car_info(conn):
    res_speed = _run_obd_command(conn, obd.commands.SPEED)
    if res_speed:
        logger.info(f"OBD :: speed - {res_speed.to('kph')}")


def check_engine(conn):
    pass


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    conn = obd.OBD()
    if OBD_DEVICE_PORT:
        conn = obd.OBD(OBD_DEVICE_PORT)

    logger.info(f"OBD :: CONN :: {conn.status()}")

    while conn.status() == OBDStatus.NOT_CONNECTED:
        logger.debug("OBD :: CONN :: retrying...")
        sleep(1)
        logger.info(f"OBD :: CONN :: {conn.status()}")

    logger.info("OBD :: CONN :: device connected successfully")

    if conn.status() == OBDStatus.OBD_CONNECTED:
        logger.info("OBD :: CAR :: ignition off")

    if conn.status() == OBDStatus.CAR_CONNECTED:
        logger.info("OBD :: CAR :: ignition on")

    menu = ConsoleMenu("AI Mechanic")

    menu.append_item(FunctionItem("Get Car Info", menu_car_info, conn))
    menu.append_item(FunctionItem("Check Engine", check_engine, conn))

    menu.show()

# # no connection is made
# OBDStatus.NOT_CONNECTED # "Not Connected"

# # successful communication with the ELM327 adapter
# OBDStatus.ELM_CONNECTED # "ELM Connected"

# # successful communication with the ELM327 adapter,
# # OBD port connected to the car, ignition off
# # (not available with argument "check_voltage=False")
# OBDStatus.OBD_CONNECTED # "OBD Connected"

# # successful communication with the ELM327 and the
# # vehicle; ignition on
# OBDStatus.CAR_CONNECTED # "Car Connected"
