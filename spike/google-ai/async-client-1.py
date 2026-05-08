import logging
import dotenv

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"
logger = logging.getLogger(__name__)

dotenv.load_dotenv()

import asyncio
from google.genai.client import Client, AsyncClient
from google.genai import types
from google.genai.types import Content, Part

async def writeStory() -> None:

    systemInst = types.Content(
        role="model",
        parts=[
            Part.from_text(text="Role: You a good story teller"),
            Part.from_text(text="Goal: User will give you an idea of the story, then you write a short story follows the given rules"),
            Part.from_text(text="Rules: the story should around 1000 words and it is for children")
        ]
    )

    chatHistory = types.Content(
        role="user",
        parts=[
            Part.from_text(text="Can you tell me a love story between a chair and a table")
        ]
    )

    async with Client().aio as client:
        resp = await client.models.generate_content(
            model = "gemini-2.5-flash-lite",
            contents = chatHistory,
            config = types.GenerateContentConfig(
                system_instruction=systemInst
            )
        )
        logger.info(resp)
    
    with open("response.json", mode="w") as f:
        f.write(resp.model_dump_json(indent=4))

def main() -> None:
    asyncio.run(writeStory())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()