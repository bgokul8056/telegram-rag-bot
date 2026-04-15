import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class VisionSystem:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama")
        )
        self.vision_model = os.getenv("VISION_MODEL", "llava")

    def describe_image_bytes(self, image_bytes: bytes) -> str:
        """Reads image bytes directly from memory, encodes it, and queries Ollama Llava."""
        try:
            encoded_string = base64.b64encode(image_bytes).decode('utf-8')

            prompt = (
                "Describe the image in a short caption, followed by exactly 3 keywords or tags "
                "formatted as '#tag1, #tag2, #tag3'. Do not add any conversational filler."
            )

            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_string}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=200,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing the image: {str(e)}"
