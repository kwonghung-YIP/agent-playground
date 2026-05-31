package org.hung.spike.gateway;

import lombok.Data;

@Data
public class AgentResponse {
    private String agentId;
    private String chatId;
    private String responseId;
}
