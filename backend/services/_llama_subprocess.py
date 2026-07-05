import sys
import os
import json
import pysubs2
from pathlib import Path

# Add project root to sys.path so we can import 'backend'
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Important: Do NOT import torch or transcriber in this file!
# This process must remain isolated to prevent HIP runtime conflicts.

def main():
    if len(sys.argv) < 6:
        print("Usage: python _llama_subprocess.py <input> <output> <target_lang> <source_lang> <model_path> [llama_params_json]")
        sys.exit(1)
        
    input_srt = sys.argv[1]
    output_srt = sys.argv[2]
    target_lang = sys.argv[3]
    source_lang = sys.argv[4]
    model_path = sys.argv[5]
    
    llama_params = {}
    if len(sys.argv) >= 7:
        try:
            llama_params = json.loads(sys.argv[6])
        except Exception as e:
            print(f"Warning: Failed to parse llama_params JSON: {e}", file=sys.stderr)
    
    # Load dotenv if available to ensure HSA overrides are respected
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    
    # We must import NativeLlamaService here, AFTER environments are set
    from backend.services.translator import NativeLlamaService
    
    # Load Glossary safely
    matched_glossary = []
    try:
        try:
            from backend.api.glossary import load_glossary
        except ImportError:
            from api.glossary import load_glossary
            
        glossary_data = load_glossary()
        for e in glossary_data:
            if e.get("source_lang", "").lower() == source_lang.lower() and e.get("target_lang", "").lower() == target_lang.lower():
                matched_glossary.append({"source": e.get("source_term"), "target": e.get("target_term")})
    except Exception as e:
        print(f"Warning: Failed to load glossary in subprocess: {e}", file=sys.stderr)
        
    llama_params["glossary"] = matched_glossary
    
    llama_service = NativeLlamaService()
    
    try:
        subs = pysubs2.load(input_srt)
    except Exception as e:
        print(f"Failed to load SRT: {e}", file=sys.stderr)
        sys.exit(1)
        
    try:
        llama_service.load_model(model_path, params=llama_params)
    except Exception as e:
        print(f"Failed to load model: {e}", file=sys.stderr)
        sys.exit(1)
        
    events = subs.events
    total = len(events)
    processed = 0

    # Sentence-aware batching logic
    min_batch = 20
    max_batch = 45
    
    if "batch_mode" in llama_params and not llama_params["batch_mode"]:
        min_batch = 1
        max_batch = 1
        
    sentence_enders = {'.', '!', '?', '"', '”', '»'}
    
    batches = []
    current_batch = []
    
    for i, event in enumerate(events):
        current_batch.append(event)
        
        # Check if we should break the batch
        if len(current_batch) >= min_batch:
            text = event.text.strip()
            # If text ends with a sentence ender, or we reached max_batch, or it's the last item
            is_sentence_end = any(text.endswith(c) for c in sentence_enders)
            if is_sentence_end or len(current_batch) >= max_batch or i == total - 1:
                batches.append(current_batch)
                current_batch = []
                
    if current_batch:
        batches.append(current_batch)

    total_batches = len(batches)
    for batch_num, batch_events in enumerate(batches, 1):
        batch_texts = [e.text.strip() for e in batch_events]

        print(f"[Llama Subprocess] Translating batch {batch_num}/{total_batches} ({len(batch_events)} lines)...", flush=True)

        try:
            glossary = llama_params.get("glossary", None)
            translations = llama_service.translate_batch(batch_texts, target_lang, source_lang, glossary)
            for i, event in enumerate(batch_events):
                if i < len(translations):
                    event.text = translations[i].strip()
        except Exception as e:
            print(f"[Llama Subprocess] Batch failed: {e}", file=sys.stderr)

        processed += len(batch_events)
        
        # Print progress to stdout for the parent process to read
        print(f"PROGRESS:{processed}/{total}", flush=True)
            
    subs.save(output_srt)
    print("DONE", flush=True)

if __name__ == "__main__":
    main()
