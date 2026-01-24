import os
import sys
from groq import Groq
from colorama import Fore, Style
from src.logger import logging
from src.exception import CustomException

class BaseAgent:

    def __init__(self, name, role, model_name = "llama-3.3-70b-versatile"):

        self.name = name
        self.role = role
        self.model_name = model_name

        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(
            api_key = api_key
        )

    def generate(self, prompt):

        try:

            logging.info(f"{self.name} model whose role is {self.role} is generating content....")

            chat_completion = self.client.chat.completions.create(
                messages = [
                    {
                        "role": "system",
                        "content": self.role,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model = self.model_name,
                temperature = 0.2
            )

            logging.info(f"{self.name} model whose role is {self.role} has generated required content....")

            return chat_completion.choices[0].message.content

        except Exception as e:

            raise CustomException(e, sys)