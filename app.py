from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import tempfile

app = Flask(__name__)
CORS(app)

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
        video_ids = ",".join([item['id']['videoId'] for item in search_response.get('items', []) if 'id' in item and 'videoId' in item['id']])
        
        if video_ids:
            duration_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_ids}&key={YOUTUBE_API_KEY}"
            duration_response = requests.get(duration_url).json()
            durations = {item['id']: item['contentDetails']['duration'] for item in duration_response.get('items', [])}
            
            for item in search_response.get('items', []):
                vid = item['id'].get('videoId')
                if vid in durations:
                    item['snippet']['duration'] = durations[vid]
                    
        return jsonify(search_response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_unlimited_stream_url(video_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    last_error = "Unknown"
    
    # Try Piped
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.syncpundit.io"
    ]
    for base in piped_instances:
        try:
            r = requests.get(f"{base}/streams/{video_id}", headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                streams = data.get('audioStreams', [])
                if streams:
                    best = next((s for s in streams if 'mp4' in s.get('mimeType', '')), streams[0])
                    return best['url']
        except Exception as e:
            last_error = f"Piped error: {str(e)}"
            continue
            
    # Try Invidious Backup
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

    raise Exception(f"All proxy networks failed. Last error: {last_error}")

@app.route('/get_stream', methods=['GET'])
def stream_audio():
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
    video_id = request.args.get('v')
    if not video_id:
        return jsonify({"error": "No video ID provided"}), 400
    try:
        audio_url = get_unlimited_stream_url(video_id)
        audio_file = requests.get(audio_url, stream=True)
        temp_file = os.path.join(tempfile.gettempdir(), f"{video_id}.m4a")
        
        with open(temp_file, 'wb') as f:
            for chunk in audio_file.iter_content(chunk_size=1024):
                if chunk: f.write(chunk)
                
        return send_file(temp_file, as_attachment=True, mimetype='audio/mp4')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
