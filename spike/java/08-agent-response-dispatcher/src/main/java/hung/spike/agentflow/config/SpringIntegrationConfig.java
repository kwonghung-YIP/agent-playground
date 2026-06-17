package hung.spike.agentflow.config;

import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.amqp.dsl.Amqp;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.dsl.Transformers;
import org.springframework.messaging.MessageChannel;

import hung.spike.agentflow.agent.AgentResponse;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Configuration
public class SpringIntegrationConfig {

    @Value("${demo.rabbitmq.outbound.exchangeName}")
    private String outboundExchangeName;

    @Value("${demo.rabbitmq.outbound.routingKey}")
    private String outboundRoutingKey;

    @Value("${demo.rabbitmq.inbound.queueName}")
    private String inboundQueueName;


    @Bean
    public MessageChannel agentOutChannel() {
        var channel = new DirectChannel();
        return channel;
    }

    @Bean
    public IntegrationFlow agentOutFlow(AmqpTemplate amqpTemplate) {
        return IntegrationFlow
            .from(agentOutChannel())
            .log()
            //.transform(new ObjectToJsonTransformer())
            .transform(Transformers.toJson())
            .log()
            .handle(Amqp.outboundAdapter(amqpTemplate)
                .exchangeName(outboundExchangeName)
                .routingKey(outboundRoutingKey))
            .get();
    }

    @Bean
    public IntegrationFlow agentInFlow(ConnectionFactory connectionFactory) {
        return IntegrationFlow
            .from(Amqp.inboundAdapter(connectionFactory, inboundQueueName))
            .transform(Transformers.fromJson(AgentResponse.class))
            .log()
            //.handle((p,h) -> {
            //    log.info("here!");
            //    return "";
            //})
            //.nullChannel();
            .channel("agent-in-channel")
            .get();
    }
}
