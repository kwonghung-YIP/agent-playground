package org.hung.spike.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpMethod;
import org.springframework.integration.annotation.MessagingGateway;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.http.dsl.Http;

import lombok.extern.slf4j.Slf4j;

@Slf4j
@Configuration
//@Profile("disabled")
public class HttpConfiguration {

    record IncomingRequest(String id, String msg) {}

    @Bean
    public IntegrationFlow httpInboundAdapter() {
        return IntegrationFlow
            .from(
                Http.inboundChannelAdapter("/inbound-adapter")
                    .requestMapping(mapping -> 
                        mapping.consumes("application/json")
                            .methods(HttpMethod.POST))
                    .requestPayloadType(IncomingRequest.class))
            .log()
            .<IncomingRequest,String>transform(req -> req.toString())
            .gateway(echoSubflow())
            .gateway(echoSubflow())
            .handle("echoGateway2","echo")         
            .log()
            .channel("dummySubflow.input")
            //.get();
            //.to(dummySubflow());
            .get();
    }

    @Bean
    public IntegrationFlow dummySubflow() {
        return f -> f.handle(msg -> log.info("MyHandler -> {}",msg));
    }

    @Bean
    public IntegrationFlow echoSubflow() {
        return f -> f.<String>handle((payload,headers) -> "Echo [%s]".formatted(payload));
    }

    @MessagingGateway(name = "echoGateway2", defaultRequestChannel = "echoSubflow.input")
    public interface EchoGateway {

        public String echo(String input);
    }

    @Bean
    public IntegrationFlow httpInboundGateway() {
        return IntegrationFlow
            .from(
                Http.inboundGateway("/inbound-gateway/{pathVar1}")
                    .requestMapping(mapping ->
                        mapping.consumes("application/json")
                            .methods(HttpMethod.POST))
                    // https://docs.spring.io/spring-integration/api/org/springframework/integration/http/inbound/BaseHttpInboundEndpoint.html#setPayloadExpression(org.springframework.expression.Expression) 
                    //.payloadExpression("#pathVariables.pathVar1")
                    .requestPayloadType(IncomingRequest.class))
                .log()
                //.handle((payload,headers) -> "My Http Response...")
                //.channel("httpRespSubflow.input")
                .<IncomingRequest,String>transform(req -> {
                    //MessageHeaderAccessor.getAccessor(null, MessageHeaderAccessor.class).getHeader("");
                    return req.toString();
                })
                .publishSubscribeChannel(pubsub -> {
                    pubsub.subscribe(httpRespSubflowA());
                    pubsub.subscribe(httpRespSubflowB());
                })
                .get();
                //.handle(msg -> log.info("{}",msg))
                //.get();
                //.to(dummySubflow());
    }

    @Bean
    public IntegrationFlow httpRespSubflowA() {
        return f -> f
            .handle(String.class,(payload,headers) -> "Http Response A:[%s]".formatted(payload))
            .log();
    }
    
    @Bean
    public IntegrationFlow httpRespSubflowB() {
        return f -> f
            .handle(String.class,(payload,headers) -> "Http Response B:[%s]".formatted(payload))
            .log()
            .handle(msg -> {});
    }
}
