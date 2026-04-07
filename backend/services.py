import yt_dlp
import os
import traceback
import tempfile
import logging
import base64
import subprocess
import json
import time
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import ollama
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
# Using gemini-2.5-flash which is the standard model
generation_model = genai.GenerativeModel("gemini-2.5-flash")

def call_gemini_with_retry(prompt: str | list, max_retries: int = 4):
    """
    Helper to call Gemini API and handle 429 Quota Exceeded errors with exponential backoff.
    The free tier is limited to 15 RPM.
    """
    base_wait = 15
    for attempt in range(max_retries):
        try:
            return generation_model.generate_content(prompt)
        except ResourceExhausted as e:
            if attempt == max_retries - 1:
                logger.error(f"Gemini API quota exceeded after {max_retries} attempts.")
                raise e
            wait_time = base_wait * (2 ** attempt)
            logger.warning(f"Gemini API limit reached. Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
        except Exception as e:
            # Re-raise other errors immediately
            raise e

# Define local Ollama models based on our plan
TEXT_MODEL = "qwen2.5:3b"
VISION_MODEL = "moondream"

whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        logger.info("Loading Faster-Whisper base model lazily...")
        # Using CPU because the system lacks the full CUDA toolkit (cublas64_12.dll missing)
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return whisper_model

def extract_audio(youtube_url: str) -> tuple[str, str]:
    """
    Downloads the audio from the youtube_url and returns a tuple of (file_path, video_title).
    The file should be deleted after processing.
    """
    temp_dir = tempfile.gettempdir()
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True
    }
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        video_title = info_dict.get('title', 'Unknown Title')
        video_id = info_dict.get('id')
        expected_filename = os.path.join(temp_dir, f"{video_id}.mp3")
        return expected_filename, video_title

