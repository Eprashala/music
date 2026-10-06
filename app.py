from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import yt_dlp
import os
import tempfile

app = Flask(__name__)
CORS(app) # Allows your HTML file to connect

# Embed your Google Cloud YouTube Data API v3 Key here
YOUTUBE_API_KEY = 'AIzaSyBZXats0YG2QqXXLnrTdxQvgg7CtRhn1PI'

@app.route('/search', methods=['GET'])
def search_youtube():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "No query provided"}), 400
        
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=12&q={query}&type=video&key={YOUTUBE_API_KEY}"
    
    try:
        youtube_response = requests.get(url)
        return jsonify(youtube_response.json()) 
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['GET'])
def download_audio():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400

    temp_dir = tempfile.gettempdir()
    
    # Download the native m4a audio stream
    ydl_opts = {
        'format': '140',
        'outtmpl': os.path.join(temp_dir, f"{video_id}.%(ext)s"),
        'quiet': True,
        'noplaylist': True,
        'extractor_args': {'youtube': {'client': ['android']}}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
            downloaded_file = ydl.prepare_filename(info)
        
        # Send the file back to the browser
        return send_file(downloaded_file, as_attachment=True, mimetype='audio/mp4')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
