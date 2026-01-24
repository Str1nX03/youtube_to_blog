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
        
        # Check for cookies file
        # On Vercel, the filesystem is read-only except /tmp
        # We disable cookies on Vercel to prevent Read-only filesystem errors
        is_vercel = os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        
        if is_vercel:
            cookies_arg = None
            logging.info("Running on Vercel: Cookies disabled to prevent filesystem errors.")
        else:
            cookies_arg = "cookies.txt" if os.path.exists("cookies.txt") else None
            if cookies_arg:
                logging.info(f"Using cookies from {os.path.abspath(cookies_arg)}")

        ydl_opts = {
            'skip_download': True,      # We only want metadata/subs, not video
            'writesubtitles': True,
            'writeautomaticsub': True,  # Get auto-generated subs if manual aren't there
            'subtitleslangs': ['en', 'hi', 'ja', 'es'], # Prioritize English, then others
            'cookiefile': cookies_arg,
            'quiet': True,
            'no_warnings': True,
            # CRITICAL FOR VERCEL: Point cache to writable /tmp directory
            'cache_dir': '/tmp/yt-dlp-cache' if is_vercel else None,
            # EXTRA OPTIONS TO BYPASS BOT DETECTION
            'nocheckcertificate': True,
            # 'ignoreerrors': True, # Removed to catch actual exceptions for better debugging/handling
            'no_call_home': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            # USE ANDROID CLIENT TO BYPASS "SIGN IN" CHECK
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Attempt extraction
                try:
                    info = ydl.extract_info(video_url, download=False)
                except Exception as dl_error:
                    logging.error(f"yt-dlp extraction error: {dl_error}")
                    return None
                
                if not info:
                    logging.error("yt-dlp returned no information (extraction failed).")
                    return None

                # 1. Check for manual subtitles
                subtitles = info.get('subtitles', {})
                # 2. Check for automatic captions
                auto_captions = info.get('automatic_captions', {})
                
                # Merge them (prioritize manual)
                all_subs = {**auto_captions, **subtitles}
                
                if not all_subs:
                    logging.warning("No subtitles found in video metadata.")
                    return None

                # Find the best language (Prioritize 'en', then 'en-orig', then any)
                chosen_lang = None
                for lang in ['en', 'en-orig', 'en-US', 'en-GB']:
                    if lang in all_subs:
                        chosen_lang = lang
                        break
                
                # If no English, take the first available one
                if not chosen_lang and all_subs:
                    chosen_lang = list(all_subs.keys())[0]
                    logging.warning(f"No English subs found. Falling back to language: {chosen_lang}")

                # Get the JSON3 format URL (it's the easiest to parse)
                subs_list = all_subs.get(chosen_lang, [])
                json3_url = None
                
                for sub in subs_list:
                    if sub.get('ext') == 'json3':
                        json3_url = sub.get('url')
                        break
                
                # If no json3, try extracting from the first available url
                if not json3_url and subs_list:
                     # Often the first one is usable (vtt or srv3)
                     # But for simplicity, let's try to fetch the first url and hope it's text-based
                     json3_url = subs_list[0].get('url')

                if not json3_url:
                    logging.warning("Could not find a valid subtitle URL.")
                    return None

                # Fetch the actual subtitle data
                # Using a session with headers might help bypass some checks
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                response = session.get(json3_url)
                
                if response.status_code != 200:
                    logging.error(f"Failed to download subs from {json3_url}. Status: {response.status_code}")
                    return None

                # Parse JSON3 format
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
                    # If it wasn't JSON (e.g. VTT), simply return the raw text
                    return response.text

        except Exception as e:
            logging.error(f"yt-dlp critical failure: {str(e)}")
            # On Vercel, if this fails due to IP blocking, we might want to return a helpful message
            if "Sign in to confirm" in str(e):
                return "Error: YouTube blocked the request from this server IP. Try running locally."
            raise CustomException(e, sys)

    def analyze(self, video_url):
        try:
            logging.info(f"Analyzing video: {video_url}")

            # --- TRY YT-DLP EXTRACTION ---
            transcript = self.download_subs_with_ytdlp(video_url)
            
            if not transcript:
                return "Error: Unable to extract transcript (yt-dlp failed or blocked). The video might not have captions."
            
            if "Error:" in transcript: # Pass through the specific error message from above
                return transcript

            # --- LLM ANALYSIS ---
            # Truncate to avoid token limits (15k chars is approx 3-4k tokens)
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