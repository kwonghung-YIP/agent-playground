package org.hung.spike.config;

import java.util.UUID;

import org.hung.spike.gateway.AgentRequest;
import org.hung.spike.gateway.AgentResponse;
import org.hung.spike.gateway.SimpleAgentGateway;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.aggregator.BarrierMessageHandler;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.http.dsl.Http;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Configuration
public class SimpleAsyncGatewayWithHttpInboungGateway {

    @Bean
    public IntegrationFlow simpleAsyncGateway() {
        return IntegrationFlow
            .from("agent-request")
            .log(msg -> "entry into simpleAsyncGateway...")
            .log()
            .delay(spec -> spec
                .messageGroupId("message-group-id#1")
                .defaultDelay(5 * 1000))
            .log(msg -> "wake up after delay...")
            .<AgentRequest>handle((payload, headers) -> {
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
    public IntegrationFlow httpCompetableMainflow2(
        SimpleAgentGateway<AgentRequest, AgentResponse> gateway) {
        return IntegrationFlow
            .from(Http
                .inboundGateway("/simple-async-gateway/mono")
                .requestPayloadType(AgentRequest.class))
            .log()
            .enrichHeaders(spec -> spec.correlationId(UUID.randomUUID()))
            .log()
            .publishSubscribeChannel(pubsub -> {
                pubsub.subscribe(httpResponseSubflow());
                pubsub.subscribe(callMonoAsyncGatewaySubflow(null));
            })
            //.log(msg -> "wait for trigger barrier...")
            //.handle(httpResponseBarrier())
            .get();

    }

    /*@Bean
    public BarrierMessageHandler httpResponseBarrier() {
        BarrierMessageHandler barrier = new BarrierMessageHandler(15 * 1000);
        return barrier;
    }*/

    @Bean
    public IntegrationFlow httpResponseSubflow() {
        return f -> f
            .log(msg -> "entry httpResponseSubflow...")
            .log()
            //.delay(spec -> spec
            //    .messageGroupId("test-group-id")
            //    .defaultDelay(5 * 1000))
            .<AgentRequest, String>transform(reqeust -> {
                return "Here is the http response";
            })
            .log()
            //.log(msg -> "trigger and wake up Http Response...")
            //.trigger(httpResponseBarrier())
            ;
    }

    @Bean
    public IntegrationFlow callMonoAsyncGatewaySubflow(
        SimpleAgentGateway<AgentRequest, AgentResponse> gateway) {
        return IntegrationFlow
            .from("call-mono-async-gateway")
            .log(msg -> "entry callMonoAsyncGatewaySubflow...")
            .handle(AgentRequest.class,(payload, headers) -> {
                return gateway.chatMono(payload)
                        .flatMap(response -> {
                            log.info("run 2nd agent.chat...");             
                            AgentRequest _2ndRequest = new AgentRequest();
                            _2ndRequest.setAgentId("agentId#2");
                            _2ndRequest.setChatId(response.getChatId());
                            _2ndRequest.setRequestId(UUID.randomUUID().toString());
                            return gateway.chatMono(_2ndRequest);               
                        })
                        .map(_2ndResponse -> {
                            log.info("the final result");
                            return _2ndResponse;
                        });
            })
            .log(msg -> "done %s".formatted(msg))
            .nullChannel();
    }
}
