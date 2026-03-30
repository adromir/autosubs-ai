import os
import gc
import sys
import pysubs2
import requests
import json
import threading
from typing import List
from pathlib import Path

# NOTE: 'import torch' and 'from transformers import pipeline' are intentionally NOT imported at module level.
# This prevents ROCm/HIP initialization (which can hang) from blocking server startup.

# Enable experimental PyTorch ROCm SDPA Flash Attention natively suppressing warnings
os.environ["TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL"] = "1"

NLLB_LANG_MAP = {
    "en": "eng_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "it": "ita_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "zh": "zho_Hans",
    "id": "ind_Latn",
}

# Global cache for the translation pipeline
_translation_cache = {
    "model_name": None,
    "device": None,
    "model": None,
    "tokenizer": None
}

def clear_translation_cache():
    global _translation_cache
    if _translation_cache["model"] is not None:
        del _translation_cache["model"]
        _translation_cache["model"] = None
        
    if _translation_cache["tokenizer"] is not None:
        del _translation_cache["tokenizer"]
        _translation_cache["tokenizer"] = None

    _translation_cache["model_name"] = None
    _translation_cache["device"] = None
    
    try:
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except:
        pass

def translate_srt(input_srt_path: str, output_srt_path: str, target_lang: str, source_lang: str = "en", provider: str = "auto", cancel_check = None, progress_callback = None):
    global _translation_cache
    
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    
    nllb_target = NLLB_LANG_MAP.get(target_lang, f"{target_lang}_Latn")
    nllb_source = NLLB_LANG_MAP.get(source_lang, "eng_Latn")
    
    print(f"Translating {input_srt_path} from {nllb_source} to {nllb_target}...")
    
    # Device detection
    device_name = "cpu"
    if provider in ["cuda", "nvidia", "rocm", "amd", "auto"] and torch.cuda.is_available():
        device_name = "cuda:0"
    elif provider == "directml" or (provider == "auto" and 'torch_directml' in sys.modules):
        try:
            import torch_directml
            device_name = torch_directml.device()
        except ImportError:
            pass
            
    model_name = "facebook/nllb-200-distilled-600M"
    cache_dir = Path(__file__).parent.parent / "model_cache" / "nllb"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Reload model if properties changed
    if _translation_cache["model_name"] != model_name or _translation_cache["device"] != device_name:
        print(f"Loading Translation Model: {model_name} on {device_name} [float16, SDPA]...")
        clear_translation_cache()
        
        dtype = torch.float16 if "cuda" in str(device_name) or "privateuse" in str(device_name) else torch.float32
        
        # We use local_files_only if the model is correctly cached to prevent constant network checks
        try:
            # We already set HF_HUB_OFFLINE=1 in main.py, but we stay explicit here
            tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir), local_files_only=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                dtype=dtype,
                attn_implementation="sdpa",
                tie_word_embeddings=False,
                cache_dir=str(cache_dir),
                local_files_only=True
            ).to(device_name)
        except Exception:
            # Fallback if first run or cache incomplete
            print(f" -> Initializing or updating model weights from HuggingFace...")
            # Temporarily disable offline mode to allow download
            os.environ["HF_HUB_OFFLINE"] = "0"
            os.environ["TRANSFORMERS_OFFLINE"] = "0"
            try:
                tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    dtype=dtype,
                    attn_implementation="sdpa",
                    tie_word_embeddings=False,
                    cache_dir=str(cache_dir)
                ).to(device_name)
            finally:
                # Re-engage offline mode
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
        
        _translation_cache.update({
            "model_name": model_name,
            "device": device_name,
            "model": model,
            "tokenizer": tokenizer
        })
    else:
        model = _translation_cache["model"]
        tokenizer = _translation_cache["tokenizer"]
    
    # Load subs
    try:
        subs = pysubs2.load(input_srt_path)
    except Exception as e:
        print(f"Failed to load SRT: {e}")
        raise
        
    texts = [event.text for event in subs.events]
    
    # Translate in batches
    batch_size = 16
    translated_texts = []
    
    # Get target language token ID
    forced_bos_token_id = tokenizer.convert_tokens_to_ids(nllb_target)
    tokenizer.src_lang = nllb_source
    
    for i in range(0, len(texts), batch_size):
        if cancel_check and cancel_check(): raise InterruptedError("Cancelled by user")
        batch = texts[i:i+batch_size]
        if not batch: continue
        
        # Encode inputs
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=400).to(device_name)
        
        # Generate translations
        with torch.no_grad():
            generated_tokens = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=400
            )
        
        # Decode results
        batch_translations = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        translated_texts.extend(batch_translations)
        
        if progress_callback and len(texts) > 0:
            current_idx = min(i + batch_size, len(texts))
            progress_callback(current_idx / len(texts))
            
    # Reassign translated text
    for i, event in enumerate(subs.events):
        if i < len(translated_texts):
            event.text = translated_texts[i]
        
    subs.save(output_srt_path)
    print(f"Successfully translated into {nllb_target} and saved to {output_srt_path}")


    subs.save(output_srt_path)
    print(f"Successfully translated into {nllb_target} and saved to {output_srt_path}")


# ── Native Llama-CPP Translation (In-Process) ──

