import sys
sys.path.append('.')
import services

transcript = 'test transcript'
visuals = {10.5: 'a graph showing temperature', 25.0: 'a pie chart'}

try:
    print('Calling Gemini...')
    summary = services.summarize_text_gemini(transcript, visuals)
    print('Success:', summary[:50])
except Exception as e:
    import traceback
    traceback.print_exc()
