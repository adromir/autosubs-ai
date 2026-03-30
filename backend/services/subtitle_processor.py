import os
import re
import textwrap
from pathlib import Path
from typing import List

def word_safe_wrap(text: str, width: int = 42) -> str:
    """
    Wraps text into multiple lines, ensuring no line exceeds width.
    Never breaks words; only splits at spaces.
    """
    if not text or len(text) <= width:
        return text
    
    # textwrap.wrap handles the heavy lifting of word-safe wrapping
    lines = textwrap.wrap(
        text, 
        width=width, 
        break_long_words=False, 
        replace_whitespace=False,
        drop_whitespace=True
    )
    return "\n".join(lines)

def refine_subtitle_content(content: str, deep_cleanup: bool = True) -> str:
    """
    Performs deep cleaning and formatting on SRT content strings.
    """
    if not content:
        return ""

    # 1. Standardize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Pattern-based cleaning (Ads, Metadata, Hallucinations)
    if deep_cleanup:
        # Remove common provider ads and watermarks
        ad_patterns = [
            r"(?i)Downloaded from.*",
            r"(?i)Subtitles by.*",
            r"(?i)Support us and become VIP.*",
            r"(?i)OpenSubtitles.*",
            r"(?i)Addic7ed.*",
            r"(?i)SubtitleHub.*",
            r"(?i)Promo code.*",
            r"(?i)Advertise your product.*",
            r"(?i)Follow us on.*",
            r"(?i)Corrected by.*",
            r"(?i)Resynced by.*"
        ]
        for pattern in ad_patterns:
            content = re.sub(pattern, "", content)

        # Remove AI noise markers
        noise_markers = [
            r"\[.*?\]",  # [MUSIC], [BIRD CHIRPING]
            r"\(.*?\)",  # (Laughter), (Sighs)
            r"♪.*?♪",     # Musical notes
            r"¶.*",       # Whisper hallucinations
        ]
        for pattern in noise_markers:
            content = re.sub(pattern, "", content)

    # 3. Process SRT blocks for line wrapping
    # An SRT block is typically: index \n timestamps \n text... \n\n
    blocks = re.split(r"(\n\n+)", content)
    refined_blocks = []

    for block in blocks:
        if not block.strip() or " --> " not in block:
            refined_blocks.append(block)
            continue
        
        lines = block.split("\n")
        if len(lines) < 3:
            refined_blocks.append(block)
            continue
            
        header = lines[:2] # Index and Timestamps
        text_lines = lines[2:] # The actual dialogue
        
        # Combine dialogue lines to re-wrap them properly
        full_text = " ".join([l.strip() for l in text_lines if l.strip()])
        wrapped_text = word_safe_wrap(full_text, width=42)
        
        refined_blocks.append("\n".join(header + [wrapped_text]))

    return "".join(refined_blocks)

def sanitize_and_refine(filepath: str, deep_cleanup: bool = True):
    """
    Loads, refines, and saves an SRT file with UTF-8 encoding.
    """
    try:
        import charset_normalizer
        
        if not os.path.exists(filepath):
            return

        with open(filepath, 'rb') as f:
            raw_data = f.read()
            
        if not raw_data:
            return

        # Detect and load
        results = charset_normalizer.from_bytes(raw_data)
        best_match = results.best()
        if best_match:
            content = str(best_match)
        else:
            content = raw_data.decode('utf-8', errors='replace')

        # Refine
        refined = refine_subtitle_content(content, deep_cleanup=deep_cleanup)
        
        # Security: Don't overwrite if we've accidentally wiped everything
        if len(refined.strip()) < 10 and len(content.strip()) > 50:
            print(f"[Processor] Warning: Refusal to save suspiciously empty refinement for {filepath}")
            return

        # Save as clean UTF-8
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(refined)
            
        print(f"[Processor] Refined and sanitized: {os.path.basename(filepath)}")
        
    except Exception as e:
        print(f"[Processor] Error refining {filepath}: {e}")
