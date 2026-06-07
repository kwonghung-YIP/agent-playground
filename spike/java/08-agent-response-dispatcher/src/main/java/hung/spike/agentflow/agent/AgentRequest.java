package hung.spike.agentflow.agent;

import java.util.UUID;

import hung.spike.agentflow.model.Flow;
import lombok.Data;
import tools.jackson.databind.JsonNode;

@Data
public class AgentRequest {

    public enum Type {
        WRITER_FIRST_DRAFT,
        WRITER_REVISE_STORY,
        EDITOR_REVIEW_STORY
    }

    final private Flow.Type flowType;
    final private UUID flowId;
    final private String agentId;
    final private Long chatId;
    final private UUID requestId = UUID.randomUUID();
    final private Type type;
    
    private JsonNode userInput;

}
