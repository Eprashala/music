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

def get_unlimited_stream_url(video_id):
    """Fetches raw audio using multiple open-source networks (Piped & Invidious) and browser disguises."""
    
    # 1. Disguise the Python server as a normal Google Chrome desktop browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    last_error = "Unknown"
    
    # 2. Try the Piped Network First
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.syncpundit.io"
    ]
    for base in piped_instances:
        try:
            r = requests.get(f"{base}/streams/{video_id}", headers=headers, timeout=8)
            if r.status_code == 200: # Only try to read it if Cloudflare let us through
                data = r.json()
                streams = data.get('audioStreams', [])
                if streams:
                    best = next((s for s in streams if 'mp4' in s.get('mimeType', '')), streams[0])
                    return best['url']
        except Exception as e:
            last_error = f"Piped error: {str(e)}"
            continue
            
    # 3. Try the Invidious Network as a Backup
    invidious_instances = [
        "https://vid.puffyan.us",
        "https://invidious.slipfox.xyz"
    ]
    for base in invidious_instances:
        try:
            r = requests.get(f"{base}/api/v1/videos/{video_id}", headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                streams = data.get('adaptiveFormats', [])
                audio_streams = [s for s in streams if 'audio' in s.get('type', '')]
                if audio_streams:
                    best = next((s for s in audio_streams if 'mp4' in s.get('type', '')), audio_streams[0])
                    return best['url']
        except Exception as e:
            last_error = f"Invidious error: {str(e)}"
            continue

    # If every server on both networks fails, report the final error
    raise Exception(f"All open-source proxy networks blocked the connection. Last error: {last_error}")
