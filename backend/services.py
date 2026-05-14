# Manideep Sai C
# Reg.no 23BCE0737

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
import re

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
    if visual_analyses:
        visual_context = "\nVisual Content Identified in the Video (from analyzing actual video frames):\n"
        for t, analysis in visual_analyses.items():
            # Convert float seconds to MM:SS
            m, s = divmod(int(t), 60)
            visual_context += f"- At {m:02d}:{s:02d}: {analysis}\n"

    prompt = f"""
    You are an expert assistant. Please summarize the following video content.
    Generate the summary using standard Markdown. Use bolding, bullet points, and headers for clarity.
    
    CRITICAL CONSTRAINTS:
    - Do NOT output reasoning, thinking process, confidence scores, or internal model notes.
    - Output ONLY the formatted summary.
    - Use MM:SS format for all timestamps (e.g., 02:45 instead of 165.0 seconds).
    - If the video contains statistics, data tables, or comparisons, use a Markdown table.
    
    The "Visual Content" section below was extracted by analyzing actual frames from the video.
    You MUST include this in your summary, formatted as a Markdown table with columns: [Timestamp, Visual Element, Analysis/Description].
    
    Structure:
    # [VIDEO TITLE]
    
    ## OVERVIEW
    [Brief overview here]
    
    ## KEY TOPICS
    - [Topic 1]
    - [Topic 2]
    
    ## VISUAL CONTENT (TABLE)
    | Timestamp | Visual Element | Analysis/Description |
    |-----------|---------------|-----------------------|
    | [MM:SS]   | [Element]     | [Detail]              |
    
    ## IMPORTANT POINTS
    - [Point 1]
    - [Point 2]
    
    Transcript:
    {transcript_json}
    {visual_context}
    """
    response = call_gemini_with_retry(prompt)
    return response.text

def summarize_text_local(transcript_json: str, visual_analyses: dict[float, str] = None) -> str:
    """
    Summarizes the transcript using Qwen 2.5 3B, with specific few-shot examples for layout.
    """
    visual_context = ""
    if visual_analyses:
        visual_context = "\nVisual Content Identified in the Video:\n"
        for t, analysis in visual_analyses.items():
            m, s = divmod(int(t), 60)
            visual_context += f"- At {m:02d}:{s:02d}: {analysis}\n"

    prompt = f"""
    You are an expert assistant. Summarize the video content using standard Markdown.
    
    CRITICAL CONSTRAINTS:
    - Do NOT output reasoning, thinking process, confidence scores, or internal notes.
    - Use MM:SS format for all timestamps.
    - Use Markdown tables for Visual Content and data comparisons.
    
    FEW-SHOT EXAMPLE:
    # Introduction to Python
    ## OVERVIEW
    A short guide on Python types.
    ## KEY TOPICS
    - Variables
    - Types
    ## VISUAL CONTENT (TABLE)
    | Timestamp | Visual Element | Analysis/Description |
    |-----------|---------------|-----------------------|
    | 01:25     | Code Snippet  | Shows `x = 5` and `y = "hello"`. |
    ## IMPORTANT POINTS
    - Python is dynamic.
    
    NOW GENERATE THE SUMMARY FOR:
    Transcript:
    {transcript_json}
    {visual_context}
    """
    response = ollama.chat(model=TEXT_MODEL, messages=[
        {'role': 'user', 'content': prompt}
    ])
    return response['message']['content']

