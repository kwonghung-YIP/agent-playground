#!/bin/sh
while true; do
    rabbitmq-diagnostics -q ping
    if [ $? -eq 0 ]; then
        break
    fi
    sleep 5
done
echo "Create exchange or queue after here..."

rabbitmqadmin -u admin -p passwd list users
rabbitmqadmin -u admin -p passwd declare queue --name request
rabbitmqadmin -u admin -p passwd declare queue --name response