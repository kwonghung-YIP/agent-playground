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
```