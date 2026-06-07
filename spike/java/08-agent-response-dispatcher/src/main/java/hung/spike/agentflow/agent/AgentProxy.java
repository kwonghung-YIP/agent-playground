package hung.spike.agentflow.agent;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.repository.CrudRepository;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;

import hung.spike.agentflow.model.Flow;
import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
@Component
public class AgentProxy {

    final private Map<Flow.Type, CrudRepository<? extends Flow, UUID>> repoMapping;

    @Qualifier("agentOutChannel")
    final private MessageChannel agentOutChannel;

    public void sendRequest(AgentRequest request) {
        var message = MessageBuilder
            .withPayload(request)
            //.setHeader("content-type", "application/json")
            .build();
        agentOutChannel.send(message);
    }

    @ServiceActivator(inputChannel = "agent-in-channel")
    public void dispatchResponse(AgentResponse response) {
        // 1. Get the Repo bean for the flow type provided by agent response.
        var repo = this.repoMapping.get(response.getFlowType());
        // 2. Search the flow instance by flow type and Id in the response.
        Optional<? extends Flow> result = repo.findById(response.getFlowId());
        result.ifPresent(flow -> {
            // 3. Identify the handler function by flow type and response type.
            var handler = flow.getHandlerMapping().get(response.getType());
            // 4. Pass the response and this agent proxy to the handler function.
            //handler.handle(this, response);
        });
    }
    
}
