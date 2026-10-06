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
        
    # MAKE SURE YOUR ACTUAL API KEY IS HERE
    YOUTUBE_API_KEY = 'YOUR_API_KEY_HERE'
    
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

def get_unlimited_stream_url(video_id):
    """Fetches the raw audio stream from the decentralized Piped network to bypass bot detection"""
    res = requests.get(f"https://pipedapi.kavin.rocks/streams/{video_id}").json()
    audio_streams = res.get('audioStreams', [])
    if not audio_streams:
        raise Exception("Failed to extract audio stream")
    
    # Grab the native m4a/mp4 audio stream 
    best_stream = next((s for s in audio_streams if 'mp4' in s.get('mimeType', '')), audio_streams[0])
    return best_stream['url']

@app.route('/get_stream', methods=['GET'])
def stream_audio():
    # New endpoint: Feeds raw audio directly to the browser for screen-off playback
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": "No video ID"}), 400
    try:
        url = get_unlimited_stream_url(video_id)
        return jsonify({"stream_url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['GET'])
def download_audio():
    # Upgraded endpoint: Unlimited offline downloads
    video_id = request.args.get('v')
    try:
        audio_url = get_unlimited_stream_url(video_id)
        
        # Download file to the Render server temporarily, then push to phone
        audio_file = requests.get(audio_url, stream=True)
        temp_file = os.path.join(tempfile.gettempdir(), f"{video_id}.m4a")
        
        with open(temp_file, 'wb') as f:
            for chunk in audio_file.iter_content(chunk_size=1024):
                if chunk: f.write(chunk)
                
        return send_file(temp_file, as_attachment=True, mimetype='audio/mp4')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
