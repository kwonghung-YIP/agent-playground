package hung.spike.reactor;

import org.junit.jupiter.api.Test;

import hung.spike.reactor.agent.AgentProxy;
import hung.spike.reactor.agent.AgentRequest;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MainTests {

    @Test
    public void helloWorld() {
        log.info("here");
        
        AgentProxy agent = new AgentProxy();

        AgentRequest req = new AgentRequest();
        req.setAgentId("agenId#1");
        req.setChatId("chatId#1");
        req.setUserInput("Tell me a fairy tale!");

        agent.createContent(req)
            .subscribe(resp -> {
                log.info("{}", resp);
            });
    }
}
