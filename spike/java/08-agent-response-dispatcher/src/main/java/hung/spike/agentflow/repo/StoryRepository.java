package hung.spike.agentflow.repo;

import java.util.UUID;

import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

import hung.spike.agentflow.model.Story;

@Repository
public interface StoryRepository extends CrudRepository<Story, UUID> {

}
