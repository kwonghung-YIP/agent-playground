package hung.spike.agentflow.model;

import java.util.Map;
import java.util.UUID;

import hung.spike.agentflow.agent.AgentResponse;

public interface Flow {

    public enum Type {
        STORY
    }

    public Type getType();

    public UUID getFlowId();

    public Map<AgentResponse.Type, AgentResponse.Handler> getHandlerMapping();
    
}
