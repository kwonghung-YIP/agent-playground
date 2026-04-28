import os
import logging
import logging.config
import dotenv
import yaml

def load_logging_config():
    config_file = os.getenv("LOG_CONFIG_FILE","logging-config.yaml")
    if os.path.exists(config_file):
        with open(config_file, 'rt') as yaml_file:
            try:
                config = yaml.safe_load(yaml_file.read())
                logging.config.dictConfig(config)
            except Exception as e:
                print(f"Exception when loading the config file {yaml_file}: {e}")
    else:
        print(f"Cannot find the logging config file:{config_file}")
        
    # back to basic config in case cannot load the config file
    default_level = logging.INFO
    logging.basicConfig(level=default_level)

dotenv.load_dotenv()
load_logging_config()
logger = logging.getLogger(__name__)

import time
import functools
import asyncio
import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties
from pika.exchange_type import ExchangeType

class AsyncConsumer():

    def __init__(self, eventloop: asyncio.AbstractEventLoop):
        self._eventloop: asyncio.AbstractEventLoop = eventloop
        self._connection: AsyncioConnection = None
        self._channel: Channel = None
        self._consumerTag: str = None


    def connect(self) -> AsyncioConnection:
        credential = pika.PlainCredentials("admin","passwd")
        parameters = pika.ConnectionParameters(credentials=credential)
        conn = AsyncioConnection(
            parameters=parameters,
            on_open_callback=self.on_conn_open,
            on_open_error_callback=self.on_conn_open_error,
            on_close_callback=self.on_conn_close,
            custom_ioloop=self._eventloop
        )
        return conn

    def on_conn_open(self, conn:AsyncioConnection) -> None:
        logger.info("Connection opened...")
        self._channel = self.open_channel()

    def on_conn_open_error(self, conn:AsyncioConnection, err:Exception) -> None:
        logger.error("Cannot open the connection with error...")

    def on_conn_close(self, conn:AsyncioConnection, reason:Exception) -> None:
        logger.info("Connection closed...")

    def open_channel(self) -> Channel:
        logger.info("Open channel...")
        channel = self._connection.channel(on_open_callback=self.on_channel_open)
        return channel

    def on_channel_open(self, channel:Channel):
        logger.info("Channel opened...")
        self._channel.add_on_cancel_callback(self.on_channel_cancel)
        self._channel.add_on_close_callback(self.on_channel_close)

        self._consumerTag = self.start_consuming_channel("test")

    def on_channel_cancel(self, method_frame:pika.frame.Method):
        logger.info("Channel cancelled...")
        self._channel.close()

    def on_channel_close(self, channel:Channel, reason:Exception):
        logger.info("Channel closed...")
        self._connection.close()

    def start_consuming_channel(self, queue:str) -> str:
        logger.info("Start consuming channel...")
        consumerTag = self._channel.basic_consume(
            queue=queue,
            on_message_callback=self.on_message
        )
        return consumerTag

    def on_message(self, channel:Channel, method: Basic.Deliver, props: BasicProperties, body:bytes):
        logger.info(f"Receive message {body.decode()}")
        self._channel.basic_ack(delivery_tag=method.delivery_tag)

    def stop_consuming_channel(self):
        logger.info("Stop consuming channel...")
        cb = functools.partial(self.on_channel_cancel_ok, userdata=self._consumerTag)
        self._channel.basic_cancel(self._consumerTag, cb)

    def on_channel_cancel_ok(self, method_frame:pika.frame.Method, userdata):
        logger.info("Channel Basic.Cancel OK...")
        logger.info("Closing channel...")
        self._channel.close()


    def run(self):
        logger.info("AsyncConsumer run...")
        self._connection = self.connect()
        self._connection.ioloop.run_forever()

    def stop(self):
        logger.info("AsyncConsumer stop...")
        self._connection.ioloop.stop()
        

def main():
    eventloop = asyncio.new_event_loop()
    consumer = AsyncConsumer(eventloop)
    
    try:
        consumer.run()
    except KeyboardInterrupt:
        consumer.stop_consuming_channel()
        time.sleep(5)
        #consumer.stop()
        #eventloop.close()

if __name__ == "__main__":
    main()