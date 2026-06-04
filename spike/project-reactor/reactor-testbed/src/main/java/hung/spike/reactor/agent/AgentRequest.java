package hung.spike.reactor.agent;

import java.util.UUID;

import lombok.Data;

@Data
public class AgentRequest {
    private String agentId;
    private String chatId;
    final private UUID requestId = UUID.randomUUID();
    private String userInput;
}
