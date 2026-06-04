package hung.spike.reactor;

import hung.spike.reactor.agent.AgentProxy;
import hung.spike.reactor.model.Story;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class Main {
    public static void main(String[] args) throws InterruptedException {
        log.info("Hello world!");

        AgentProxy agent = new AgentProxy();

        /*
        AgentProxy.Request req = new AgentProxy.Request();
        req.setAgentId("agenId#1");
        req.setChatId("chatId#1");
        req.setUserInput("tell me a story");
    
        var resp = agent.createContent(req).block();
        log.info("Response: {}", resp);
        */


        Story story = new Story(agent, "Tell me a fairy tale.");
        story.initProcess();

        while (!story.isStoryReady()) {
            Thread.sleep(1000);
        }
    }
}