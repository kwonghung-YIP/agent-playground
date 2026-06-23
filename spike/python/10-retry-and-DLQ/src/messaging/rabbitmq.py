import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
import asyncio
from functools import partial
import threading
from typing import Any
import json

import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties, Exchange, Queue
from pika.exchange_type import ExchangeType

from llm.google_genai import AgentRequest, AgentResponse, BatchJob, GoogleLLM

logger = logging.getLogger(__name__)

@dataclass
class RabbitHostConfig:
    """
    dataclass for rabbitmq server configuration
    """
    host:str
    username:str
    password:str

    def getPikaConfig(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            credentials=credentials
        )
        return parameters

@dataclass
class QueueConfig:
    """
    configuration for declare and bind queue
    """
    queue:str
    exchange:str
    routing_key:str
    dlq_exchange:str|None

class PikaAsyncioImpl:

    def __init__(self):
        self._connection:AsyncioConnection = None
        self._channel:Channel = None

        self._taskCount:int = 0

    @asynccontextmanager
    async def openConnection(self, config:RabbitHostConfig):

        try:
            openedEvent = asyncio.Event()
            closedEvent = asyncio.Event()
            connection = AsyncioConnection(
                parameters=config.getPikaConfig(),
                on_open_callback=partial(self.on_connection_open, event=openedEvent),
                on_open_error_callback=self.on_connection_open_error,
                on_close_callback=partial(self.on_connection_close, event=closedEvent)
            )
            await openedEvent.wait()
            yield connection
        except Exception as err:
            logger.error("Exception when using the connection: %s", err)
            raise err
        finally:
            connection.close()
            await closedEvent.wait()

    def on_connection_open(self, conn:AsyncioConnection, event:asyncio.Event) -> None:
        """
        callback function when rabbitmq connection is established
        """
        event.set()

    def on_connection_close(self, conn:AsyncioConnection, reason:BaseException, event:asyncio.Event) -> None:
        """
        callback function when rabbitmq connection is closed
        """
        event.set()

    def on_connection_open_error(self, conn:AsyncioConnection, error:BaseException) -> None:
        pass

    @asynccontextmanager
    async def openChannel(self, connection:AsyncioConnection):

        try:
            openedEvent = asyncio.Event()
            closedEvent = asyncio.Event()

            channel = connection.channel(
                on_open_callback=partial(self.on_channel_open,
                    event=openedEvent,
                    onClosedCallback=partial(self.on_channel_close, 
                        event=closedEvent))
            )
            await openedEvent.wait()
            yield channel
        except Exception as err:
            logger.error("Exception when using the channel: %s", err)
            raise err
        finally:
            channel.close()
            await closedEvent.wait()

    def on_channel_open(self, channel:Channel, 
        event:asyncio.Event, onClosedCallback:function) -> None:
        channel.add_on_close_callback(onClosedCallback)
        event.set()

    def on_channel_close(self, channel:Channel, reason:Exception, event:asyncio.Event):
        event.set()

    async def declare_exchange(self, channel:Channel, name:str):
        """
        declare an exchange
        """
        declaredEvent = asyncio.Event()
        
        channel.exchange_declare(
            exchange=name,
            exchange_type=ExchangeType.direct,
            callback=partial(self.on_exchange_declare_ok, event=declaredEvent)
        )
        await declaredEvent.wait()

    def on_exchange_declare_ok(self, declare_ok:Exchange.DeclareOk, event:asyncio.Event) -> None:
        event.set()

    async def declare_and_bind_queue(self, channel:Channel, queue_name:str, exchange_name:str, 
        routing_key:str, arguments:dict[str,Any]) -> None:
        """
        declare an exchange
        """
        declaredEvent = asyncio.Event()

        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments=arguments,
            callback=partial(self.on_queue_declare, event=declaredEvent)
        )

        await declaredEvent.wait()

        bindEvent = asyncio.Event()

        channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=routing_key,
            callback=partial(self.on_queue_bind, event=bindEvent)
        )

        await bindEvent.wait()

    def on_queue_declare(self, declare_ok:Queue.DeclareOk, event:asyncio.Event) -> None:
        event.set()

    def on_queue_bind(self, bind_ok:Queue.BindOk, event:asyncio.Event) -> None:
        event.set()

    async def declare_main_and_dlq(self, channel:Channel, config:QueueConfig) -> None:
        await self.declare_main_and_dlq2(channel,
            queue_name=config.queue,
            exchange_name=config.exchange,
            routing_key=config.routing_key,
            dlq_exchange=config.dlq_exchange
        )

    async def declare_main_and_dlq2(self, channel:Channel, queue_name:str, 
        exchange_name:str, routing_key:str, dlq_exchange:str) -> None:
        
        dlq_queue_name:str = f"{queue_name}-dlq"
        dlq_routing_key:str = f"{routing_key}-dlq"

        # define the DLQ queue and bind to DLQ exchange
        arguments = {
            'x-queue-type': 'quorum',
        }
        await self.declare_and_bind_queue(channel, 
            queue_name=dlq_queue_name,
            exchange_name=dlq_exchange,
            routing_key=dlq_routing_key,
            arguments=arguments)
        
        # define main queue and bind to exchange
        
        # Quorum Queue delayed-retry feature
        # https://www.rabbitmq.com/docs/quorum-queues#delayed-retry
        arguments = {
            'x-queue-type': 'quorum',
            'x-delayed-retry-type': 'all', #disabled/all/failed/returned
            'x-delayed-retry-min': 1000, #ms
            'x-delayed-retry-max': 30000, #ms
            'x-delivery-limit': 5,
            'x-dead-letter-exchange': dlq_exchange,
            'x-dead-letter-routing-key': dlq_routing_key
        }
        await self.declare_and_bind_queue(channel, 
            queue_name=queue_name,
            exchange_name=exchange_name,
            routing_key=routing_key,
            arguments=arguments)

    def subscribe_queue(self, channel:Channel, queue_name:str, tg:asyncio.TaskGroup, handler:function) -> str:
        consumer_tag:str = channel.basic_consume(
            queue=queue_name,
            on_message_callback=partial(self.on_channel_message, taskgroup=tg, handler=handler),
            callback=self.on_channel_basic_consume_ok
        )
        return consumer_tag

    def on_channel_message(self, channel:Channel, method:Basic.Deliver, 
        props:BasicProperties, raw:bytes, taskgroup:asyncio.TaskGroup, handler:function) -> None:

        for (key,value) in props.headers.items():
            logger.info(f"header {key}:{value}")

        self._taskCount += 1
        # if one of the task in the taskgroup throw exception that will stop the whole task group
        # so we call the wrapper to catch the exception and keep the group running
        task = taskgroup.create_task(
            self.task_wrapper(channel, method.delivery_tag, handler(channel, raw, props)), 
            name=f"handlerTask_{self._taskCount}"
        )

    async def task_wrapper(self, channel:Channel, delivery_tag:int, handler:asyncio.coroutines) -> None:
        try:
            result = await handler
            channel.basic_ack(delivery_tag)
        except Exception as err:
            logger.error("exception when running task %s", err)
            # will Quorum Queue, once the no of times a message being rejected hit the x-delivery-limit
            # it will be move to the dead letter queue by the rabbitmq and don't need to explivitly specify 
            # the basic.reject reqeueue flag to False
            channel.basic_reject(delivery_tag, requeue=True)
        finally:
            pass

    def on_channel_basic_consume_ok(self, consumeOK:Basic.ConsumeOk) -> None:
        logger.info("channel basic ConsumeOK")

    async def cancel_subscription(self, channel:Channel, consumer_tag:str) -> None:
        cancelOKEvent = asyncio.Event()
        logger.info(f"Cancelling conumer subscription consumer_tag:{consumer_tag}")
        channel.basic_cancel(
            consumer_tag=consumer_tag,
            callback=partial(self.on_channel_basic_cancel_ok, event=cancelOKEvent)
        )
        await cancelOKEvent.wait()

    def on_channel_basic_cancel_ok(self, cancelOk:Basic.CancelOk, event:asyncio.Event) -> None:
        logger.info(f"channel BasicCancelOK")
        event.set()


