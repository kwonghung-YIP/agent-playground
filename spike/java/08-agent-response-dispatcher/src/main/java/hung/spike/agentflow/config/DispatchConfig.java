package hung.spike.agentflow.config;

import java.util.HashMap;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import hung.spike.agentflow.model.Flow;
import hung.spike.agentflow.service.FlowService;
import hung.spike.agentflow.service.StoryService;

@Configuration
public class DispatchConfig {

    @Autowired
    private StoryService storyService;

    @Bean
    public Map<Flow.Type, FlowService> flowTypeToServiceMapping() {
        var mapping = new HashMap<Flow.Type, FlowService>();
        mapping.put(Flow.Type.STORY, storyService);
        return mapping;
    }
}
