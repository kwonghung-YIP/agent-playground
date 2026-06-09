package hung.spike.agentflow.service;

import org.springframework.stereotype.Service;

import hung.spike.agentflow.agent.AgentProxy;
import hung.spike.agentflow.agent.AgentRequest;
import hung.spike.agentflow.model.Story;
import hung.spike.agentflow.repo.FlowRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import tools.jackson.databind.ObjectMapper;

@Slf4j
@RequiredArgsConstructor
@Service
public class StoryService {

    final private ObjectMapper objectMapper;
    final private FlowRepository repository;
    final private AgentProxy agent;

    public Story requestFirstDraft(String idea) {
        Story story = new Story();
        story.setIdea(idea);
        story.setStatus(Story.Status.INIT);
        //story.getStories().add("edition#1");
        //story.getComments().add("comment#1");
        repository.save(story);

        AgentRequest writerRequest = story.genAgentRequest(
            "writer#1", null, AgentRequest.Type.WRITER_FIRST_DRAFT);
        
        var userInput = objectMapper.createObjectNode();
        userInput.put("idea",idea);
        writerRequest.setUserInput(userInput);

        agent.sendRequest(writerRequest);

        return story;
    }

}
