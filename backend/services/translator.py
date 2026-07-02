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

    def load_model(self, model_path: str, n_gpu_layers: int = -1, params: dict = None):
        if params is None:
            params = {}
            
        with self.lock:
            if self.model and self.model_path == model_path:
                return
            
            self.unload_model()
            
            self.n_ctx = params.get("n_ctx", 4096)
            n_batch = params.get("n_batch", 2048)
            flash_attn = params.get("flash_attn", True)
            self.disable_reasoning = params.get("disable_reasoning", True)
            self.supports_reasoning_disable = params.get("supports_reasoning_disable", False)
            spec_draft_n_max = params.get("spec_draft_n_max", 0)
            
            from llama_cpp import Llama
            # For AMD 9060XT, n_gpu_layers=99 sends everything to the GPU (if compiled with HIP/ROCm)
            # We set verbose=True to see the logs in the terminal for verification.
            import multiprocessing
            try:
                n_threads = max(1, multiprocessing.cpu_count() - 1)
            except Exception:
                n_threads = 4

            print(f"[Native Llama] Initializing Llama instance with n_ctx={self.n_ctx}, n_batch={n_batch}, flash_attn={flash_attn}, spec_draft_n_max={spec_draft_n_max}")
            
            kwargs = {
                "model_path": model_path,
                "n_gpu_layers": 99,
                "n_ctx": self.n_ctx,
                "n_batch": n_batch,
                "n_threads": n_threads,
                "logits_all": False,
                "use_mlock": False,
                "use_mmap": True,
                "flash_attn": flash_attn,
                "verbose": True
            }
            
            # Robust MTP injection: Check if llama_cpp bindings support MTP natively yet
            if spec_draft_n_max > 0:
                import inspect
                sig = inspect.signature(Llama.__init__)
                if "spec_draft_n_max" in sig.parameters:
                    kwargs["spec_draft_n_max"] = spec_draft_n_max
                if "draft_n_max" in sig.parameters:
                    kwargs["draft_n_max"] = spec_draft_n_max
            
            self.model = Llama(**kwargs)
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

        numbered_input = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        system_instruction = (
            f"You are an expert audiovisual translator. Your task is to translate subtitles from {source_lang} to {target_lang}. "
            f"Follow these rules strictly:\n"
            f"1. Preserve the original tone, context, and nuance of the dialogue.\n"
            f"2. Keep translations natural and concise, suitable for subtitle reading speeds.\n"
            f"3. Maintain any subtitle formatting (like italics) if present, and do not translate proper nouns unless customary.\n"
            f"4. Respond ONLY with a valid JSON array of strings, keeping the exact same order and number of lines. "
            f"Example: [\"line 1\", \"line 2\"].\n"
            f"Do NOT include conversational text, markdown blocks, or explanations."
        )
        
        messages = [
            {"role": "user", "content": f"{system_instruction}\n\nLines to translate:\n{numbered_input}"}
        ]
        
        from llama_cpp import LlamaGrammar
        
        # GBNF Grammar to force a JSON array of strings: ["a", "b", "c"]
        json_grammar = r"""
        root   ::= "[" space (string (space "," space string)*)? space "]"
        string ::= "\"" ([^"\\\n] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
        space  ::= [ \t\n\r]*
        """
        grammar = LlamaGrammar.from_string(json_grammar)

        kwargs = {
            "messages": messages,
            "max_tokens": self.n_ctx,
            "temperature": 0.1,
            "grammar": grammar
        }

        if getattr(self, "disable_reasoning", True) and getattr(self, "supports_reasoning_disable", False):
            try:
                import inspect
                sig = inspect.signature(self.model.create_chat_completion)
                if "chat_template_kwargs" in sig.parameters:
                    kwargs["chat_template_kwargs"] = {"enable_thinking": False}
            except Exception:
                pass

        output = self.model.create_chat_completion(**kwargs)
        
        # Raw response from the assistant
        raw_response = output["choices"][0]["message"]["content"].strip()
        
        if getattr(self, "disable_reasoning", True):
            import re
            raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
        
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

    def clean_batch(self, texts: List[str]) -> List[str]:
        if not self.model:
            raise RuntimeError("Llama model not loaded")

        numbered_input = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        system_instruction = (
            "You are an AI subtitle cleaner. Your task is to remove spam, ads, and credits from subtitles.\n"
            "If a line is purely an ad or credit, replace it with an empty string.\n"
            "Otherwise, return the line exactly as is.\n"
            "Respond ONLY with a valid JSON array of strings, keeping the exact same order and number of lines.\n"
            "Example: [\"hello\", \"\", \"world\"]."
        )
        
        messages = [
            {"role": "user", "content": f"{system_instruction}\n\nLines to clean:\n{numbered_input}"}
        ]
        
        from llama_cpp import LlamaGrammar
        json_grammar = r"""
        root   ::= "[" space (string (space "," space string)*)? space "]"
        string ::= "\"" ([^"\\\n] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
        space  ::= [ \t\n\r]*
        """
        grammar = LlamaGrammar.from_string(json_grammar)

        kwargs = {
            "messages": messages,
            "max_tokens": self.n_ctx,
            "temperature": 0.1,
            "grammar": grammar
        }

        if getattr(self, "disable_reasoning", True) and getattr(self, "supports_reasoning_disable", False):
            try:
                import inspect
                sig = inspect.signature(self.model.create_chat_completion)
                if "chat_template_kwargs" in sig.parameters:
                    kwargs["chat_template_kwargs"] = {"enable_thinking": False}
            except Exception:
                pass

        output = self.model.create_chat_completion(**kwargs)
        
        raw_response = output["choices"][0]["message"]["content"].strip()
        
        if getattr(self, "disable_reasoning", True):
            import re
            raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
            
        fixed_response = raw_response.strip()
        if fixed_response.startswith('```json'):
            fixed_response = fixed_response[7:].strip()
        if fixed_response.endswith('```'):
            fixed_response = fixed_response[:-3].strip()

        try:
            cleaned = json.loads(fixed_response)
            if not isinstance(cleaned, list):
                cleaned = []
        except Exception as e:
            print(f"[Native Llama] JSON Parse Error in clean_batch: {e}")
            import re
            matches = re.finditer(r'"((?:[^"\\]|\\.)*)"', raw_response)
            cleaned = [m.group(1) for m in matches]
            
        final_cleaned = []
        for i in range(len(texts)):
            if i < len(cleaned):
                t = str(cleaned[i])
                t = t.replace('\\"', '"').replace('\\\\', '\\')
                final_cleaned.append(t)
            else:
                final_cleaned.append(texts[i])
                
        return final_cleaned

