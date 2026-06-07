package hung.spike.agentflow.agent;

import java.util.UUID;

import hung.spike.agentflow.model.Flow;
import lombok.Data;
import tools.jackson.databind.JsonNode;

@Data
public class AgentResponse {

    public enum Type {
        WRITER_STORY,
        EDITOR_COMMENT
    }

    final private Flow.Type flowType;
    final private UUID flowId;
    final private String agentId;
    final private Long chatId;
    final private UUID requestId;
    final private UUID responseId = UUID.randomUUID();
    final private Type type;
    
    private JsonNode modelOutput;

    public AgentResponse(AgentRequest request, Type type) {
        this.flowType = request.getFlowType();
        this.flowId = request.getFlowId();
        this.agentId = request.getAgentId();
        this.chatId = request.getChatId();
        this.requestId = request.getRequestId();
        this.type = type;
    }

    @FunctionalInterface
    public interface Handler {
        void handle(AgentProxy agent, AgentResponse resp);
    }
}
