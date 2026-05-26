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
from pika.spec import Basic, BasicProperties, Exchange, Queue
from pika.exchange_type import ExchangeType
from pika.adapters.asyncio_connection import AsyncioConnection

class PikaAsyncConnector(Thread):

    def __init__(self, host:str, handler:asyncio.coroutines):
        super().__init__()
        self._termSignal = Event()

        self._rabbitHost = host
        self._username = "admin"
        self._passwd = "passwd"

        self._connection:AsyncioConnection = None
        self._channel:Channel = None
        self._consumer_tag: str = None

        self._requestQueue:DirectQueue = None
        self._responseQueue:DirectQueue = None

        self._taskCount:int = 0
        self._handler = handler

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
        async with self.openConnection() as conn, self.openChannel() as channel:
            self._requestQueue = DirectQueue(channel,"AgentRequest")
            await self._requestQueue.prepare()

            self._responseQueue = DirectQueue(channel,"AgentResponse")
            await self._responseQueue.prepare()            

            logger.info("Start the asyncio.TaskGroup...")
            async with asyncio.TaskGroup() as tg:
                bgTask = tg.create_task(self.backgroundTask(),name="backgroundTask")
                self._consumer_tag = channel.basic_consume(
                    queue=self._requestQueue._queue,
                    on_message_callback=partial(self.on_channel_message,taskgroup=tg),
                    callback=self.on_channel_basic_consume_ok
                )
            logger.info("asyncio.TaskGroup completed.")

            cancelOKEvent = asyncio.Event()
            logger.info(f"Cancelling conumer subscription consumer_tag:{self._consumer_tag}")
            self._channel.basic_cancel(
                consumer_tag=self._consumer_tag,
                callback=partial(self.on_channel_basic_cancel_ok, event=cancelOKEvent)
            )
            await cancelOKEvent.wait()

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
            connection = AsyncioConnection(
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

    def on_connection_open(self, conn:AsyncioConnection) -> None:
        """
        callback function when rabbitmq connection is established
        """
        logger.info("Connection opened.")
        self._connection = conn

    def on_connection_close(self, conn:AsyncioConnection, reason:BaseException) -> None:
        """
        callback function when rabbitmq connection is closed
        """
        logger.info("Connection closed.")
        self._connection = None

    def on_connetion_open_error(self, conn:AsyncioConnection, error:BaseException) -> None:
        pass

    def connectionIsOpened(self) -> bool:
        return self._connection is not None and self._connection.is_open
    
    async def waitConnIsOpened(self, delay:float=1) -> None:
        while not self.connectionIsOpened():
            await asyncio.sleep(delay)

    def connectionIsClosed(self) -> bool:
        return self._connection is None or self._connection.is_closed

    async def waitConnIsClosed(self, delay:float=1) -> None:
        while not self.connectionIsClosed():
            await asyncio.sleep(delay)

    @asynccontextmanager
    async def openChannel(self):
        try:
            logger.info("open channel...")
            channel = self._connection.channel(
                on_open_callback=self.on_channel_open
            )
            await self.waitChannelIsOpened()
            yield self._channel
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("close channel")
            self._channel.close()
            await self.waitChannelIsClosed()

    def on_channel_open(self, channel:Channel) -> None:
        logger.info("channel opened.")
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_close)

    def on_channel_close(self, channel:Channel, reason:Exception):
        logger.info("channel closed.")
        self._channel = None

    def channelIsOpened(self) -> bool:
        return self._channel is not None and self._channel.is_open
    
    async def waitChannelIsOpened(self, delay:float=1) -> None:
        while not self.channelIsOpened():
            await asyncio.sleep(delay)

    def channelIsClosed(self) -> bool:
        return self._channel is None or self._channel.is_closed

    async def waitChannelIsClosed(self, delay:float=1) -> None:
        while not self.channelIsClosed():
            await asyncio.sleep(delay)
        
    def on_channel_message(self, channel:Channel, method:Basic.Deliver, props:BasicProperties, 
                           raw:bytes, taskgroup:asyncio.TaskGroup) -> None:
        logger.info(f"Received message:{raw}")
        logger.info(f"reply_to:{props.reply_to}")
        logger.info(f"correlation_id:{props.correlation_id}")
        logger.info(f"message_id:{props.message_id}")
        logger.info(f"content_type:{props.content_type}")
        for (key,value) in props.headers.items():
            logger.info(f"header {key}:{value}")

        request = AgentRequest.model_validate_json(raw)

        self._taskCount += 1
        task = taskgroup.create_task(
            self._handler(request), 
            name=f"handlerTask_{self._taskCount}"
        )
        task.add_done_callback(partial(self.handler_task_done_callback,props=props))

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def handler_task_done_callback(self, task:asyncio.Task, props:BasicProperties) -> None:
        logger.info(f"task {task.get_name()} done")

        response:AgentResponse = task.result()

        logger.info(f"task done, publishing result type:{type(response)}, value:{response}")
        self._channel.basic_publish(
            exchange="", routing_key=props.reply_to,
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=props.correlation_id,
                headers={
                    "__TypeId__": props.headers.get('reply_to_typeId')
                }
            ),
            body=response.model_dump_json()
        )


    def on_channel_basic_consume_ok(self, consumeOK:Basic.ConsumeOk) -> None:
        logger.info(f"channel basic ConsumeOK")

    def on_channel_basic_cancel_ok(self, cancelOk:Basic.CancelOk, event:asyncio.Event) -> None:
        logger.info(f"channel BasicCancelOK")
        event.set()

