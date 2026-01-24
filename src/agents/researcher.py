from src.agent_engine.base_agent import BaseAgent
from duckduckgo_search import DDGS
import sys
import json
from src.exception import CustomException
from src.logger import logging

class ResearchAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name = "Senior Researcher",
            role = "You are a web researcher. Your job is to find the latest developments, facts, and external links related to a given topic to enrich content."
        )

    def search_web(self, query, max_results = 5):
        """Performs a web search using DuckDuckGo."""
        
        try:

            logging.info(f"Searching web for: {query}")

            results_text = ""
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
                if not results:
                    logging.warning(f"No results found for: {query}")
                    return ""

                for res in results:
                    title = res.get('title', 'No Title')
                    link = res.get('href', 'No Link')
                    snippet = res.get('body', 'No Snippet')
                    results_text += f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n\n"

            logging.info("Web content extracted!!")

            return results_text
        
        except Exception as e:

            raise CustomException(e, sys)
        
    def enrich_context(self, video_analysis):

        try:

            logging.info(f"Enriching context on {video_analysis}")

            search_plan_prompt = f"""
                Based on the following video analysis, generate 3 specific, high-quality search queries to find the latest updates, confirmed news, or verified facts.
                
                Video Analysis:
                {video_analysis}
                
                OUTPUT FORMAT:
                Return ONLY a raw JSON list of strings. Do not use Markdown code blocks.
                Example: ["Magnus Carlsen 2026 Candidates Tournament news", "latest updates on FIDE Candidates 2026 location", "current world chess rankings 2025"]
            """

            search_queries_raw = self.generate(search_plan_prompt)
        
            if not search_queries_raw:
                return "Error: LLM failed to generate search queries."
            
            queries = []
            try:
                clean_raw = search_queries_raw.replace('```json', '').replace('```', '').strip()
                queries = json.loads(clean_raw)
            except json.JSONDecodeError:
                queries = [
                    line.strip().lstrip('1234567890. -') 
                    for line in search_queries_raw.split('\n') 
                    if line.strip() and len(line) > 5
                ]

            if not queries:
                return "Error: Could not parse any valid search queries."

            research_summary = "External Research Findings:\n"
            for q in queries:
                if isinstance(q, str) and len(q) > 3:
                    research_summary += self.search_web(q)

            logging.info(f"Enriched context!!")
                
            return research_summary
        
        except Exception as e:

            raise CustomException(e, sys)