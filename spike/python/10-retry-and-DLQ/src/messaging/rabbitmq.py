import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
import asyncio
from functools import partial
import threading

import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from pika.spec import Basic, BasicProperties, Exchange, Queue
from pika.exchange_type import ExchangeType

logger = logging.getLogger(__name__)

@dataclass
class RabbitmqConfig:
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

class PikaAsyncioImpl:

    def __init__(self):
        self._config:RabbitmqConfig = None

        self._connection:AsyncioConnection = None
        self._channel:Channel = None

    @asynccontextmanager
    async def openConnection(self, config:RabbitmqConfig):

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

    async def declare_and_bind_queue(self, channel:Channel, 
        queue_name:str, exchange_name:str, routing_key:str, 
        dlq_exchange:str=None, dlq_routing_key:str=None) -> None:
        """
        declare an exchange
        """
        declaredEvent = asyncio.Event()

        # Quorum Queue delayed-retry feature
        # https://www.rabbitmq.com/docs/quorum-queues#delayed-retry
        arguments = {
            'x-queue-type': 'quorum',
            'x-delayed-retry-type': 'all', #disabled/all/failed/returned
            'x-delayed-retry-min': 1000, #ms
            'x-delayed-retry-max': 30000, #ms
            'x-delivery-limit': 5
        }
        if dlq_exchange is not None:
            arguments['x-dead-letter-exchange'] = dlq_exchange
        if dlq_routing_key is not None:
            arguments['x-dead-letter-routing-key'] = dlq_routing_key

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

    async def declare_main_and_dlq(self, channel:Channel, queue_name:str, 
        exchange_name:str, routing_key:str, dlq_exchange:str) -> None:
        
        dlq_queue_name:str = f"{queue_name}-dlq"
        dlq_routing_key:str = f"{routing_key}-dlq"

        # define the DLQ queue and bind to DLQ exchange
        await self.declare_and_bind_queue(channel, 
            queue_name=dlq_queue_name,
            exchange_name=dlq_exchange,
            routing_key=dlq_routing_key)
        
        # define main queue and bind to exchange
        await self.declare_and_bind_queue(channel, 
            queue_name=queue_name,
            exchange_name=exchange_name,
            routing_key=routing_key,
            dlq_exchange=dlq_exchange,
            dlq_routing_key=dlq_routing_key)

class MessageThread(threading.Thread):
    
    def __init__(self, handler:asyncio.coroutines) -> None:
        super().__init__()
        self._termSignal:threading.Event = threading.Event()

        self._handler = handler

        self._taskCount:int = 0

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
        """
        pikaCfg = RabbitmqConfig(host="localhost", username="admin", password="passwd")
        pikaImpl = PikaAsyncioImpl()
        async with pikaImpl.openConnection(pikaCfg) as conn, pikaImpl.openChannel(conn) as channel:
            await pikaImpl.declare_exchange(channel, "dlq-exchange")
            await pikaImpl.declare_exchange(channel, "main-exchange")
            await pikaImpl.declare_main_and_dlq(channel,
                queue_name="main",
                exchange_name="main-exchange",
                routing_key="main",
                dlq_exchange="dlq-exchange")
            
            async with asyncio.TaskGroup() as tg:
                # define background tasks
                bgTask = tg.create_task(self.backgroundTask(),name="backgroundTask")
                consumer_tag = channel.basic_consume(
                    queue="main",
                    on_message_callback=partial(self.on_channel_message,taskgroup=tg),
                    callback=self.on_channel_basic_consume_ok
                )

            logger.info("asyncio.TaskGroup completed.")

            cancelOKEvent = asyncio.Event()
            logger.info(f"Cancelling conumer subscription consumer_tag:{consumer_tag}")
            channel.basic_cancel(
                consumer_tag=consumer_tag,
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

    def on_channel_message(self, channel:Channel, method:Basic.Deliver, 
        props:BasicProperties, raw:bytes, taskgroup:asyncio.TaskGroup) -> None:

        for (key,value) in props.headers.items():
            logger.info(f"header {key}:{value}")

        self._taskCount += 1
        # if one of the task in the taskgroup throw exception that will stop the whole task group
        # so we call the wrapper to catch the exception and keep the group running
        task = taskgroup.create_task(
            self.handler_wrapper(channel, method.delivery_tag), 
            name=f"handlerTask_{self._taskCount}"
        )

    def on_channel_basic_consume_ok(self, consumeOK:Basic.ConsumeOk) -> None:
        logger.info("channel basic ConsumeOK")
    
    def on_channel_basic_cancel_ok(self, cancelOk:Basic.CancelOk, event:asyncio.Event) -> None:
        logger.info(f"channel BasicCancelOK")
        event.set()

    async def handler_wrapper(self, channel:Channel, delivery_tag:int) -> None:
        try:
            result = await self._handler()

            channel.basic_ack(delivery_tag)
        except Exception as err:
            await asyncio.sleep(5)
            # will Quorum Queue, once the no of times a message being rejected hit the x-delivery-limit
            # it will be move to the dead letter queue by the rabbitmq and don't need to explivitly specify 
            # the basic.reject reqeueue flag to False
            channel.basic_reject(delivery_tag, requeue=True)
        finally:
            pass
