package hung.spike.agentflow.agent;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.integration.support.MessageBuilder;
import org.springframework.messaging.MessageChannel;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;

@RequiredArgsConstructor
@Component
public class AgentRequestSender {

    @Qualifier("agentOutChannel")
    final private MessageChannel agentOutChannel;

    public void sendRequest(AgentRequest request) {
        var message = MessageBuilder
            .withPayload(request)
            //.setHeader("content-type", "application/json")
            .build();
        agentOutChannel.send(message);
    }
}
