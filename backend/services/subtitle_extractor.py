import ffmpeg
import os

def extract_subtitle(video_path: str, output_srt_path: str, track_index: int):
    try:
        stream = ffmpeg.input(video_path)
        # Select the specific absolute track index
        stream = stream[str(track_index)]
        # Extract as SRT
        stream = ffmpeg.output(stream, output_srt_path, f='srt')
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
    except ffmpeg.Error as e:
        print(f"Failed to extract subtitle: {e.stderr.decode('utf8') if e.stderr else str(e)}")
        raise RuntimeError(f"Subtitle extraction failed for {video_path}")
