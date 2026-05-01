import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)
      

import threading
import asyncio
import signal
import functools

class AsyncPikaConsumer(threading.Thread):

    def __init__(self):
        super().__init__()
        self._termSignal = threading.Event()

    def run(self) -> None:
        try:
            logger.info("start asyncio.run...")
            asyncio.run(self.consumeMessage())
        finally:
            logger.info("asyncio.run completed.")

    def stop(self):
        logger.info("set termSignal...")
        self._termSignal.set()

    async def consumeMessage(self) -> None:
        logger.info("start taskGroup...")
        async with asyncio.TaskGroup() as tg:
            task = tg.create_task(self.backgroundTask(),name="backgroundTask")
        logger.info("taskGroup stopped.")

    async def backgroundTask(self) -> None:
        while not self._termSignal.is_set():
            logger.info("background thread sleep for 1 second...")
            await asyncio.sleep(1)

def handle_signal(signum, frame, consumer):
    logger.info(f"received signal {signal.Signals(signum).name}({signum})")
    consumer.stop()

def main():
    try:
        consumer = AsyncPikaConsumer()
        signal.signal(signal.SIGTERM, functools.partial(handle_signal,consumer=consumer))
        consumer.start()
        # keep the MainThread running...
        while consumer.is_alive():
            consumer.join(5)
    except KeyboardInterrupt:
        consumer.stop()
    finally:
        while consumer.is_alive():
            logger.info("join consumer thread still alive...")
            consumer.join(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()