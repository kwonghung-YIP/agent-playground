package hung.spike.agentflow.model;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import hung.spike.agentflow.agent.AgentProxy;
import hung.spike.agentflow.agent.AgentRequest;
import hung.spike.agentflow.agent.AgentResponse;
import jakarta.persistence.CollectionTable;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Transient;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.extern.slf4j.Slf4j;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@Slf4j
@Data
@EqualsAndHashCode(callSuper = true)
@Entity
public class Story extends Flow {

    public enum Status {
        INIT,
        DRAFT,
        REVIEW,
        PUBLISH
    }

    public Story() {
        super(Flow.Type.STORY);
    }

    private String idea;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "story_editions", joinColumns = @JoinColumn(name = "flow_id"))
    private List<String> stories = new ArrayList<>();

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "story_comments", joinColumns = @JoinColumn(name = "flow_id"))
    private List<String> comments = new ArrayList<>();

    private Status status = Status.INIT;

    @Transient
    private ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public Type getType() {
        return Flow.Type.STORY;
    }

    @Override
    public Map<AgentResponse.Type, AgentResponse.Handler> getHandlerMapping() {
        return Map.of(
            AgentResponse.Type.WRITER_STORY, this::handleWriterResponse,
            AgentResponse.Type.EDITOR_COMMENT, this::handleEditorResponse
        );
    }
    
    public int getNumOfReview() {
        return this.comments.size();
    }

    public AgentRequest genAgentRequest(
        String agentId, Long chatId, AgentRequest.Type type) {

        AgentRequest request = new AgentRequest(
            getType(), getFlowId(), agentId, chatId, type);

        return request;
    }

    public void handleWriterResponse(AgentProxy agent, AgentResponse response) {
        JsonNode output = response.getModelOutput();
        String story = output.get("story").stringValue();
        this.stories.add(story);

        log.info("Received {} edition story {}.", this.stories.size(), story);

        if (this.getNumOfReview() < 2) {
            AgentRequest editorRequest = new AgentRequest(
                getType(), getFlowId(),"editor#1", -1l, AgentRequest.Type.EDITOR_REVIEW_STORY);

            var input = objectMapper.createObjectNode();
            input.put("edition", this.stories.size());
            input.put("story",story);
            editorRequest.setUserInput(input);

            agent.sendRequest(editorRequest);     
        } else {
            this.status = Status.PUBLISH;
        }
    }

    public void handleEditorResponse(AgentProxy agent, AgentResponse response) {
        JsonNode output = response.getModelOutput();
        boolean hasComment = output.get("hasComment").booleanValue();
        
        if (hasComment) {
            String comment = output.get("comment").stringValue();
            log.info("Editor has comment on the latest edition :[%s].".formatted(comment));

            this.comments.add(comment);

            AgentRequest writerRequest = new AgentRequest(
                getType(), getFlowId(), "writer#1", -1l, AgentRequest.Type.WRITER_REVISE_STORY);

            var input = objectMapper.createObjectNode();
            input.put("comment", comment);
            writerRequest.setUserInput(input);

            agent.sendRequest(writerRequest);
        } else {
            log.info("Editor has no futher comment on the story.");
            this.status = Status.PUBLISH;
        }
    }
    
}
