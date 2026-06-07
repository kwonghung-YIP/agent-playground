package hung.spike.agentflow.web;

import java.util.UUID;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import hung.spike.agentflow.service.StoryService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;



@Slf4j
@RequiredArgsConstructor
@RestController
@RequestMapping(path = "/story")
public class StoryController {

    final private StoryService service;

    @GetMapping
    public String echo() {
        return "abd123";
    }

    @PostMapping(consumes = {"text/plain"})
    public UUID createStory(@RequestBody String idea) {
        var story = service.requestFirstDraft(idea);
        return story.getStoryId();
    }

}