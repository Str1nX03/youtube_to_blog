import os
import sys
import json
import logging
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
        
        # Detect Environment
        is_vercel = os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        
        cookies_arg = None
        
        # 1. Try Environment Variable (Best for Vercel/Production)
        env_cookies = os.environ.get('YOUTUBE_COOKIES')
        if env_cookies:
            try:
                temp_cookies_path = "/tmp/cookies.txt"
                with open(temp_cookies_path, "w") as f:
                    f.write(env_cookies)
                cookies_arg = temp_cookies_path
                logging.info("Using cookies from YOUTUBE_COOKIES environment variable.")
            except Exception as e:
                logging.warning(f"Failed to write temp cookies file: {e}")
        
        if not cookies_arg and is_vercel:
             logging.warning("Running on Vercel without cookies. YouTube might block this request.")

        ydl_opts = {
            'skip_download': True,     
            'format': 'best',          
            'writesubtitles': True,
            'writeautomaticsub': True,  
            'subtitleslangs': ['en', 'hi', 'ja', 'es'], 
            'cookiefile': cookies_arg,
            'quiet': True,
            'no_warnings': True,
            'cache_dir': '/tmp/yt-dlp-cache' if is_vercel else None,
            # EXTRA OPTIONS TO BYPASS BOT DETECTION
            'nocheckcertificate': True,
            'ignoreerrors': False,  
            'no_call_home': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(video_url, download=False)
                except Exception as dl_error:
                    logging.error(f"yt-dlp extraction error: {dl_error}")
                    raise CustomException(f"YouTube Download Error: {str(dl_error)}", sys)
                
                if not info:
                    logging.error("yt-dlp returned no information (extraction failed).")
                    return None

                subtitles = info.get('subtitles', {})
                auto_captions = info.get('automatic_captions', {})
                
                all_subs = {**auto_captions, **subtitles}
                
                if not all_subs:
                    logging.warning("No subtitles found in video metadata.")
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
                    logging.warning("Could not find a valid subtitle URL.")
                    return None

                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                response = session.get(json3_url)
                
                if response.status_code != 200:
                    logging.error(f"Failed to download subs from {json3_url}. Status: {response.status_code}")
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
            logging.error(f"yt-dlp critical failure: {str(e)}")
            if "Sign in to confirm" in str(e):
                return "Error: YouTube blocked the request from this server IP. Try running locally."
            raise CustomException(e, sys)

    def analyze(self, video_url):
        try:
            logging.info(f"Analyzing video: {video_url}")

            transcript = self.download_subs_with_ytdlp(video_url)
            
            if not transcript:
                return "Error: Unable to extract transcript (yt-dlp failed or blocked). The video might not have captions."
            
            if "Error:" in transcript: 
                return transcript

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