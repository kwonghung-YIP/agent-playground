package hung.spike.reactor.agent;

import java.util.UUID;

import lombok.Data;
import tools.jackson.databind.JsonNode;

@Data
public class AgentResponse {

    public enum Type{
        WRITER_RESPONSE,
        EDITOR_RESPONSE
    }

    private String agentId;
    private String chatId;
    private UUID requestId;
    final private UUID responseId = UUID.randomUUID();
    private Type type;
    private JsonNode modelOutput;

    public AgentResponse(AgentRequest request) {
        this.agentId = request.getAgentId();
        this.chatId = request.getChatId();
        this.requestId = request.getRequestId();
    }
}
