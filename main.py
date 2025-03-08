import streamlit as st
import yt_dlp
import os
import requests
from time import sleep

upload_endpoint = "https://api.assemblyai.com/v2/upload"
transcript_endpoint = "https://api.assemblyai.com/v2/transcript"

headers = {
    "authorization": "cbb10c26b06144c6a6e403fbf4f0a949",
    "content-type": "application/json"
}

def save_audio(url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info_dict).replace(".webm", ".mp3").replace(".m4a", ".mp3")
        
        return info_dict['title'], file_name, info_dict['thumbnail']
    
    except Exception as e:
        st.write(f"Error: {e}")
        return None, None, None

def upload_to_AssemblyAI(save_location):
    CHUNK_SIZE = 5242880
    
    def read_file(filename):
        with open(filename, 'rb') as _file:
            while True:
                data = _file.read(CHUNK_SIZE)
                if not data:
                    break
                yield data

    upload_response = requests.post(upload_endpoint, headers=headers, data=read_file(save_location))
    
    if "error" in upload_response.json():
        return None, upload_response.json()["error"]

    return upload_response.json()['upload_url'], None

def start_analysis(audio_url):
    data = {
        'audio_url': audio_url,
        'iab_categories': True,
        'content_safety': True,
        "summarization": True,
        "summary_model": "informative",
        "summary_type": "bullets"
    }

    transcript_response = requests.post(transcript_endpoint, json=data, headers=headers)
    
    if 'error' in transcript_response.json():
        return None, transcript_response.json()['error']

    return transcript_endpoint + "/" + transcript_response.json()['id'], None

def get_analysis_results(polling_endpoint):
    status = 'submitted'
    while True:
        polling_response = requests.get(polling_endpoint, headers=headers)
        status = polling_response.json()['status']
        
        if status in ['submitted', 'processing', 'queued']:
            sleep(10)
        elif status == 'completed':
            return polling_response
        else:
            return False

st.title("YouTube Video Summarizer")
st.markdown("Enter a YouTube video link below and click 'Summarize' to generate a summary.")
st.markdown("Make sure your links are in the format: https://www.youtube.com/watch?v=qrvK_KuIeJk and not https://youtu.be/qrvK_KuIeJk")

youtube_url = st.text_input("YouTube Video URL")

if st.button("Summarize"):
    if youtube_url:
        video_title, save_location, video_thumbnail = save_audio(youtube_url)
        if video_title:
            st.header(video_title)
            st.audio(save_location)
            
            audio_url, error = upload_to_AssemblyAI(save_location)
            if error:
                st.write(error)
            else:
                polling_endpoint, error = start_analysis(audio_url)
                if error:
                    st.write(error)
                else:
                    results = get_analysis_results(polling_endpoint)
                    if results:
                        st.header("Summary of this video")
                        st.write(results.json()['summary'])
                    else:
                        st.write("Error in fetching summary.")
        else:
            st.write("Error downloading the video audio.")
    else:
        st.write("Please enter a valid YouTube URL.")
