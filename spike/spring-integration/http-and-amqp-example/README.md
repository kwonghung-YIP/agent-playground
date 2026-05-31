```bash
curl -v -X POST \
    -H "Content-Type: application/json" \
    -d '{"id":"12345","msg":"Hello World!"}' \
    localhost:8080/demo/inbound-adapter

curl -v -X POST \
    -H "Content-Type: application/json" \
    -d '{"id":"12345","msg":"Hello World!"}' \
    localhost:8080/demo/inbound-gateway/abcd1234

curl -v -X POST \
    -H "Content-Type: application/json" \
    -d '{"id":"12345","msg":"Hello World!"}' \
    localhost:8080/demo/barrier

curl -v -X POST \
    -H "Content-Type: application/json" \
    -d '{"id":"12345","msg":"Hello World!"}' \
    localhost:8080/demo/barrier2

curl -v -X POST \
    -H "Content-Type: application/json" \
    -d '{"agentId":"agent#1","chatId":"chat#1"}' \
    localhost:8080/demo/simple-async-gateway/competable

curl -v -X POST \
    -H "Content-Type: application/json" \
    -d '{"agentId":"agent#1","chatId":"chat#1"}' \
    localhost:8080/demo/simple-async-gateway/mono
```