def answer_question_gemini(transcript: str, question: str, visual_analyses_json: str = None, video_path: str = None) -> str:
    """
    Answers a question based on transcript AND visual analyses.
    Includes On-Demand frame extraction if a timestamp is detected in the question.
    """
    # --- STEP 1: Detect timestamp in question ---
    time_pattern = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?|(\d+)\s*minute|(\d+)\s*second', question, re.IGNORECASE)
    
    on_demand_visual = ""
    on_demand_audio = ""
    detected_seconds = None

    if time_pattern and video_path and os.path.exists(video_path):
        raw = time_pattern.group(0)
        parts = re.findall(r'\d+', raw)
        
        if ':' in raw:
            if len(parts) == 3:
                detected_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                detected_seconds = int(parts[0]) * 60 + int(parts[1])
        elif 'minute' in raw.lower():
            detected_seconds = int(parts[0]) * 60
        elif 'second' in raw.lower():
            detected_seconds = int(parts[0])

    if detected_seconds is not None:
        # Extract frame on-demand at that exact second
        frames = extract_frames(video_path, [float(detected_seconds)])
        
        if frames:
            try:
                chunks = json.loads(transcript) if transcript.strip().startswith('[') else []
            except:
                chunks = []
            
            # Get audio window: 30 seconds before and after
            window_chunks = [
                c for c in chunks
                if abs(c.get("start_time_in_seconds", 0) - detected_seconds) <= 30
            ]
            caption = " ".join([c.get("text", "") for c in window_chunks])
            
            # Analyze the on-demand frame with Gemini vision
            fresh_analyses = analyze_frames_gemini(frames, json.dumps(window_chunks))
            
            if fresh_analyses:
                t_key = list(fresh_analyses.keys())[0]
                on_demand_visual = f"\n\nON-DEMAND FRAME ANALYSIS at {detected_seconds}s:\n{fresh_analyses[t_key]}"
            
            on_demand_audio = f"\n\nAUDIO NEAR {detected_seconds}s (±30 seconds):\n{caption}"
        else:
            on_demand_audio = f"\n\nNo frame could be extracted at {detected_seconds}s from the video."
            on_demand_visual = ""

    # --- STEP 2: Build existing visual context ---
    visual_context = ""
    if visual_analyses_json:
        try:
            visual_data = json.loads(visual_analyses_json)
            visual_context = "\n\nPre-captured Visual Frame Analyses:\n"
            for t, analysis in visual_data.items():
                visual_context += f"- At {t} seconds: {analysis}\n"
        except:
            pass

    # --- STEP 3: Build the prompt ---
    prompt = f"""
    You are an expert video analysis assistant with access to a full transcript and visual frame analyses.

    {f"TIMESTAMP QUERY DETECTED: The user asked about {detected_seconds} seconds into the video. Use the ON-DEMAND data below as the PRIMARY source for your answer." if detected_seconds is not None else "Answer the user's question using the transcript and visual analyses below."}
    
    If detection was triggered, structure your response as:
    AUDIO (around {detected_seconds}s): [What the speaker was saying]
    VISUAL (around {detected_seconds}s): [What was shown on screen]
    CONTEXT: [Summary of the moment]

    If the answer is not found in any of the provided data, say so clearly.

    FULL TRANSCRIPT:
    {transcript}
    {visual_context}
    {on_demand_audio}
    {on_demand_visual}

    USER QUESTION:
    {question}
    """
    response = call_gemini_with_retry(prompt)
    return response.text

def answer_question_local(transcript: str, question: str, visual_analyses_json: str = None, video_path: str = None) -> str:
    """
    Answers a question using Local Qwen 2.5 3B with optional on-demand frame extraction via Moondream.
    """
    time_pattern = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?|(\d+)\s*minute|(\d+)\s*second', question, re.IGNORECASE)
    on_demand_visual = ""
    on_demand_audio = ""
    detected_seconds = None

    if time_pattern and video_path and os.path.exists(video_path):
        raw = time_pattern.group(0)
        parts = re.findall(r'\d+', raw)
        if ':' in raw:
            detected_seconds = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
        elif 'minute' in raw.lower(): detected_seconds = int(parts[0]) * 60
        elif 'second' in raw.lower(): detected_seconds = int(parts[0])

    if detected_seconds is not None:
        frames = extract_frames(video_path, [float(detected_seconds)])
        if frames:
            chunks = json.loads(transcript)
            window_chunks = [c for c in chunks if abs(c.get("start_time_in_seconds", 0) - detected_seconds) <= 30]
            caption = " ".join([c.get("text", "") for c in window_chunks])
            fresh_analyses = analyze_frames_local(frames, json.dumps(window_chunks))
            if fresh_analyses:
                t_key = list(fresh_analyses.keys())[0]
                on_demand_visual = f"\n\nON-DEMAND FRAME ANALYSIS at {detected_seconds}s:\n{fresh_analyses[t_key]}"
            on_demand_audio = f"\n\nAUDIO NEAR {detected_seconds}s (±30 seconds):\n{caption}"

    visual_context = ""
    if visual_analyses_json:
        try:
            visual_data = json.loads(visual_analyses_json)
            visual_context = "\n\nPre-captured Visual Frame Analyses:\n"
            for t, analysis in visual_data.items():
                visual_context += f"- At {t} seconds: {analysis}\n"
        except: pass

    prompt = f"""
    You are an expert video analysis assistant.
    {f"TIMESTAMP QUERY DETECTED: {detected_seconds}s. Provide AUDIO, VISUAL, and CONTEXT sections." if detected_seconds is not None else "Answer the question using provided data."}
    
    Transcript:
    {transcript}
    {visual_context}
    {on_demand_audio}
    {on_demand_visual}

    Question:
    {question}
    """
    response = ollama.chat(model=TEXT_MODEL, messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']
