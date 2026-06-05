package org.hung.spike.config;

import java.util.UUID;
import java.util.concurrent.CompletableFuture;

import org.hung.spike.gateway.SimpleAgentGateway;
import org.hung.spike.gateway.AgentRequest;
import org.hung.spike.gateway.AgentResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.http.dsl.Http;

import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

@Slf4j
@Configuration
@Profile("disabled")
public class SimpleAsyncGatewayWithHttpInboundAdapter<REQ extends AgentRequest, RESP extends AgentResponse> {
    
    @Bean
    public IntegrationFlow simpleAsyncGateway() {
        return IntegrationFlow
            .from("agent-request")
            .log(msg -> "entry into simpleAsyncGAteway...")
            .log()
            .delay(spec -> spec
                .messageGroupId("message-group-#1")
                .defaultDelay(5 * 1000))
            .log(msg -> "wake up after delay...")
            .<REQ>handle((payload, headers) -> {
                AgentResponse response = new AgentResponse();
                response.setAgentId(payload.getAgentId());
                response.setChatId(payload.getChatId());
                response.setResponseId(UUID.randomUUID().toString());
                return response;
            })
            .log()
            .get();
    }

    @Bean
    public IntegrationFlow httpCompetableMainflow(
        SimpleAgentGateway<AgentRequest, AgentResponse> gateway) {
        return IntegrationFlow
            .from(Http
                .inboundChannelAdapter("/simple-async-gateway/competable")
                .requestPayloadType(AgentRequest.class))
            .log()
            .<REQ>handle((p,h) -> gateway.chatCompetable(p))
            .<CompletableFuture<RESP>>handle((p,h) -> {
                return p.thenCompose(response -> {
                    AgentRequest request = new AgentRequest();
                    request.setAgentId("agentId#2");
                    request.setChatId("chatId#2");
                    return gateway.chatCompetable(request);
                });
            })
            .log(msg -> "done! %s".formatted(msg))
            .nullChannel();
    }

    @Bean
    public IntegrationFlow httpMonoMainflow(
        SimpleAgentGateway<AgentRequest, AgentResponse> gateway) {
        return IntegrationFlow
            .from(Http
                .inboundChannelAdapter("/simple-async-gateway/mono")
                .requestPayloadType(AgentRequest.class))
            .log()
            .<REQ>handle((p,h) -> gateway.chatMono(p))
            .<Mono<RESP>>handle((p,h) -> {
                return p.map(response -> {
                    AgentRequest request = new AgentRequest();
                    request.setAgentId("agentId#2");
                    request.setChatId("chatId#2");
                    return gateway.chatMono(request);
                });
            })
            .log(msg -> "done! %s".formatted(msg))
            .nullChannel();
    }
}
