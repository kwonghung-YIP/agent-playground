import os
import logging
import logging.config
import dotenv
import yaml

import threading
import signal

import pika
from pika.adapters.blocking_connection import BlockingConnection, BlockingChannel 
from pika.spec import Basic, BasicProperties
from pika.exceptions import StreamLostError

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

termSignal = threading.Event()
connection:BlockingConnection
channel:BlockingChannel

def on_message(channel:BlockingChannel,method: Basic.Deliver,
               props: BasicProperties, body:bytes):
    logger.info(f"Receive message {body.decode()}")
    channel.basic_ack(delivery_tag=method.delivery_tag)

def consume_channel(termSignal:threading.Event):
    logger.info("start comsuing channel...")

    global connection, channel

    credential = pika.PlainCredentials("admin","passwd")
    parameters = pika.ConnectionParameters(credentials=credential)

    logger.info("Opening Pika BlockingConnection...")
    connection = pika.BlockingConnection(parameters=parameters)
    logger.info("Opening Pika BlockingChannel...")
    channel = connection.channel()
    try:
        consumerTag = channel.basic_consume(
            queue='test', on_message_callback=on_message)
        logger.info(f"obtain consumerTag:{consumerTag}, before start_consuming()...")

        channel.start_consuming()

    except Exception as e:
        logger.error(f"{type(e)} while consuming channel:{e}")
    finally:
        logger.info(f"stop consuming channel")

        if channel.is_open:
            channel.close()
            logger.info("Closed Pika BlockingChannel")
        if connection.is_open:
            connection.close()
            logger.info("Closed Pika BlocingConnection")

def handle_signal(signum,frame):
    global stopMain
    logger.info(f"received signal {signal.Signals(signum).name}({signum})")
    match signum:
        case signal.SIGTERM:
            termSignal.set()
            connection.add_callback_threadsafe(channel.start_consuming)

def joinThreadPool(pool:list[threading.Thread], termSignal:threading.Event):
    alive = len(pool)
    while alive > 0:
        try:
            if termSignal.is_set():
                alive = 0
                for thread in pool:
                    if thread.is_alive():
                        alive += 1
                        logger.info(f"waiting for thread {thread.name}")
                        thread.join(1)
            else:
                termSignal.wait(5)
        except KeyboardInterrupt:
            termSignal.set()
            connection.add_callback_threadsafe(channel.start_consuming)

def main():
    logger.info("main...")
    try:
        signal.signal(signal.SIGTERM, handle_signal)
        threadPool:list[threading.Thread] = []

        queueListener = threading.Thread(name="rabbitmq_listener",
                                         target=consume_channel,kwargs={"termSignal":termSignal})
        threadPool.append(queueListener)

        for thread in threadPool:
            thread.start()

        joinThreadPool(threadPool,termSignal)

    finally:
        logger.info("end main.")

if __name__ == "__main__":
    main()