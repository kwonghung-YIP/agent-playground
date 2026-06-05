package org.hung.spike.gateway;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Future;

import org.springframework.integration.annotation.MessagingGateway;

import reactor.core.publisher.Mono;

@MessagingGateway(defaultRequestChannel = "agent-request")
public interface SimpleAgentGateway<REQ extends AgentRequest, RESP extends AgentResponse> {

    public Future<RESP> chatFuture(REQ request);

    public CompletableFuture<RESP> chatCompetable(REQ request);

    public Mono<RESP> chatMono(REQ request);

}
