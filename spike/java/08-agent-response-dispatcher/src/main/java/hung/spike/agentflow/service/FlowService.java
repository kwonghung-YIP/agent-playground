package hung.spike.agentflow.service;

import hung.spike.agentflow.agent.AgentResponse;
import hung.spike.agentflow.model.Flow;

public interface FlowService {

    void handleResponse(Flow flow, AgentResponse response);

}
