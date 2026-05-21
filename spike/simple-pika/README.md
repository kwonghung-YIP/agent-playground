# References:

- [Docker Hub - RabbitMq](https://hub.docker.com/_/rabbitmq)
- [RabbitMq Python Example](https://www.rabbitmq.com/tutorials/tutorial-one-python)
- [Python - Pika](https://pika.readthedocs.io/en/stable/)
- [Baeldung - Exchange, Queue, and Binding in RabbitMq](https://www.baeldung.com/java-rabbitmq-exchanges-queues-bindings)
- [Rabbitmq Config file](https://www.rabbitmq.com/docs/configure#configuration-files)
- [Rabbitmq:Definition Import at Node Boot Time](https://www.rabbitmq.com/docs/definitions#import-on-boot)
- [Python-rabbitmq-pika](https://oneuptime.com/blog/post/2025-07-02-python-rabbitmq-pika/view)

# Commands:

- To export the existing definitions from Rabbitmq API:
'''bash
curl -u admin:passwd http://localhost:15672/api/definitions > definitions.json
'''

'''bash
docker exec rabbitmq rabbitmqadmin -u admin -p passwd list users
docker exec rabbitmq rabbitmq-diagnostics -q ping


docker exec -it rabbitmq /bin/sh
chmod +x /etc/rabbitmq/init-setup.sh
docker exec rabbitmq /etc/rabbitmq/init-setup.sh
'''