class DirectQueue:

    def __init__(self, channel:Channel, exchange:str, queue:str=None, routingKey:str=None) -> None:
        self._channel = channel
        self._exchange = exchange
        self._exchange_type = ExchangeType.topic
        self._queue = queue if queue is not None else exchange
        self._routingKey = routingKey if routingKey is not None else exchange
        self._isReadyEvent = asyncio.Event()

    async def prepare(self) -> None:
        logger.info(f"declaring exchange {self._exchange}")
        self._channel.exchange_declare(
            exchange=self._exchange,
            exchange_type=self._exchange_type,
            callback=self.on_exchange_declare
        )
        await self._isReadyEvent.wait()

    def on_exchange_declare(self, declare_ok:Exchange.DeclareOk) -> None:
        logger.info(f"Exchange {self._exchange_type} declared, declaring queue {self._queue}...")
        self._channel.queue_declare(
            queue=self._queue,
            durable=True,
            callback=self.on_queue_declare
        )

    def on_queue_declare(self, declare_ok:Queue.DeclareOk) -> None:
        logger.info(f"Queue {self._queue} declared, binding to exchange...")
        self._channel.queue_bind(
            exchange=self._exchange,
            queue=self._queue,
            routing_key=self._routingKey,
            callback=self.on_queue_bind
        )

    def on_queue_bind(self, bind_ok:Queue.BindOk) -> None:
        logger.info(f"Queue {self._queue} bind to Exchange {self._exchange}")
        self._isReadyEvent.set()

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
from pydantic import BaseModel

class AgentRequest(BaseModel):
    agentId: str
    chatId: str
    userInput: str

class AgentResponse(BaseModel):
    agentId: str
    chatId: str
    modelReply: str

async def callLLMModel(request:AgentRequest) -> AgentResponse:
    """
    dummy async function to simulate calling LLM model
    """
    sleep = random.randrange(4,10)
    await asyncio.sleep(sleep)
    logger.info(f"call to LLM model completed after {sleep} second")

    if request.agentId == "story_teller":
        reply = f"Here is the story for {request.userInput}"
    elif request.agentId == "editor":
        reply = f"Here is my comment for story {request.userInput}"
    else:
        reply = f"response from model {request.userInput}"
        
    response = AgentResponse(
        agentId=request.agentId,
        chatId=request.chatId,
        modelReply=reply
    )
    return response

import os

def main() -> None:
    """
    Keep the main thread running until all child thread completed.
    """
    logger.info("Start main....")
    host = os.getenv("RABBITMQ_HOST","localhost")
    try:
        messageThread = PikaAsyncConnector(host=host, handler=callLLMModel)
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