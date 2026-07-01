import sys
import os
import pysubs2
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    if len(sys.argv) < 4:
        print("Usage: python _llama_clean_subprocess.py <input> <output> <model_path>")
        sys.exit(1)
        
    input_srt = sys.argv[1]
    output_srt = sys.argv[2]
    model_path = sys.argv[3]
    
    from backend.services.translator import NativeLlamaService
    
    llama_service = NativeLlamaService()
    
    try:
        subs = pysubs2.load(input_srt)
    except Exception as e:
        print(f"Failed to load SRT: {e}", file=sys.stderr)
        sys.exit(1)
        
    try:
        llama_service.load_model(model_path)
    except Exception as e:
        print(f"Failed to load model: {e}", file=sys.stderr)
        sys.exit(1)
        
    events = subs.events
    total = len(events)
    processed = 0

    # For AI cleaning, we batch texts and ask the LLM to remove spam/ads
    min_batch = 10
    max_batch = 30
    
    batches = []
    current_batch = []
    
    for event in events:
        current_batch.append(event)
        if len(current_batch) >= max_batch:
            batches.append(current_batch)
            current_batch = []
                
    if current_batch:
        batches.append(current_batch)

    total_batches = len(batches)
    cleaned_events = []
    
    for batch_num, batch_events in enumerate(batches, 1):
        batch_texts = [e.text.strip() for e in batch_events]

        print(f"[Llama Clean Subprocess] Cleaning batch {batch_num}/{total_batches} ({len(batch_events)} lines)...", flush=True)

        try:
            # We add a clean_batch method in NativeLlamaService
            cleaned_texts = llama_service.clean_batch(batch_texts)
            for i, event in enumerate(batch_events):
                if i < len(cleaned_texts):
                    # If empty string returned, it means it's spam
                    cleaned_text = cleaned_texts[i].strip()
                    if cleaned_text:
                        event.text = cleaned_text
                        cleaned_events.append(event)
        except Exception as e:
            print(f"[Llama Clean Subprocess] Batch failed: {e}", file=sys.stderr)
            # Fallback: keep original events if it fails
            cleaned_events.extend(batch_events)

        processed += len(batch_events)
        print(f"PROGRESS:{processed}/{total}", flush=True)
            
    subs.events = cleaned_events
    subs.save(output_srt)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