class NativeLlamaService:
    def __init__(self):
        self.model = None
        self.model_path = None
        self.n_ctx = 4096
        self.lock = threading.Lock()

    def load_model(self, model_path: str, n_gpu_layers: int = -1):
        with self.lock:
            if self.model and self.model_path == model_path:
                return
            
            self.unload_model()
            
            from llama_cpp import Llama
            # For AMD 9060XT, n_gpu_layers=99 sends everything to the GPU (if compiled with HIP/ROCm)
            # We set verbose=True to see the logs in the terminal for verification.
            self.model = Llama(
                model_path=model_path,
                n_gpu_layers=99,
                n_ctx=self.n_ctx,
                n_batch=512,
                logits_all=False,
                use_mlock=True,
                use_mmap=True,
                flash_attn=True,
                verbose=True
            )
            self.model_path = model_path

    def unload_model(self):
        if self.model:
            del self.model
            self.model = None
            self.model_path = None
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def translate_batch(self, texts: List[str], target_lang: str, source_lang: str) -> List[str]:
        if not self.model:
            raise RuntimeError("Llama model not loaded")

        # Prompt engineering for subtitle translation
        # We ask for JSON for parseability
        numbered_input = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            f"You are a professional subtitle translator. "
            f"Translate each numbered line from {source_lang} to {target_lang}. "
            f"Respond ONLY with a JSON array of strings in the exact same order, e.g. [\"line1\", \"line2\"]. "
            f"Do NOT include explanations or markdown.<|eot_id|>"
            f"Lines to translate:\n{numbered_input}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        
        from llama_cpp import LlamaGrammar
        
        # GBNF Grammar to force a JSON array of strings: ["a", "b", "c"]
        json_grammar = r"""
        root   ::= "[" space (string (space "," space string)*)? space "]"
        string ::= "\"" ([^"\\\n] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
        space  ::= [ \t\n\r]*
        """
        grammar = LlamaGrammar.from_string(json_grammar)

        output = self.model(
            prompt,
            max_tokens=self.n_ctx,
            temperature=0.1,
            stop=["<|eot_id|>", "<|end_of_text|>"],
            grammar=grammar,
            cache_prompt=True,
            echo=False
        )
        
        # Raw response contains the assistent's text starting from the opening bracket.
        # Since the grammar includes the brackets, we take it as-is.
        raw_response = output["choices"][0]["text"].strip()
        
        # Grammar ensures it starts with [ and ends with ] and is valid.
        # But we still do our newline fix just in case the LLM used literal \N instead of escaped \\N
        fixed_response = raw_response.strip()
        
        # Cleanup common LLM JSON mishaps
        if fixed_response.endswith(",]"):
            fixed_response = fixed_response[:-2] + "]"
        elif fixed_response.endswith(", ]"):
            fixed_response = fixed_response[:-3] + "]"
        
        fixed_response = fixed_response.replace("\\N", "\\\\N").replace("\\n", "\\\\n")

        translations = []
        try:
            translations = json.loads(fixed_response)
            if not isinstance(translations, list):
                translations = []
        except Exception as e:
            print(f"[Native Llama] JSON Parse Error: {e}. Attempting robust regex fallback...")
            # Pattern for finding strings in JSON-like structure: "((?:[^"\\]|\\.)*)"
            # This regex captures the contents of a double-quoted string while respecting escaped quotes.
            import re
            matches = re.finditer(r'"((?:[^"\\]|\\.)*)"', raw_response)
            translations = [m.group(1) for m in matches]
            
        # Post-process translations for alignment and common escape fixes
        final_translations = []
        for i in range(len(texts)):
            if i < len(translations):
                # Unescape common JSON escapes that json.loads normally handles
                t = str(translations[i])
                t = t.replace('\\"', '"').replace('\\\\', '\\')
                final_translations.append(t)
            else:
                # Fallback to original text if LLM under-produced or was truncated
                final_translations.append(texts[i])
                
        return final_translations

# Singleton instance
llama_service = NativeLlamaService()

def native_llama_translate(input_srt_path: str, output_srt_path: str, target_lang: str, source_lang: str = "en", model_path: str = None, cancel_check = None, progress_callback = None):
    print(f"Translating {input_srt_path} to {target_lang} via Native Llama GGUF...")
    
    # Path resolution: If not absolute and doesn't exist, check backend/models/
    resolved_path = model_path
    if resolved_path and not os.path.isabs(resolved_path) and not os.path.exists(resolved_path):
        # We try a few common locations
        base_dir = Path(__file__).parent.parent
        searched_paths = [
            base_dir / "models" / resolved_path,
            base_dir / "models" / "llama" / resolved_path,
            Path.cwd() / "backend" / "models" / resolved_path
        ]
        
        found = False
        for p in searched_paths:
            if p.exists():
                resolved_path = str(p)
                found = True
                print(f"[Native Llama] Resolved model path to: {resolved_path}")
                break
        
        if not found:
            print(f"[Native Llama] ERROR: Could not find model '{model_path}' in searched locations:")
            for p in searched_paths:
                print(f"  - ATTEMPTED: {p}")
            
    if not resolved_path or not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Llama GGUF model not found at: {resolved_path or model_path}")
    
    model_path = resolved_path
        
    try:
        subs = pysubs2.load(input_srt_path)
    except Exception as e:
        print(f"Failed to load SRT for Llama: {e}")
        raise
        
    # Ensure model is loaded
    llama_service.load_model(model_path)
    
    events = subs.events
    total = len(events)
    processed = 0
    batch_size = 15

    for batch_start in range(0, total, batch_size):
        if cancel_check and cancel_check(): raise InterruptedError("Cancelled by user")

        batch_events = events[batch_start:batch_start + batch_size]
        batch_texts = [e.text.strip() for e in batch_events]

        try:
            translations = llama_service.translate_batch(batch_texts, target_lang, source_lang)
            for i, event in enumerate(batch_events):
                if i < len(translations):
                    event.text = translations[i].strip()
        except Exception as e:
            print(f"[Native Llama] Batch failed: {e}")

        processed += len(batch_events)
        if progress_callback and total > 0:
            progress_callback(processed / total)
            
    subs.save(output_srt_path)
    print(f"Saved Native Llama translated subtitle to {output_srt_path}")
