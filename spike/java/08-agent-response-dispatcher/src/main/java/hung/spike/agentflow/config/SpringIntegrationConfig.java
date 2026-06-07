package hung.spike.agentflow.config;

import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.amqp.dsl.Amqp;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.dsl.Transformers;
import org.springframework.messaging.MessageChannel;

@Configuration
public class SpringIntegrationConfig {

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
                .exchangeName("agent-request")
                .routingKey("agnet-request"))
            .get();
    }
}
