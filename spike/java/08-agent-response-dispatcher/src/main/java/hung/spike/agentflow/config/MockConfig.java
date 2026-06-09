package hung.spike.agentflow.config;

import java.util.UUID;

import org.springframework.amqp.core.AmqpTemplate;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.amqp.dsl.Amqp;
import org.springframework.integration.dsl.IntegrationFlow;
import org.springframework.integration.dsl.Transformers;

import hung.spike.agentflow.agent.AgentRequest;
import hung.spike.agentflow.agent.AgentResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import tools.jackson.databind.ObjectMapper;

@Slf4j
@RequiredArgsConstructor
@Configuration
public class MockConfig {

    @Value("${demo.rabbitmq.outbound.queueName}")
    private String outboundQueueName;

    @Value("${demo.rabbitmq.inbound.exchangeName}")
    private String inboundExchangeName;

    @Value("${demo.rabbitmq.inbound.routingKey}")
    private String inboundRoutingKey;

    final private ObjectMapper objectMapper;

    @Bean
    public IntegrationFlow mockAgentFlow(
        ConnectionFactory connectionFactory, AmqpTemplate amqpTemplate) {
        
        return IntegrationFlow
            .from(Amqp.inboundAdapter(connectionFactory, outboundQueueName))
            .log()
            .transform(Transformers.fromJson())
            .<AgentRequest, AgentResponse>transform(this::mockResponse)
            .transform(Transformers.toJson())
            .log()
            .handle(Amqp.outboundAdapter(amqpTemplate)
                .exchangeName(inboundExchangeName)
                .routingKey(inboundRoutingKey))
            .get();
    }

    private AgentResponse mockResponse(AgentRequest request) {
        
        AgentResponse response;
        var userInput = request.getUserInput();
        var modelOutput = objectMapper.createObjectNode();

        UUID chatId = request.getChatId();
        chatId = (chatId == null) ? UUID.randomUUID() : chatId;

        switch (request.getType()) {
            case AgentRequest.Type.WRITER_FIRST_DRAFT:
                String idea = userInput.get("idea").asString();

                modelOutput.put("input", "Idea of the story [%s]".formatted(idea));
                modelOutput.put("story","Base on the story idea, here is my first draft [.....]");

                response = new AgentResponse(request, AgentResponse.Type.WRITER_STORY);
                response.setChatId(chatId);
                response.setModelOutput(modelOutput);
                return response;
            case AgentRequest.Type.WRITER_REVISE_STORY:
                String comment = userInput.get("comment").asString();

                modelOutput.put("input", "Comment for the last edition [%s]".formatted(comment));
                modelOutput.put("story","Base on editor's comment, here is my new edition [.....]");

                response = new AgentResponse(request, AgentResponse.Type.WRITER_STORY);
                response.setModelOutput(modelOutput);
                return response;
            case AgentRequest.Type.EDITOR_REVIEW_STORY:
                int edition = userInput.get("edition").asInt();
                String story = userInput.get("story").asString();

                modelOutput.put("input", "%d edition of the story [%s]".formatted(edition, story));
                if (Math.random() > 0.97) {
                    modelOutput.put("hasComment",false);
                    modelOutput.put("comment","I have no further comment on the story.");  
                } else {
                    modelOutput.put("hasComment",true);
                    modelOutput.put("comment","Base on the latest edition, here is my comment [.....]");
                }

                response = new AgentResponse(request, AgentResponse.Type.EDITOR_COMMENT);
                response.setChatId(chatId);
                response.setModelOutput(modelOutput);
                return response;
            default:
                return null;
        }
    }
}
