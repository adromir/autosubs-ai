import sys
import os
import pysubs2
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    if len(sys.argv) < 7:
        print("Usage: python _vad_clean_subprocess.py <input_srt> <audio_path> <output_srt> <vad_model> <onset> <offset>")
        sys.exit(1)
        
    input_srt = sys.argv[1]
    audio_path = sys.argv[2]
    output_srt = sys.argv[3]
    vad_model_name = sys.argv[4]
    onset = float(sys.argv[5])
    offset = float(sys.argv[6])
    
    from faster_whisper.vad import get_speech_timestamps, VadOptions
    import whisperx
    
    print("[VAD Clean Subprocess] Loading audio...", flush=True)
    audio = whisperx.load_audio(audio_path)
    
    print(f"[VAD Clean Subprocess] Running VAD on audio using Silero...", flush=True)
    vad_options = VadOptions(
        threshold=onset,
        min_speech_duration_ms=250,
        max_speech_duration_s=float('inf'),
        min_silence_duration_ms=int(offset * 1000),
        speech_pad_ms=400
    )
    
    timestamps_samples = get_speech_timestamps(audio, vad_options=vad_options, sampling_rate=16000)
    
    # Convert samples to seconds
    timestamps = []
    for ts in timestamps_samples:
        timestamps.append({
            'start': ts['start'] / 16000.0,
            'end': ts['end'] / 16000.0
        })
    
    try:
        subs = pysubs2.load(input_srt)
    except Exception as e:
        print(f"Failed to load SRT: {e}", file=sys.stderr)
        sys.exit(1)
        
    cleaned_events = []
    
    # Add a small buffer around speech
    buffer_ms = 500
    
    for event in subs.events:
        # Check if event falls inside ANY speech timestamp
        event_start_s = event.start / 1000.0
        event_end_s = event.end / 1000.0
        
        is_speech = False
        for ts in timestamps:
            ts_start = ts['start'] - (buffer_ms / 1000.0)
            ts_end = ts['end'] + (buffer_ms / 1000.0)
            
            # Subtitle overlaps with speech
            if max(event_start_s, ts_start) < min(event_end_s, ts_end):
                is_speech = True
                break
                
        if is_speech:
            cleaned_events.append(event)
            
    print(f"[VAD Clean Subprocess] Original lines: {len(subs.events)}, Cleaned lines: {len(cleaned_events)}", flush=True)
    
    subs.events = cleaned_events
    subs.save(output_srt)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
