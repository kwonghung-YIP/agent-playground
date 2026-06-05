import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

import time

def dummy() -> None:
    try:
        for i in range(1,100):
            time.sleep(1)
            logger.info(f"sleep {i}")
    except KeyboardInterrupt:
        logger.info("interrupted...")
    finally:
        logger.info("done")

from threading import Thread, Event
import asyncio
import signal
from contextlib import asynccontextmanager
from functools import partial

import pika
from pika.channel import Channel
from pika.spec import Basic, BasicProperties
from pika.adapters.select_connection import SelectConnection

class PikaAsyncConnector(Thread):

    def __init__(self, handler:asyncio.coroutines):
        super().__init__()
        self._termSignal = Event()

        self._rabbitHost = "localhost"
        self._username = "admin"
        self._passwd = "passwd"

        self._connection:SelectConnection = None
        self._channel:Channel = None

    def run(self) -> None:
        """
        The runnable function for this Thread, and it switch to async here,
        a new eventloop initial under this thread when call asyncio below.
        """
        try:
            logger.info("Call asyncio.run() to start consume message...")
            asyncio.run(self.consumeMessage())
        finally:
            logger.info("asyncio.run()... completed.")

    def stop(self) -> None:
        """ 
        Allow the parent thread to stop this thread, set the self._termSignal to 
        trigger the stop process
        """
        logger.info("set termSignal")
        self._termSignal.set()

    async def consumeMessage(self) -> None:
        """
        The self.run call this async coroutine, it
        - open the rabbit SelectionConnection, Channel
        - start a new asyncio.TaskGroup and wait until all tasks completed
        - start a backgroud task to keep this thread running
        - for any incoming message, it will handled by a new task under the taskgroup
        """
        async with self.openConnection() as connection:
            logger.info("Start the asyncio.TaskGroup...")
            async with asyncio.TaskGroup() as tg:
                bgTask = tg.create_task(self.backgroundTask(),name="backgroundTask")
            logger.info("asyncio.TaskGroup completed.")

    async def backgroundTask(self, interval:float=1) -> None:
        """
        This background task keep running under any external party call the self.stop()
        function to set the self._termSignal, without this background thread, the taskgroup
        will end immediately and will not wait for incoming message.
        """
        logger.info("Starting the background task...")
        while not self._termSignal.is_set():
            logger.debug("The self._termSignal has not activated sleep for {interval} sec...")
            await asyncio.sleep(interval)

    @asynccontextmanager
    async def openConnection(self):
        """
        Implement an async context manager to encapsulate the connection
        with the async with statement
        """
        try:
            logger.info("Openning connection...")
            credential = pika.PlainCredentials(self._username, self._passwd)
            parameters = pika.ConnectionParameters(host=self._rabbitHost, credentials=credential)
            self._connection = SelectConnection(
                parameters=parameters,
                on_open_callback=self.on_connection_open,
                on_close_callback=self.on_connection_close,
                on_open_error_callback=self.on_connetion_open_error
            )
            await self.waitConnIsOpened()
            yield self._connection
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("close connection...")
            self._connection.close()
            await self.waitConnIsClosed()

    def on_connection_open(self, connection:SelectConnection) -> None:
        """
        callback function when rabbitmq connection is established
        """
        logger.info("Connection opened.")
        self._connection = connection

    def on_connection_close(self, connection:SelectConnection, reason:Exception) -> None:
        """
        callback function when rabbitmq connection is closed
        """
        logger.info("Connection closed.")
        self._connection = None

    def on_connetion_open_error(self, connection:SelectConnection, error:Exception) -> None:
        pass
            
    def connectionIsOpened(self) -> bool:
        return self._connection is not None and self._connection.is_open
    
    async def waitConnIsOpened(self, delay:float=1) -> None:
        while not self.connectionIsOpened():
            logger.info("here")
            await asyncio.sleep(delay)

    def connectionIsClosed(self) -> bool:
        return self._connection is None or self._connection.is_closed

    async def waitConnIsClosed(self, delay:float=1) -> None:
        while not self.connectionIsClosed():
            await asyncio.sleep(delay)

def handle_signal(signum, frame, threadPool:list[Thread]) -> None:
    logger.info(f"received signal {signal.Signals(signum).name}({signum})")
    for thread in threadPool:
        thread.stop()

def joinThreads(threadPool:list[Thread],timeout:float) -> None:
    activeThread = len(threadPool)
    while activeThread > 0:
        activeThread = 0
        for thread in threadPool:
            if thread.is_alive():
                logger.debug(f"Thread {thread.name} still active, waiting for {timeout} sec...")
                activeThread += 1
                thread.join(timeout)
    logger.info("All threads stopped.")

import random

async def callLLMModel(request:str) -> str:
    """
    dummy async function to simulate calling LLM model
    """
    await asyncio.sleep(random.randrange(4,10))

def main() -> None:
    """
    Keep the main thread running until all child thread completed.
    """
    logger.info("Start main....")
    try:
        messageThread = PikaAsyncConnector(handler=callLLMModel)
        signal.signal(signal.SIGTERM, partial(handle_signal, threadPool=[messageThread]))
        
        messageThread.start()
        joinThreads([messageThread],5)
    except KeyboardInterrupt:
        logger.info("main() interrupted by keyboard...")
        messageThread.stop()
    finally:
        joinThreads([messageThread],1)
    


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()