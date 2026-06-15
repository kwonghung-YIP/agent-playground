import logging
import threading
import asyncio
from contextlib import asynccontextmanager
from functools import partial

import pika
from pika.channel import Channel
from pika.spec import Basic, BasicProperties, Exchange, Queue
from pika.exchange_type import ExchangeType
from pika.adapters.asyncio_connection import AsyncioConnection

from agent.common import AgentRequest, AgentResponse
from agent.google import AsyncAgent

logger = logging.getLogger(__name__)

class PikaAsyncGateway(threading.Thread):

    def __init__(self, host:str, handler:asyncio.coroutines):
        super().__init__()
        self._termSignal = threading.Event()

        self._rabbitHost = host
        self._username = "admin"
        self._passwd = "passwd"

        self._connection:AsyncioConnection = None
        self._channel:Channel = None
        self._consumer_tag: str = None

        self._requestQueue:ExchangeAndQueue = None
        self._responseQueue:ExchangeAndQueue = None

        self._taskCount:int = 0
        self._llmAsyncCall = handler
        
    def run(self) -> None:
        """
        The runnable function for this Thread, and it switch to async here,
        a new eventloop initial under this thread when call asyncio below.
        """
        try:
            logger.info("Call asyncio.run() to start accepting agent request...")
            asyncio.run(self.acceptRequest())
        finally:
            logger.info("asyncio.run()... completed.")

    def stop(self) -> None:
        """ 
        Allow the parent thread to stop this thread, set the self._termSignal to 
        trigger the stop process
        """
        logger.info("set termSignal")
        self._termSignal.set()

    async def acceptRequest(self) -> None:
        """
        The self.run call this async coroutine, it
        - open the rabbit SelectionConnection, Channel
        - start a new asyncio.TaskGroup and wait until all tasks completed
        - start a backgroud task to keep this thread running
        - for any incoming message, it will handled by a new task under the taskgroup
        """
        async with self.openConnection() as conn, self.openChannel() as channel:
            self._requestQueue = ExchangeAndQueue(channel,"agent-request")
            await self._requestQueue.declare()

            self._responseQueue = ExchangeAndQueue(channel,"agent-response")
            await self._responseQueue.declare()            

            logger.info("Start the asyncio.TaskGroup...")
            async with asyncio.TaskGroup() as tg:
                bgTask = tg.create_task(self.backgroundTask(),name="backgroundTask")
                self._consumer_tag = channel.basic_consume(
                    queue=self._requestQueue._queueName,
                    on_message_callback=partial(self.on_channel_message,taskgroup=tg),
                    callback=self.on_channel_basic_consume_ok
                )
            logger.info("asyncio.TaskGroup completed.")

            cancelOKEvent = asyncio.Event()
            logger.info("Cancelling consumer subscription consumer_tag: %s", self._consumer_tag)
            self._channel.basic_cancel(
                consumer_tag=self._consumer_tag,
                callback=partial(self.on_channel_basic_cancel_ok, event=cancelOKEvent)
            )
            await cancelOKEvent.wait()

    async def backgroundTask(self, interval:float=1) -> None:
        """
        This background task keep running until any external party call the self.stop()
        function to set the self._termSignal, without this background thread, the taskgroup
        will end immediately and will not wait for incoming message.
        """
        logger.info("Starting the background task...")
        while not self._termSignal.is_set():
            logger.debug("The self._termSignal has not activated sleep for %d sec...", interval)
            await asyncio.sleep(interval)

    @asynccontextmanager
    async def openConnection(self):
        """
        Implement an async context manager to encapsulate the connection
        for the async with statement
        """
        try:
            logger.info("Openning connection...")
            credential = pika.PlainCredentials(self._username, self._passwd)
            parameters = pika.ConnectionParameters(host=self._rabbitHost, credentials=credential)
            
            connOpenedEvent = asyncio.Event()
            connClosedEvent = asyncio.Event()
            connection = AsyncioConnection(
                parameters=parameters,
                on_open_callback=partial(self.on_connection_open, event=connOpenedEvent),
                on_close_callback=partial(self.on_connection_close, event=connClosedEvent),
                on_open_error_callback=self.on_connetion_open_error
            )
            await connOpenedEvent.wait()
            yield self._connection
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("close connection...")
            self._connection.close()
            await connClosedEvent.wait()

    def on_connection_open(self, conn:AsyncioConnection, event:asyncio.Event) -> None:
        """
        callback function when rabbitmq connection is established
        """
        logger.info("Connection opened.")
        self._connection = conn
        event.set()

    def on_connection_close(self, conn:AsyncioConnection, reason:BaseException, event:asyncio.Event) -> None:
        """
        callback function when rabbitmq connection is closed
        """
        logger.info("Connection closed.")
        self._connection = None
        event.set()

    def on_connetion_open_error(self, conn:AsyncioConnection, error:BaseException) -> None:
        pass

    @asynccontextmanager
    async def openChannel(self):
        try:
            logger.info("open channel...")
            channelOpenedEvent = asyncio.Event()
            channelClosedEvent = asyncio.Event()
            channel = self._connection.channel(
                on_open_callback=partial(self.on_channel_open, 
                    openedEvent=channelOpenedEvent, closedEvent=channelClosedEvent)
            )
            await channelOpenedEvent.wait()
            yield self._channel
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("close channel")
            self._channel.close()
            await channelClosedEvent.wait()

    def on_channel_open(self, channel:Channel, 
        openedEvent:asyncio.Event, closedEvent:asyncio.Event) -> None:
        logger.info("channel opened.")
        self._channel = channel
        self._channel.add_on_close_callback(partial(self.on_channel_close, event=closedEvent))
        openedEvent.set()

    def on_channel_close(self, channel:Channel, reason:Exception, event:asyncio.Event):
        logger.info("channel closed.")
        self._channel = None
        event.set()

    def on_channel_message(self, channel:Channel, method:Basic.Deliver, props:BasicProperties, 
                           raw:bytes, taskgroup:asyncio.TaskGroup) -> None:
        logger.info("Received message: %s", raw)
        logger.info("reply_to: %s", props.reply_to)
        logger.info("correlation_id: %s", props.correlation_id)
        logger.info("message_id: %s", props.message_id)
        logger.info("content_type: %s", props.content_type)
        for (key,value) in props.headers.items():
            logger.info("header %s:%s", key, value)

        request = AgentRequest.model_validate_json(raw)

        self._taskCount += 1
        task = taskgroup.create_task(
            self._llmAsyncCall(request), 
            name=f"handlerTask_{self._taskCount}"
        )
        task.add_done_callback(partial(self.handler_task_done_callback, props=props))

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def handler_task_done_callback(self, task:asyncio.Task, props:BasicProperties) -> None:
        logger.info("task %s done", task.get_name())

        response:AgentResponse = task.result()

        logger.info("task done, publishing result type:%s, value:%s", type(response), response)
        self._channel.basic_publish(
            exchange=self._responseQueue._exchangeName, 
            routing_key=self._responseQueue._routingKey,
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=props.correlation_id,
            ),
            body=response.model_dump_json()
        )

    def on_channel_basic_consume_ok(self, consumeOK:Basic.ConsumeOk) -> None:
        logger.info("channel basic ConsumeOK")

    def on_channel_basic_cancel_ok(self, cancelOk:Basic.CancelOk, event:asyncio.Event) -> None:
        logger.info("channel BasicCancelOK")
        event.set()