class MessageThread(threading.Thread):

    def __init__(self, llm:GoogleLLM) -> None:
        super().__init__()
        self._termSignal:threading.Event = threading.Event()

        self._hostConfig:RabbitHostConfig = RabbitHostConfig(host="localhost", username="admin", password="passwd")
        
        self._request_routing_exchange:str = "request-routing"
        self._request_dlq_exchange:str = "request-dlq"

        self._google_async_queue_cfg:QueueConfig = QueueConfig(
            queue="google-genai-async-request",
            exchange=self._request_routing_exchange,
            routing_key="google-genai-async",
            dlq_exchange=self._request_dlq_exchange
        )
        self._google_async_batch_queue_cfg:QueueConfig = QueueConfig(
            queue="google-genai-async-batch-request",
            exchange=self._request_routing_exchange,
            routing_key="google-genai-async-batch",
            dlq_exchange=self._request_dlq_exchange
        )

        self._response_exchange:str = "agent-response"
        self._response_dlq_exchange:str = "agent-response-dlq"

        self._agent_response_queue_cfg:QueueConfig = QueueConfig(
            queue="agent-response",
            exchange=self._response_exchange,
            routing_key="google-genai-async-batch",
            dlq_exchange=self._response_dlq_exchange
        )

        self._googleLLM = llm

        self._taskCount:int = 0

    def run(self) -> None:
        """
        The runnable function for this Thread, and it switch to async here,
        a new eventloop initial under this thread when call asyncio below.
        """
        try:
            logger.info("Call asyncio.run() to start accepting agent request...")
            asyncio.run(self.acceptRequest(self._hostConfig))
        finally:
            logger.info("asyncio.run()... completed.")

    def stop(self) -> None:
        """ 
        Allow the parent thread to stop this thread, set the self._termSignal to 
        trigger the stop process
        """
        logger.info("set termSignal")
        self._termSignal.set()

    async def acceptRequest(self, hostCfg:RabbitHostConfig) -> None:
        """
        """
        pikaImpl = PikaAsyncioImpl()
        async with pikaImpl.openConnection(self._hostConfig) as conn, pikaImpl.openChannel(conn) as channel:

            await pikaImpl.declare_exchange(channel, self._request_routing_exchange)
            await pikaImpl.declare_exchange(channel, self._request_dlq_exchange)
            
            await pikaImpl.declare_main_and_dlq(channel, self._google_async_queue_cfg)
            
            await pikaImpl.declare_main_and_dlq(channel, self._google_async_batch_queue_cfg)
            
            await pikaImpl.declare_exchange(channel, self._response_exchange)
            await pikaImpl.declare_exchange(channel, self._response_dlq_exchange)

            await pikaImpl.declare_main_and_dlq(channel, self._agent_response_queue_cfg)

            async with asyncio.TaskGroup() as tg:
                # define background tasks
                bgTask = tg.create_task(self.backgroundTask(), name="backgroundTask")
                consumer_tag = pikaImpl.subscribe_queue(channel, self._google_async_queue_cfg.queue, tg, self.llm_async_wrapper)
                consumer_tag = pikaImpl.subscribe_queue(channel, self._google_async_batch_queue_cfg.queue, tg, self.llm_async_batch_wrapper)

            logger.info("asyncio.TaskGroup completed.")

            await pikaImpl.cancel_subscription(channel, consumer_tag)

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

    async def llm_async_wrapper(self, channel:Channel, raw:bytes, props:BasicProperties) -> None:
        request:AgentRequest = json.loads(raw)
        response:AgentResponse = await self._googleLLM.callAsyncLLM(request)
        
        channel.basic_publish(
            exchange=self._agent_response_queue_cfg.exchange, 
            routing_key=self._agent_response_queue_cfg.routing_key,
            properties=pika.BasicProperties(
                content_type="application/json",
                correlation_id=props.correlation_id,
            ),
            body=json.dumps(response.__dict__)
        )

    async def llm_async_batch_wrapper(self, channel:Channel, raw:bytes, props:BasicProperties) -> None:
        request:AgentRequest = json.loads(raw)
        batchJob:BatchJob = await self._googleLLM.callAsyncBatchLLM(request)