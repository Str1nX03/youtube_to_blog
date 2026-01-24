from src.agent_engine.base_agent import BaseAgent
from src.logger import logging
from src.exception import CustomException
import sys

class BloggerAgent(BaseAgent):

    def __init__(self):

        super().__init__(
            name = "Creative Writer",
            role = "You are a professional blog writer. You write engaging, viral-ready, and SEO-optimized articles. You combine video insights with external research."
        )

    def write_blog(self, video_analysis, research_findings):

        try:

            logging.info("Drafting a blog post.")

            prompt = f"""

            Create a high-quality blog post based on the following information.
        
            SOURCE 1: Video Analysis (Core Content)
            {video_analysis}
            
            SOURCE 2: External Research (Latest Context)
            {research_findings}
            
            Requirements:
            - Catchy Title (Make it click-worthy)
            - Engaging Introduction (Hook the reader immediately)
            - Well-structured body with clear headers
            - Integrate the external research naturally to add value
            - Conclusion with a call to action
            - Use Markdown formatting
            - Tone: Fun, informative, and accessible to general readers

            """
            blog_post = self.generate(prompt)

            logging.info("Blog post has been drafted.")

            return blog_post

        except Exception as e:

            raise CustomException(e, sys)