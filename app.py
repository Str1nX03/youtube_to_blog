from flask import Flask, render_template, request, jsonify
from src.agents.youtube_analyzer import YoutubeAnalyzeAgent
from src.agents.researcher import ResearchAgent
from src.agents.blogger import BloggerAgent
from src.logger import logging
import os

app = Flask(__name__)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/app')
def product():
    return render_template('product.html')

@app.route('/generate', methods=['POST'])
def generate_blog():
    data = request.json
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'Please provide a valid YouTube URL'}), 400

    try:
        # 1. Initialize Agents
        youtube_agent = YoutubeAnalyzeAgent()
        research_agent = ResearchAgent()
        blogger_agent = BloggerAgent()

        # 2. Analyze Video
        logging.info("Starting Video Analysis...")
        analysis_result = youtube_agent.analyze(video_url)
        if "Error" in analysis_result and not analysis_result.startswith("Analysis"):
             # Simple check if the string returned is actually an error message
             # Adjust logic based on your specific error string returns
             return jsonify({'error': analysis_result}), 500

        # 3. Research Context
        logging.info("Starting Research...")
        research_result = research_agent.enrich_context(analysis_result)

        # 4. Write Blog
        logging.info("Writing Blog Post...")
        final_blog = blogger_agent.write_blog(analysis_result, research_result)

        return jsonify({'content': final_blog})

    except Exception as e:
        logging.error(f"Generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)