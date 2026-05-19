#!/bin/bash

docker compose build --no-cache
docker compose up rabbitmq -d
sleep 30
docker exec rabbitmq /etc/rabbitmq/init-setup.sh
docker compose up python-pika -d
docker logs python-pika -f