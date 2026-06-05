package hung.spike.reactor.agent;

import java.time.Duration;

import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;
import tools.jackson.databind.ObjectMapper;

@Slf4j
@SuppressWarnings("null")
public class AgentProxy {

    private ObjectMapper objectMapper = new ObjectMapper();

    public Mono<AgentResponse> createContent(AgentRequest request) {
        log.info("call createContent...");
        
        long delay = Math.max(5,Math.round(Math.random()*20d));
        return Mono
            .fromSupplier(() -> {
                log.info("call Mono Supplier, delay {} sec...", delay);
                return storyContent(request);
            })
            .delayElement(Duration.ofSeconds(delay))
            //.log()
            ;
    }

    private AgentResponse createDummyContent(AgentRequest request) {
        var response = new AgentResponse(request);
        var output = objectMapper.createObjectNode();
        output.put("reply","Model reply for request [%s]".formatted(request.getUserInput()));
        response.setModelOutput(output);
        return response;
    }

    private AgentResponse storyContent(AgentRequest request) {
        var response = new AgentResponse(request);
        var output = objectMapper.createObjectNode();
        if (request.getAgentId().startsWith("writer")) {
            response.setType(AgentResponse.Type.WRITER_RESPONSE);
            output.put("input", request.getUserInput());
            output.put("story","Base on your idea/comment, here is my story [.....]");
        } else if (request.getAgentId().startsWith("editor")) {
            response.setType(AgentResponse.Type.EDITOR_RESPONSE);
            output.put("input", request.getUserInput());
            if (Math.random() > 0.97) {
                output.put("hasComment",false);
                output.put("comment","I have no further comment on your story.");  
            } else {
                output.put("hasComment",true);
                output.put("comment","Base on your story, here is my comment [.....]");
            }
        }
        response.setModelOutput(output);
        return response;
    }

}