import json

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes the audio using local faster-whisper model.
    Returns a JSON string of a list of dictionaries: [{"text": "...", "start_time_in_seconds": 0.0}]
    """
    model = get_whisper_model()
    # faster-whisper returns a generator for segments and an info object
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    chunks = []
    for segment in segments:
        chunks.append({
            "text": segment.text.strip(),
            "start_time_in_seconds": segment.start
        })
        
    return json.dumps(chunks)

def detect_visual_triggers_gemini(transcript_json: str) -> list[float]:
    prompt = f"""
    You are an AI tasked with finding moments in a video where the speaker is directing attention to something visual.
    This includes referring to a graph, chart, diagram, equation, formula, board, screen, figure, model, image, or data visually present — 
    or using phrases like "look at", "you can see", "notice", "as shown", "here we have", "on the board", "this shows", "observe", "take a look", 
    or any similar language that implies the speaker is pointing at or referencing something visible on screen. 
    Use semantic understanding, not just keyword matching — if the sentence implies the viewer should be looking at something, flag it.
    
    Transcript chunks (JSON):
    {transcript_json}
    
    Output ONLY a JSON array of floats representing the start_time_in_seconds of every flagged chunk. 
    If two flags fall within 10 seconds of each other, keep only the first.
    For example: [15.2, 85.0, 120.5]
    Do not wrap it in markdown codeblocks. Just output the array.
    """
    response = call_gemini_with_retry(prompt)
    try:
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        timestamps = json.loads(raw_text)
        if not timestamps:
            return []
        timestamps.sort()
        deduped = [timestamps[0]]
        for t in timestamps[1:]:
            if t - deduped[-1] > 10:
                deduped.append(t)
        return deduped
    except Exception as e:
        logger.error(f"Failed to parse visual triggers (Gemini): {e}")
        return []

def detect_visual_triggers_local(transcript_json: str) -> list[float]:
    prompt = f"""
    You are an AI tasked with finding moments in a video where the speaker is directing attention to something visual.
    This includes referring to a graph, chart, diagram, equation, formula, board, screen, figure, model, image, or data visually present — 
    or using phrases like "look at", "you can see", "notice", "as shown", "here we have", "on the board", "this shows", "observe", "take a look", 
    or any similar language that implies the speaker is pointing at or referencing something visible on screen. 
    Use semantic understanding, not just keyword matching — if the sentence implies the viewer should be looking at something, flag it.
    
    Transcript chunks (JSON):
    {transcript_json}
    
    Output ONLY a JSON array of floats representing the start_time_in_seconds of every flagged chunk. 
    If two flags fall within 10 seconds of each other, keep only the first.
    For example: [15.2, 85.0, 120.5]
    Do not wrap it in markdown codeblocks. Just output the array.
    """
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': prompt}
    ])
    try:
        raw_text = response['message']['content'].replace("```json", "").replace("```", "").strip()
        timestamps = json.loads(raw_text)
        if not timestamps:
            return []
        timestamps.sort()
        deduped = [timestamps[0]]
        for t in timestamps[1:]:
            if t - deduped[-1] > 10:
                deduped.append(t)
        return deduped
    except Exception as e:
        logger.error(f"Failed to parse visual triggers (Local): {e}")
        return []

def extract_audio_from_local(video_path: str) -> str:
    """
    Extracts audio from a local video file using ffmpeg.
    Returns the path to the extracted .mp3 file.
    """
    temp_dir = tempfile.gettempdir()
    # Generate a unique audio filename
    audio_path = os.path.join(temp_dir, f"local_audio_{os.path.basename(video_path)}.mp3")
    
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        audio_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path

def extract_frames(video_path: str, timestamps: list[float]) -> dict[float, str]:
    """
    Extracts base64 frames from a local video file at specific timestamps using ffmpeg.
    """
    if not timestamps:
        return {}
        
    temp_dir = tempfile.gettempdir()
    
    frames = {}
    try:
        target_size = 512
        for t in timestamps:
            output_jpg = os.path.join(temp_dir, f"frame_{t}.jpg")
            cmd = [
                "ffmpeg", "-y", "-ss", str(t), "-i", video_path, 
                "-vframes", "1", "-q:v", "2", 
                "-vf", f"scale='min({target_size},iw)':-1", 
                output_jpg
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(output_jpg):
                with open(output_jpg, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    frames[t] = encoded_string
                os.remove(output_jpg)
                
        return frames
    except Exception as e:
        logger.error(f"Error extracting frames: {e}")
        return frames

def analyze_frames_gemini(frames: dict[float, str], transcript_json: str) -> dict[float, str]:
    try:
        chunks = json.loads(transcript_json)
    except:
        chunks = []
        
    analyses = {}
    for t, b64_frame in frames.items():
        caption = ""
        for chunk in chunks:
            if abs(chunk.get("start_time_in_seconds", 0) - t) < 15:
                caption = chunk.get("text", "")
                break
                
        # Format t to HH:MM:SS
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        t_str = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
                
        prompt = f"At {t_str} the speaker said: '{caption}'. Analyze what is shown — identify any graphs, equations, diagrams, or visual data and explain it in context."
        
        try:
            image_data = base64.b64decode(b64_frame)
            image_part = {"mime_type": "image/jpeg", "data": image_data}
            response = call_gemini_with_retry([prompt, image_part])
            analyses[t] = response.text
        except Exception as e:
            logger.error(f"Failed to analyze frame at {t} (Gemini): {e}")
            
    return analyses

def analyze_frames_local(frames: dict[float, str], transcript_json: str) -> dict[float, str]:
    try:
        chunks = json.loads(transcript_json)
    except:
        chunks = []
        
    analyses = {}
    for t, b64_frame in frames.items():
        caption = ""
        for chunk in chunks:
            if abs(chunk.get("start_time_in_seconds", 0) - t) < 15:
                caption = chunk.get("text", "")
                break
                
        # Format t to HH:MM:SS
        hours = int(t // 3600)
        minutes = int((t % 3600) // 60)
        seconds = int(t % 60)
        t_str = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
                
        prompt = f"At {t_str} the speaker said: '{caption}'. Analyze what is shown — identify any graphs, equations, diagrams, or visual data and explain it in context."
        
        try:
            # Moondream expects base64 without the data:image prefix, which we already have.
            response = ollama.generate(
                model=VISION_MODEL,
                prompt=prompt,
                images=[b64_frame]
            )
            analyses[t] = response['response']
        except Exception as e:
            logger.error(f"Failed to analyze frame at {t} (Local): {e}")
            
    return analyses

def summarize_text_gemini(transcript_json: str, visual_analyses: dict[float, str] = None) -> str:
    """
    Summarizes the transcript using Gemini, weaving in visual context.
    """
    visual_context = ""
    visual_format_section = ""
    if visual_analyses:
        visual_context = "\nVisual Content Identified in the Video (from analyzing actual video frames):\n"
        for t, analysis in visual_analyses.items():
            visual_context += f"- At {t} seconds: {analysis}\n"
        visual_format_section = "\n    VISUAL CONTENT\n    Describe what was shown in the graphs, charts, diagrams, or images. Include specific numbers, labels, and data points visible in the visuals.\n"

    prompt = f"""
    You are an expert assistant. Please summarize the following video content.
    Generate the summary using plain text only. Do NOT use markdown syntax. 
    Do not use asterisks (*) for bullets, do not use hash symbols (#) for headers, 
    and do not use quotation marks around titles. Use line breaks and capitalization to create structure.
    
    CRITICAL: The "Visual Content" data below was extracted by analyzing actual frames/screenshots from the video.
    This data contains information about graphs, charts, numbers, and visuals that the speaker shows on screen.
    You MUST include this visual data in your summary. Include specific numbers, data points, labels from charts and graphs.
    Do NOT ignore the visual content. It is just as important as the spoken transcript.
    
    Format exactly like this:
    YOUR TITLE HERE

    OVERVIEW
    Your brief overview here...

    KEY TOPICS
    Topic 1
    Topic 2
{visual_format_section}
    IMPORTANT POINTS
    Point 1
    Point 2

    Transcript (JSON):
    {transcript_json}
    {visual_context}
    """
    response = call_gemini_with_retry(prompt)
    return response.text

def summarize_text_local(transcript_json: str, visual_analyses: dict[float, str] = None) -> str:
    """
    Summarizes the transcript using Local Ollama Qwen, weaving in visual context.
    """
    visual_context = ""
    visual_format_section = ""
    if visual_analyses:
        visual_context = "\nVisual Content Identified in the Video (from analyzing actual video frames):\n"
        for t, analysis in visual_analyses.items():
            visual_context += f"- At {t} seconds: {analysis}\n"
        visual_format_section = "\n    VISUAL CONTENT\n    Describe what was shown in the graphs, charts, diagrams, or images. Include specific numbers, labels, and data points visible in the visuals.\n"

    prompt = f"""
    You are an expert assistant. Please summarize the following video content.
    Generate the summary using plain text only. Do NOT use markdown syntax. 
    Do not use asterisks (*) for bullets, do not use hash symbols (#) for headers, 
    and do not use quotation marks around titles. Use line breaks and capitalization to create structure.
    
    CRITICAL: The "Visual Content" data below was extracted by analyzing actual frames/screenshots from the video.
    This data contains information about graphs, charts, numbers, and visuals that the speaker shows on screen.
    You MUST include this visual data in your summary. Include specific numbers, data points, labels from charts and graphs.
    Do NOT ignore the visual content. It is just as important as the spoken transcript.
    
    Format exactly like this:
    YOUR TITLE HERE

    OVERVIEW
    Your brief overview here...

    KEY TOPICS
    Topic 1
    Topic 2
{visual_format_section}
    IMPORTANT POINTS
    Point 1
    Point 2

    Transcript (JSON):
    {transcript_json}
    {visual_context}
    """
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': prompt}
    ])
    return response['message']['content']

def answer_question_gemini(transcript: str, question: str, visual_analyses_json: str = None) -> str:
    """
    Answers a question based on the provided transcript AND visual analyses using Gemini.
    """
    visual_context = ""
    if visual_analyses_json:
        try:
            visual_data = json.loads(visual_analyses_json)
            visual_context = "\n\nVisual Content from the Video (frame analyses at various timestamps):\n"
            for t, analysis in visual_data.items():
                visual_context += f"- At {t} seconds: {analysis}\n"
        except:
            pass

    prompt = f"""
    You are an expert assistant. Please answer the user's question based on the following transcript and visual analysis from a video. 
    Use BOTH the transcript text AND the visual content descriptions to answer the question.
    If the answer involves data shown in graphs, charts, or visual elements described in the visual content section, use that information.
    If the answer is not contained within either the transcript or visual content, politely state that the video does not cover that topic.

    Transcript:
    {transcript}
    {visual_context}

    Question:
    {question}
    """
    response = call_gemini_with_retry(prompt)
    return response.text

def answer_question_local(transcript: str, question: str, visual_analyses_json: str = None) -> str:
    """
    Answers a question based on the provided transcript AND visual analyses using Local Ollama Qwen.
    """
    visual_context = ""
    if visual_analyses_json:
        try:
            visual_data = json.loads(visual_analyses_json)
            visual_context = "\n\nVisual Content from the Video (frame analyses at various timestamps):\n"
            for t, analysis in visual_data.items():
                visual_context += f"- At {t} seconds: {analysis}\n"
        except:
            pass

    prompt = f"""
    You are an expert assistant. Please answer the user's question based on the following transcript and visual analysis from a video. 
    Use BOTH the transcript text AND the visual content descriptions to answer the question.
    If the answer involves data shown in graphs, charts, or visual elements described in the visual content section, use that information.
    If the answer is not contained within either the transcript or visual content, politely state that the video does not cover that topic.

    Transcript:
    {transcript}
    {visual_context}

    Question:
    {question}
    """
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': prompt}
    ])
    return response['message']['content']
