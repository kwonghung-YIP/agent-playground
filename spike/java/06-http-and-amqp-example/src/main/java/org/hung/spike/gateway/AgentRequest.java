package org.hung.spike.gateway;

import lombok.Data;

@Data
public class AgentRequest {
    private String agentId;
    private String chatId;
    private String requestId;
}
