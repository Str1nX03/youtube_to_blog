import os
import sys
from src.logger import logging
import yt_dlp
import requests
from src.agent_engine.base_agent import BaseAgent
from src.exception import CustomException

class YoutubeAnalyzeAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Youtube Analyst",
            role="You are an expert video content analyst. Your goal is to extract the core topics, key takeaways, and tone from video transcripts."
        )

    def download_subs_with_ytdlp(self, video_url):
        """
        Uses yt-dlp to extract subtitle URL and download the content.
        This is the most robust method against YouTube blocks.
        """
        logging.info("Attempting to fetch transcript via yt-dlp...")
        
        cookies_arg = "cookies.txt" if os.path.exists("cookies.txt") else None
        if cookies_arg:
            logging.info(f"Using cookies from {os.path.abspath(cookies_arg)}")

        ydl_opts = {
            'skip_download': True,  
            'writesubtitles': True,
            'writeautomaticsub': True,  
            'subtitleslangs': ['en', 'hi', 'ja', 'es'],
            'cookiefile': cookies_arg,
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                subtitles = info.get('subtitles', {})
                auto_captions = info.get('automatic_captions', {})
                
                all_subs = {**auto_captions, **subtitles}
                
                if not all_subs:
                    return None

                chosen_lang = None
                for lang in ['en', 'en-orig', 'en-US', 'en-GB']:
                    if lang in all_subs:
                        chosen_lang = lang
                        break
                
                if not chosen_lang and all_subs:
                    chosen_lang = list(all_subs.keys())[0]
                    logging.warning(f"No English subs found. Falling back to language: {chosen_lang}")

                subs_list = all_subs.get(chosen_lang, [])
                json3_url = None
                
                for sub in subs_list:
                    if sub.get('ext') == 'json3':
                        json3_url = sub.get('url')
                        break
                
                if not json3_url and subs_list:
                     json3_url = subs_list[0].get('url')

                if not json3_url:
                    return None

                response = requests.get(json3_url)
                if response.status_code != 200:
                    logging.error(f"Failed to download subs from {json3_url}")
                    return None

                try:
                    data = response.json()
                    events = data.get('events', [])
                    full_text = []
                    for event in events:
                        segs = event.get('segs', [])
                        for seg in segs:
                            txt = seg.get('utf8', '').strip()
                            if txt and txt != '\n':
                                full_text.append(txt)
                    return " ".join(full_text)
                except Exception:
                    return response.text

        except Exception as e:
            logging.error(f"yt-dlp failed: {str(e)}")
            raise CustomException(e, sys)

    def analyze(self, video_url):
        try:
            logging.info(f"Analyzing video: {video_url}")
            
            transcript = self.download_subs_with_ytdlp(video_url)
            
            if not transcript:
                return "Error: Unable to extract transcript (yt-dlp failed). The video might not have captions."
            
            truncated_transcript = transcript[:15000]
            
            prompt = f"""
            Analyze the following YouTube Video Transcript.
            
            NOTE: The transcript might be in a foreign language. 
            You MUST translate the concepts and Output the final analysis in ENGLISH.

            Transcript (Truncated):
            {truncated_transcript} 

            Output a structured summary containing:
            1. Main Topic
            2. Key Points (Bullet points)
            3. The tone of the video
            4. Important keywords
            """
            
            analysis = self.generate(prompt)
            logging.info("Video analyzed successfully.")
            return analysis

        except Exception as e:
            raise CustomException(e, sys)