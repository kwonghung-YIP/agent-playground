import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

import time
import functools
import asyncio
import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties

class AsyncConsumer():

    def __init__(self, eventloop: asyncio.AbstractEventLoop):
        self._eventloop: asyncio.AbstractEventLoop = eventloop
        self._connection: AsyncioConnection = None
        self._channel: Channel = None
        self._consumerTag: str = None

        self._username = "admin"
        self._passwd = "passwd"
        self._reqQueue = "request"
        self._respExchange = "response"

    def connect(self) -> AsyncioConnection:
        credential = pika.PlainCredentials(self._username, self._passwd)
        parameters = pika.ConnectionParameters(credentials=credential)
        conn = AsyncioConnection(
            parameters=parameters,
            on_open_callback=self.on_conn_open,
            on_close_callback=self.on_conn_close,
            custom_ioloop=self._eventloop
        )
        return conn

    def on_conn_open(self, conn:AsyncioConnection) -> None:
        logger.info("Connection opened...")
        channel = conn.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel:Channel):
        logger.info("Channel opened...")
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_close)
        #self._channel.add_on_cancel_callback(self.on_channel_cancel)
        self._consumerTag = self._channel.basic_consume(
            queue=self._reqQueue,
            on_message_callback=self.on_message
        )
        logger.info(f"consumerTag is {self._consumerTag}")

    async def longRunningTask(self, sleep) -> None:
        logger.info(f"sleep for {sleep} second(s)")
        await asyncio.sleep(sleep)

    def on_message(self, channel:Channel, method: Basic.Deliver, props: BasicProperties, body:bytes):
        logger.info(f"Receive message {body.decode()}")

        #asyncio.get_running_loop().

        self._channel.basic_publish(
            exchange="", routing_key=self._respExchange,
            body=f"Received message:{body.decode()}"
        )

        self._channel.basic_ack(delivery_tag=method.delivery_tag)

    def on_channel_basic_cancel_ok(self, method_frame:pika.frame.Method):
        logger.info("Channel Basic.Cancel OK...")
        self._channel.close()

    #def on_channel_cancel(self, method_frame:pika.frame.Method):
    #    logger.info("Channel cancelled...")
    #    self._channel.close()  

    def on_channel_close(self, channel:Channel, reason:Exception):
        logger.info("Channel closed...")
        self._connection.close()        

    def on_conn_close(self, conn:AsyncioConnection, reason:Exception) -> None:
        logger.info("Connection closed...")
        logger.info("Stop eventloop...")
        self._connection.ioloop.stop()
        self._connection = None

    def start(self) -> None:
        logger.info("start...")
        self._connection = self.connect()
        self._connection.ioloop.run_forever()

    def stop(self) -> None:
        logger.info("call Basic.Cancel to stop...")
        self._channel.basic_cancel(consumer_tag=self._consumerTag,
            callback=self.on_channel_basic_cancel_ok)
        # keep running the eventloop to capture the closing event
        self._connection.ioloop.run_forever()        

def main():
    eventloop = asyncio.new_event_loop()
    consumer = AsyncConsumer(eventloop)
    
    try:
        consumer.start()
    except KeyboardInterrupt:
        consumer.stop()
        eventloop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()