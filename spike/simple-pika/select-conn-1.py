import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

import time

def main() -> None:
    logger.info("main....")
    try:
        for i in range(1,100):
            time.sleep(1)
            logger.info(f"sleep {i}")
    except KeyboardInterrupt:
        logger.info("interrupted...")
    finally:
        logger.info("done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()