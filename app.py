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
        
     
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=12&q={query}&type=video&key={YOUTUBE_API_KEY}"
    
    try:
        search_response = requests.get(search_url).json()
        
        # 1. Extract IDs from the search results
        video_ids = ",".join([item['id']['videoId'] for item in search_response.get('items', []) if 'id' in item and 'videoId' in item['id']])
        
        # 2. Ask YouTube for the durations of those specific IDs
        if video_ids:
            duration_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_ids}&key={YOUTUBE_API_KEY}"
            duration_response = requests.get(duration_url).json()
            
            # Map the durations to their IDs
            durations = {item['id']: item['contentDetails']['duration'] for item in duration_response.get('items', [])}
            
            # 3. Inject the durations back into the search results
            for item in search_response.get('items', []):
                vid = item['id'].get('videoId')
                if vid in durations:
                    item['snippet']['duration'] = durations[vid]
                    
        return jsonify(search_response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['GET'])
def download_audio():
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400

    # Option B: The Mercenary API
    RAPIDAPI_KEY = "366a2a11d9mshfa848bdd8cef305p172a00jsn953cbb31a727"
    
    url = "https://youtube-mp36.p.rapidapi.com/dl"
    querystring = {"id": video_id}
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
    }

    try:
        # 1. Ask the API to bypass YouTube and get the raw download link
        api_response = requests.get(url, headers=headers, params=querystring)
        data = api_response.json()
        
        if "link" not in data:
            return jsonify({"error": "Third-party API failed to extract audio."}), 500
            
        audio_url = data["link"]
        
        # 2. Download the actual audio file from their server to Render
        audio_file = requests.get(audio_url, stream=True)
        
        # 3. Save it temporarily and push it securely to the user's phone
        temp_file = os.path.join(tempfile.gettempdir(), f"{video_id}.mp3")
        with open(temp_file, 'wb') as f:
            for chunk in audio_file.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    
        return send_file(temp_file, as_attachment=True, mimetype='audio/mp3')

    except Exception as e:
        return jsonify({"error": str(e)}), 500
