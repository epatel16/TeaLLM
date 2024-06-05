from pathlib import Path
from openai import OpenAI
import os
from getpass import getpass
openai_api_key = getpass("🔑 Enter your OpenAI API key: ")
os.environ["OPENAI_API_KEY"] = openai_api_key
client = OpenAI()

with client.audio.speech.with_streaming_response.create(
    model="tts-1",
    voice="onyx",
    input="""uuuuuuuuuhhhhhhhhhhhhhhh uuuuuuuuuhhhhhhhhhhhhhhh uuuuuuuuuhhhhhhhhhhhhhhh UUUUUHHHHHHH aaaaaaahhhhhhhhhhh hehehehehehehe""",
) as response:
    response.stream_to_file("speech.mp3")