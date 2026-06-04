package hung.spike.reactor.model;

import java.util.ArrayList;
import java.util.List;

import hung.spike.reactor.agent.AgentProxy;
import hung.spike.reactor.agent.AgentRequest;
import hung.spike.reactor.agent.AgentResponse;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import reactor.core.Disposable;
import reactor.core.publisher.Mono;
import tools.jackson.databind.JsonNode;

@Slf4j
@Data
public class Story {

    final private AgentProxy agent;

    final private String idea;
    private List<String> editions = new ArrayList<>();
    private List<String> editorComments = new ArrayList<>();
    private boolean storyReady = false;

    public int getNumOfReview() {
        return editorComments.size();
    }

    public void initProcess() {

        AgentRequest writerRequest = new AgentRequest();
        writerRequest.setAgentId("writer#1");
        writerRequest.setChatId("chat#1");
        writerRequest.setUserInput("The idea of the story [%s]".formatted(idea));

        Story.sendAgentRequest(agent, writerRequest, this);
    }

    public void eventWriterResponse(AgentResponse writerResponse) {
        JsonNode output = writerResponse.getModelOutput();
        String story = output.get("story").stringValue();
        this.editions.add(story);

        log.info("Received {} edition from writer: {}.", this.editions.size(), story);

        if (this.getNumOfReview() < 2) {
            AgentRequest editorRequest = new AgentRequest();
            editorRequest.setAgentId("editor#1");
            editorRequest.setChatId("chat#1");
            editorRequest.setUserInput("The [%d] edition of the story: [%s]"
                .formatted(this.editions.size(), story));

            Story.sendAgentRequest(agent, editorRequest, this);           
        } else {
            this.storyReady = true;
        }
    }

    public void eventEditorResponse(AgentResponse editorResponse) {
        JsonNode output = editorResponse.getModelOutput();
        boolean hasComment = output.get("hasComment").booleanValue();
        
        if (hasComment) {
            String comment = output.get("comment").stringValue();
            log.info("Editor has comment on the latest edition :[%s].".formatted(comment));

            this.editorComments.add(comment);

            AgentRequest writerRequest = new AgentRequest();
            writerRequest.setAgentId("writer#1");
            writerRequest.setChatId("chat#1");
            writerRequest.setUserInput("Editor's comment for your last edition: [%s]"
                .formatted(comment));

            Story.sendAgentRequest(agent, writerRequest, this);
        } else {
            log.info("Editor has no futher comment on the story.");
            this.storyReady = true;
        }
    }

    static public void sendAgentRequest(AgentProxy agent, AgentRequest request, Story story) {
        log.info("Send Agent Request: [{}]", request);

        Mono<AgentResponse> mono = agent.createContent(request);
        Disposable disposable = mono.subscribe(response -> {
            dispatchAgentResponse(response, story);
        });
    }

    static public void dispatchAgentResponse(AgentResponse response, Story story) {
        log.info("Received Agent Response: [{}]", response);
        switch (response.getType()) {
            case AgentResponse.Type.WRITER_RESPONSE:
                story.eventWriterResponse(response);
                break;
            case AgentResponse.Type.EDITOR_RESPONSE:
                story.eventEditorResponse(response);
                break;
            default:
                break;
        }
    }
}
