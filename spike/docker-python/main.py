import signal
import threading
import random
import logging
import logging.config
import yaml
import os
import sys
import dotenv

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

def worker(event:threading.Event):
    logger.info(f"worker started...")
    try:
        local = threading.local()
        local.count = 0
        while not event.is_set() and local.count<100:
            local.count += 1
            logger.info(f"count:{local.count}")
            event.wait(random.randrange(1,20))
    except Exception as e:
        logger.error(f"Exception in worker...")
    finally:
        logger.info(f"worker end.")


event = threading.Event()

def handle_signal(signum,frame):
    global stopMain
    logger.info(f"received signal {signal.Signals(signum).name}({signum})")
    match signum:
        case signal.SIGTERM:
            event.set()

def main():
    signal.signal(signal.SIGTERM, handle_signal)
    logger.info(f"Start main...")
    try:
        threadpool: list[threading.Thread] = []
        for i in range(3):
            thread = threading.Thread(name=f"worker-thread-{i+1}",target=worker,kwargs={"event":event})
            threadpool.append(thread)

        for thread in threadpool:
            thread.start()

        #time.sleep(30)
        #event.set()

        aliveThread = len(threadpool)
        while aliveThread > 0:
            try:
                if event.is_set():
                    aliveThread = 0
                    for thread in threadpool:
                        if thread.is_alive():
                            aliveThread += 1
                            logger.info(f"waiting for thread {thread.name}")
                            thread.join(1)
                else:
                    event.wait(5)
            except KeyboardInterrupt:
                event.set()

    finally:
        logger.info(f"exit main.")

if __name__ == "__main__":
    main()