package hung.spike.reactor;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import hung.spike.reactor.agent.AgentProxy;
import hung.spike.reactor.model.Story;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;
import reactor.core.publisher.MonoSink;

@Slf4j
public class Main {
    public static void main(String[] args) throws InterruptedException {
        log.info("Hello world!");
        //timeoutAndRetry();
        sinkTimeoutRetry();
    }

    static private void firstStory() throws InterruptedException {
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

    static private void timeoutAndRetry() {
        Mono<String> mono = Mono.never()
            .cast(String.class)
            .timeout(Duration.ofSeconds(5))
            .retry(3)
            .log();

        mono.subscribe(data -> log.info("{}", data),
                err -> log.error("exception ~?~?~", err));

        mono.then().block();
    }

    @Data
    static public class SinkWrapper {
        
        private AtomicBoolean emit = new AtomicBoolean();
        private AtomicInteger counter = new AtomicInteger();
        final private String data;

        public void monoSinkConsumer(MonoSink<String> sink) {
            int i = counter.getAndIncrement();
            log.info("invoke monoSinkConsumer - count:[{}]", i);

            if (/*!emit.get()  && */i > 17) {
                log.info("emit data [{}] at count[{}]", data, i);
                sink.success("[%s] at count:%d - thread:%s".formatted(data, i, Thread.currentThread().getName()));
                //emit.set(true);;
            }
        }
    }

    static private void sinkTimeoutRetry() {
        var wrapper = new SinkWrapper("You are a Hero!");

        Mono<String> mono = Mono.create(wrapper::monoSinkConsumer)
            .timeout(Duration.ofSeconds(5))
            .retry(20)
            .log();

        mono.subscribe(data -> log.info("{}", data),
                err -> log.error("exception ~?~?~", err));

        //mono.subscribe(data -> log.info("{}", data),
        //        err -> log.error("exception ~?~?~", err));

        mono.then().block();
    }
}