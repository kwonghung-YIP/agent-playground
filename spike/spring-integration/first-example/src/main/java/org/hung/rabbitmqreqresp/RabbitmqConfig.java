package org.hung.rabbitmqreqresp;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.amqp.core.AsyncAmqpTemplate;
import org.springframework.amqp.rabbit.AsyncRabbitTemplate;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.amqp.dsl.Amqp;
import org.springframework.integration.amqp.support.DefaultAmqpHeaderMapper;
import org.springframework.integration.annotation.Gateway;
import org.springframework.integration.annotation.GatewayHeader;
import org.springframework.integration.annotation.IntegrationComponentScan;
import org.springframework.integration.annotation.MessagingGateway;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.dsl.Pollers;
import org.springframework.integration.dsl.Transformers;
import org.springframework.integration.json.JsonToObjectTransformer;
import org.springframework.integration.json.ObjectToJsonTransformer;
import org.springframework.integration.mapping.support.JsonHeaders;
import org.springframework.integration.store.MessageStore;
import org.springframework.integration.store.SimpleMessageStore;
import org.springframework.integration.support.json.JsonObjectMapper;
import org.springframework.stereotype.Component;
import tools.jackson.core.json.JsonWriteFeature;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

@Slf4j
@Configuration
@IntegrationComponentScan
public class RabbitmqConfig {

    //@Bean
    public IntegrationFlow dummyFlow(AmqpTemplate amqpTemplate) {
        return IntegrationFlow
                .fromSupplier(() -> "Dummy Message !",
                        c -> c.poller(Pollers.fixedDelay(30 * 1000)))
                .log()
                .handle(message -> {
                    log.info("Received message: {}", message);
                })
                .get();
    }

    //@Bean
    public IntegrationFlow outboundGateway(AmqpTemplate amqpTemplate) {
        return IntegrationFlow
                .fromSupplier(() -> "Hello!",
                        c -> c.poller(Pollers.fixedDelay(5 * 1000)))
                .handle(Amqp.outboundGateway(amqpTemplate)
                        .routingKey("request"))
                .handle(reply -> {
                    log.info("Reply: {}, payload: {}", reply, reply.getPayload());
                })
                .get();
    }

    //@Bean
    public IntegrationFlow outboundGateway2(AmqpTemplate amqpTemplate) {
        return f ->
                f.channel("requestChannel")
                        .handle(Amqp.outboundGateway(amqpTemplate).routingKey("request"));
    }

    //@MessagingGateway(name = "myGateway", defaultRequestChannel = "requestChannel")
    public interface MyMsgGateway {
        String test(String msg);
    }

    //@Component
    static public class MyApplicationRunner implements ApplicationRunner {

        @Autowired
        private MyMsgGateway myGateway;

        @Override
        public void run(ApplicationArguments args) throws Exception {
            log.info("here");
            String response = myGateway.test("Give me a story");
            log.info("response: {}", response);
        }
    }

    public record AgentRequest(String agentId, String chatId, String userInput) {}

    public record AgentResponse(String agentId, String chatId, String modelReply) {}

    @Bean
    public IntegrationFlow asyncOutboundGateway(RabbitTemplate rabbitTemplate) {
        // https://docs.spring.io/spring-amqp/reference/amqp/message-converters.html
        // https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring
        // https://docs.spring.io/spring-boot/appendix/application-properties/index.html#application-properties.json.spring.jackson.mapper
        // https://docs.spring.io/spring-boot/appendix/application-properties/index.html#application-properties.json.spring.jackson.serialization
        JacksonJsonMessageConverter jsonMessageConverter = new JacksonJsonMessageConverter();
        rabbitTemplate.setMessageConverter(jsonMessageConverter);
        AsyncRabbitTemplate asyncRabbitTemplate = new AsyncRabbitTemplate(rabbitTemplate);
        asyncRabbitTemplate.setMandatory(true);
        asyncRabbitTemplate.setReceiveTimeout((1000*60*5));

        return f ->
                f//.transform(Transformers.toJson())
                    .channel("AgentRequest")
                    .enrichHeaders( h -> {
                        h.header("reply_to_typeId",AgentResponse.class);
                    })
                    .handle(
                        Amqp.asyncOutboundGateway(asyncRabbitTemplate)
                                .exchangeName("AgentRequest")
                                .routingKey("AgentRequest"))
                        //.log()
                        /*.enrichHeaders(h -> {
                            h.header(JsonHeaders.TYPE_ID,AgentResponse.class,true);
                            h.header(JsonHeaders.RESOLVABLE_TYPE,AgentResponse.class,true);
                        })*/
                        //.transform(Transformers.<byte[],String>converter((payload) -> new String(payload, StandardCharsets.UTF_8)))
                        //.log()
                        //.transform(Transformers.fromJson())
                        //.transform(new JsonToObjectTransformer(AgentResponse.class);
                    .log()
                    .channel("AgentResponse");
    }

    @MessagingGateway(defaultRequestChannel = "AgentRequest", defaultReplyChannel = "AgentResponse")//"asyncOutboundGateway.input")
    public interface MyAsyncGateway {

        @Gateway(replyTimeout = 120000)
        Future<String> replyAsString(AgentRequest request);

        @Gateway(replyTimeout = 120000, headers = {
                @GatewayHeader(name="content-type",value="application/json"),
                @GatewayHeader(name="content-encoding",value="utf-8")
        })
        Future<AgentResponse> replyAsResponse(AgentRequest request);
    }

    @Component
    static public class MyApplicationRunner2 implements ApplicationRunner {

        final private MyAsyncGateway asyncGateway;
        public MyApplicationRunner2(MyAsyncGateway asyncGateway) {
            this.asyncGateway = asyncGateway;
        }

        @Override
        public void run(ApplicationArguments args) throws Exception {
            log.info("here");
            AgentRequest request = new AgentRequest("123","abc", "Tell me a fairy tale!");
            //Future<String> future = asyncGateway.replyAsString(request);
            Future<AgentResponse> future = asyncGateway.replyAsResponse(request);
            /*response.whenComplete((result,error) -> {
                if (error != null) {
                    log.error("", error);
                } else {
                    log.info("response: {}", result);
                }
            });*/
            log.info("here2");
            //String response = future.get(5, TimeUnit.MINUTES);
            AgentResponse response = future.get(5, TimeUnit.MINUTES);
            log.info("response: type: {}, value:{}", response.getClass(), response);
        }
    }

    @Bean
    public MessageStore messageStore() {
        return new SimpleMessageStore();
    }

    @Bean
    public IntegrationFlow claimInOutFlow(MessageStore store) {
        return f ->
                f.log()
                        .claimCheckIn(store, endpoint -> endpoint.async(true))
                        .log()
                        .claimCheckOut(store,true, endpoint -> endpoint.async(true))
                        .log()
                ;
    }

    @MessagingGateway(defaultRequestChannel="claimInOutFlow.input")
    public interface ClaimInOutGateway {
        Future<String> testing(String input);
    }

    //@Component
    static public class MyApplicationRunner3 implements ApplicationRunner {

        final private ClaimInOutGateway gateway;
        public MyApplicationRunner3(ClaimInOutGateway gateway) {
            this.gateway = gateway;
        }

        @Override
        public void run(ApplicationArguments args) throws Exception {
            Future<String> result = gateway.testing("testing");
            log.info("{}",result.get(5,TimeUnit.MINUTES));
        }
    }
}
