from loguru import logger

from utils import LLM


def main():
    with LLM() as llm:
        response = llm.query("what causing the check engine light?", hours=24)
        logger.info(response)


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
