import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)
      

import threading
import asyncio
import signal
import functools
import contextlib
import os

import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties

import random

from pydantic import BaseModel

class AgentRequest(BaseModel):
    agentId: str
    chatId: str
    userInput: str

class AgentResponse(BaseModel):
    agentId: str
    chatId: str
    modelReply: str


class AsyncPikaConsumer(threading.Thread):

    def __init__(self, host:str, handler:asyncio.coroutines):
        super().__init__()
        self._termSignal = threading.Event()

        self._connection: AsyncioConnection = None
        self._channel: Channel = None
        self._consumerTag: str = None

        self._host = host
        self._username = "admin"
        self._passwd = "passwd"
        self._reqQueue = "request"
        self._respExchange = "response"

        self._handlerTaskCount = 0
        self._handler = handler

    def run(self) -> None:
        try:
            logger.info("start asyncio.run...")
            asyncio.run(self.consumeMessage())
        finally:
            logger.info("asyncio.run completed.")

    def stop(self):
        logger.info("set termSignal...")
        self._termSignal.set()

    @contextlib.asynccontextmanager
    async def openChannel(self):
        try:
            logger.info("opening connection...")

            credential = pika.PlainCredentials(self._username, self._passwd)
            parameters = pika.ConnectionParameters(host=self._host, credentials=credential)
            connection = AsyncioConnection(
                parameters=parameters,
                on_open_callback=self.on_conn_open,
                on_close_callback=self.on_conn_close
            )
            await self.waitUtilOpened()
            yield (self._connection, self._channel)
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("sending basic.Channel to conumerTag...")
            self._channel.basic_cancel(consumer_tag=self._consumerTag,
                callback=self.on_channel_basic_cancel_ok)            
            logger.info("closing connection...")
            await self.waitUntilClosed()

    async def waitUtilOpened(self):
        while not self.channelIsOpened():
            await asyncio.sleep(1)

    def channelIsOpened(self) -> bool:
        if self._connection is not None and self._connection.is_open:
            if self._channel is not None and self._channel.is_open:
                return True
        return False
    
    async def waitUntilClosed(self):
        while not self.channelIsClosed():
            await asyncio.sleep(1)

    def channelIsClosed(self) -> bool:
        if self._connection is None or self._connection.is_closed:
            if self._channel is None or self._channel.is_closed:
                return True
        return False

    # callback functions for Connection
    def on_conn_open(self, connection:AsyncioConnection) -> None:
        logger.info("Connection opened...")
        self._connection = connection
        channel = self._connection.channel(on_open_callback=self.on_channel_open)

    def on_conn_close(self, conn:AsyncioConnection, reason:Exception) -> None:
        logger.info(f"Connection closed:reason:{reason}")
        self._connection = None

    # callback functions for Channel
    def on_channel_open(self, channel:Channel):
        logger.info("Channel opened...")
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_close)

    def on_message(self, channel:Channel, method: Basic.Deliver, props: BasicProperties, body:bytes, taskGroup:asyncio.TaskGroup):
        logger.info(f"Receive message {body}")
        logger.info(f"reply_to:{props.reply_to}")
        logger.info(f"correlation_id:{props.correlation_id}")
        logger.info(f"message_id:{props.message_id}")
        logger.info(f"content_type:{props.content_type}")
        for (key,value) in props.headers.items():
            logger.info(f"header {key}:{value}")

        self._channel.basic_ack(delivery_tag=method.delivery_tag)

        self._handlerTaskCount += 1
        task = taskGroup.create_task(self._handler(body.decode()),name=f"handlerTask{self._handlerTaskCount}")
        task.add_done_callback(functools.partial(self.on_handler_done, props=props))

    def on_channel_basic_cancel_ok(self, method_frame:pika.frame.Method):
        logger.info("Channel Basic.Cancel OK...")
        self._channel.close()

    def on_channel_close(self, channel:Channel, reason:Exception):
        logger.info("Channel closed...")
        self._connection.close()        

    def on_handler_done(self, task:asyncio.Task, props: BasicProperties):
        result = task.result()
        logger.info(f"task done, publishing result to queue type:{type(result)}, value:{result}")
        self._channel.basic_publish(
            exchange="", routing_key=props.reply_to,
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=props.correlation_id
            ),
            body=result
        )

    async def consumeMessage(self) -> None:
        logger.info("start taskGroup...")
        async with self.openChannel() as (connection, channel):
            async with asyncio.TaskGroup() as tg:
                task = tg.create_task(self.backgroundTask(),name="backgroundTask")
                self._consumerTag = channel.basic_consume(
                    queue=self._reqQueue,
                    on_message_callback=functools.partial(self.on_message, taskGroup=tg)
                )
            logger.info("taskGroup stopped.")

    async def backgroundTask(self) -> None:
        while not self._termSignal.is_set():
            logger.debug("background thread sleep for 1 second...")
            await asyncio.sleep(1)

def handle_signal(signum, frame, consumer):
    logger.info(f"received signal {signal.Signals(signum).name}({signum})")
    consumer.stop()

async def makeGeminiCall(raw:bytes) -> str:
    request = AgentRequest.model_validate_json(raw)
    logger.info(f"recevied request: {request}")
    sleep = random.randrange(1,10) #(20,120)
    logger.info(f"gemini call will take {sleep} second(s)")
    await asyncio.sleep(sleep)

    reply = f"Response for [{request.userInput}] after {sleep} secords"
    response = AgentResponse(agentId=request.agentId, chatId=request.chatId, modelReply=reply)
    return response.model_dump_json()


def main():
    host = os.getenv("RABBITMQ_HOST","localhost")
    try:
        consumer = AsyncPikaConsumer(host,makeGeminiCall)
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