class ExchangeAndQueue:

    def __init__(self, channel:Channel, exchangeName:str, queueName:str=None, routingKey:str=None) -> None:
        self._channel = channel
        self._exchangeName = exchangeName
        self._exchange_type = ExchangeType.topic
        self._queueName = queueName if queueName is not None else exchangeName
        self._routingKey = routingKey if routingKey is not None else exchangeName
        self._isReadyEvent = asyncio.Event()

    async def declare(self) -> None:
        logger.info("declaring exchange %s", self._exchangeName)
        self._channel.exchange_declare(
            exchange=self._exchangeName,
            exchange_type=self._exchange_type,
            callback=self.on_exchange_declare
        )
        await self._isReadyEvent.wait()

    def on_exchange_declare(self, declare_ok:Exchange.DeclareOk) -> None:
        logger.info("Exchange %s declared, declaring queue %s...", self._exchangeName, self._queueName)
        self._channel.queue_declare(
            queue=self._queueName,
            durable=True,
            callback=self.on_queue_declare
        )

    def on_queue_declare(self, declare_ok:Queue.DeclareOk) -> None:
        logger.info("Queue %s declared, binding it to exchange...", self._queueName)
        self._channel.queue_bind(
            exchange=self._exchangeName,
            queue=self._queueName,
            routing_key=self._routingKey,
            callback=self.on_queue_bind
        )

    def on_queue_bind(self, bind_ok:Queue.BindOk) -> None:
        logger.info("Queue %s bind to Exchange %s", self._queueName, self._exchangeName)
        self._isReadyEvent.set()