# Singleton instance
llama_service = NativeLlamaService()

def native_llama_translate(input_srt_path: str, output_srt_path: str, target_lang: str, source_lang: str = "en", model_path: str = None, cancel_check = None, progress_callback = None, disable_reasoning: bool = True, spec_draft_n_max: int = 0):
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
        
    import subprocess
    import sys
    import threading
    import queue
    import time
    import json
    
    # Resolve llama_params from available_models.json
    llama_params_json = "{}"
    try:
        models_file = Path(__file__).parent.parent / "data" / "available_models.json"
        if models_file.exists():
            with open(models_file, "r", encoding="utf-8") as f:
                models_data = json.load(f)
                filename = os.path.basename(model_path)
                for llm in models_data.get("llm_models", []):
                    if llm.get("file") == filename and "llama_params" in llm:
                        llama_params_json = json.dumps(llm["llama_params"])
                        print(f"[Native Llama] Found optimal parameters for {filename}: {llama_params_json}")
                        break
            # Convert json back to dict to inject disable_reasoning, then back to json
            try:
                params_dict = json.loads(llama_params_json)
                params_dict["disable_reasoning"] = disable_reasoning
                params_dict["spec_draft_n_max"] = spec_draft_n_max
                llama_params_json = json.dumps(params_dict)
            except Exception:
                llama_params_json = json.dumps({"disable_reasoning": disable_reasoning, "spec_draft_n_max": spec_draft_n_max})
        else:
            llama_params_json = json.dumps({"disable_reasoning": disable_reasoning, "spec_draft_n_max": spec_draft_n_max})
    except Exception as e:
        print(f"[Native Llama] Warning: Could not read available_models.json: {e}")
        llama_params_json = json.dumps({"disable_reasoning": disable_reasoning, "spec_draft_n_max": spec_draft_n_max})

    script_path = os.path.join(os.path.dirname(__file__), "_llama_subprocess.py")
    
    cmd = [sys.executable, script_path, input_srt_path, output_srt_path, target_lang, source_lang, model_path, llama_params_json]
    print(f"[Native Llama] Launching isolated subprocess for translation to prevent ROCm conflicts...")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    q = queue.Queue()
    def enqueue_output(out, q):
        for line in iter(out.readline, ''):
            q.put(line)
        out.close()
        
    t = threading.Thread(target=enqueue_output, args=(process.stdout, q))
    t.daemon = True
    t.start()
    
    try:
        while process.poll() is None or not q.empty():
            if cancel_check and cancel_check():
                process.terminate()
                raise InterruptedError("Cancelled by user")
                
            try:
                line = q.get(timeout=0.2)
            except queue.Empty:
                continue
                
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("PROGRESS:"):
                try:
                    parts = line.split("PROGRESS:")[1].split("/")
                    processed = int(parts[0])
                    total = int(parts[1])
                    if progress_callback and total > 0:
                        progress_callback(processed / total)
                except Exception:
                    pass
            elif line == "DONE":
                pass
            else:
                print(f"[Llama Subprocess] {line}")
                
        if process.returncode != 0:
            raise RuntimeError(f"Llama translation subprocess failed with exit code {process.returncode}")
            
    finally:
        if process.poll() is None:
            process.terminate()
            
    print(f"Saved Native Llama translated subtitle to {output_srt_path}")
