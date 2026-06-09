package hung.spike.agentflow.config;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.repository.CrudRepository;

import hung.spike.agentflow.model.Flow;
import hung.spike.agentflow.repo.FlowRepository;

//@Configuration
public class DispatchConfig {

    @Autowired
    private FlowRepository storyRepo;

    //@Bean
    public Map<Flow.Type, CrudRepository<? extends Flow, UUID>> flowTypeToRepoMapping() {
        var mapping = new HashMap<Flow.Type, CrudRepository<? extends Flow, UUID>>();
        mapping.put(Flow.Type.STORY, storyRepo);
        return mapping;
    }

    public CrudRepository<?, UUID> getRepo(Flow.Type type) {
        return storyRepo;
    }
}
