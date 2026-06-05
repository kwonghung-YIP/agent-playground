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

import threading
import signal
import time

from contextlib import contextmanager

from typing import Iterator, Tuple, Generator
import pika
from pika.adapters.blocking_connection import BlockingConnection, BlockingChannel 
from pika.spec import Basic, BasicProperties

import asyncio

ConsumeMessage = Tuple[Basic.Deliver|None, BasicProperties|None, bytes|None]

async def long_running_task(sleep:float) -> None:
    logger.info(f"sleep for {sleep} seconds...")
    await asyncio.sleep(sleep)
    logger.info(f"wake up after {sleep} seconds...")

class PikaBlockConsumer(threading.Thread):

    _termSignal: threading.Event

    def __init__(self, termSignal:threading.Event) -> None:
        super().__init__()
        self.name = "PikaBlockConsumer"
        self._termSignal = termSignal

    @contextmanager
    def openChannel(self, params:pika.ConnectionParameters) -> Generator[BlockingConnection,BlockingChannel]:
        logger.info("Opening Pika BlockingConnection...")
        connection = pika.BlockingConnection(parameters=params)
        
        logger.info("Opening Pika BlockingChannel...")
        channel = connection.channel()
    
        resource = (connection, channel)
        try:
            yield resource
        except:
            pass
        finally:
            if channel.is_open:
                channel.close()
                logger.info("Closed Pika BlockingChannel")
            if connection.is_open:
                connection.close()
                logger.info("Closed Pika BlocingConnection")

    def run(self) -> None:
        logger.info(f"start run...")

        try:
            credential = pika.PlainCredentials("admin","passwd")
            parameters = pika.ConnectionParameters(credentials=credential)

            with self.openChannel(parameters) as (connection, channel):

                messages: Iterator[ConsumeMessage] = channel.consume(queue="request",inactivity_timeout=5)

                for method, props, body in messages:
                    if method is None:
                        logger.info(f"inactivity_timeout")
                    else:
                        logger.info(f"Received message {type(body)} {body.decode()}")
                        channel.basic_ack(method.delivery_tag)

                        asyncio.run(long_running_task(30))

                        #logger.info(f"Publish response message")
                        #channel.basic_publish(exchange="", routing_key="response", 
                        #    body=f"I received your message \"{body}\"")
                    
                    if self._termSignal.is_set():
                        logger.info("termSignal is set and stop loop..")
                        break
                    else:
                        logger.info("termSignal is not set and continue the loop...")

                channel.cancel()
        finally:
            logger.info(f"exit run...")

termSignal = threading.Event()

def main():
    logger.info("main...")
    try:
        pikaThread = PikaBlockConsumer(termSignal)
        pikaThread.start()

        while pikaThread.is_alive():
            try:
                logger.info(f"waiting for thread:{pikaThread.name}")
                pikaThread.join(5)
            except KeyboardInterrupt:
                logger.info("intrrupted, set termSignal...")
                termSignal.set()

    finally:
        logger.info("end main.")

if __name__ == "__main__":
    main()

