package org.hung.spike.config;

import java.util.UUID;

import org.hung.spike.config.HttpConfiguration.IncomingRequest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpMethod;
import org.springframework.integration.aggregator.BarrierMessageHandler;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.http.dsl.Http;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Configuration
@Profile("disabled")
public class BarrierExample {

    @Bean
    public IntegrationFlow barrierFlow() {
        return IntegrationFlow
            .from(Http
                .inboundGateway("/barrier")
                .requestMapping(mapping -> mapping
                    .methods(HttpMethod.POST)
                    .consumes("application/json"))
                .requestPayloadType(IncomingRequest.class))
            .log()
            .enrichHeaders(spec -> spec
                .correlationId(UUID.randomUUID()))
                //.header(IntegrationMessageHeaderAccessor.CORRELATION_ID, UUID.randomUUID()))
            //.barrier(15 * 1000, spec -> spec
            //    .outputProcessor(new DefaultAggregatingMessageGroupProcessor()))
            .log()
            .publishSubscribeChannel(pubsub -> {
                pubsub.subscribe(triggerSubflow());
            })
            .handle(barrierMessageHandler())
            .get();
    }

    @Bean
    public IntegrationFlow triggerSubflow() {
        return f -> f
            .log(msg -> "entry triggerSubflow...")
            .delay(spec -> spec
                .messageGroupId("test-group-id")
                .defaultDelay(5 * 1000))
            .log()
            .log(msg -> "Wake up after delay...")
            //.trigger(barrierMessageHandler())
            // triggerActionId is the name of MessageTriggerAction bean 
            .trigger("barrierMessageHandler");
    }

    @Bean
    public BarrierMessageHandler barrierMessageHandler() {
        var handler = new BarrierMessageHandler(15 * 1000);
        //handler.setOutputChannelName("outputChannel");
        //handler.setDiscardChannelName("discardChannel");
        return handler;
    }
}
