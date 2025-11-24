import re
from typing import Iterable



def extract_video_id(url) -> str | None:
    pattern = r"(?:youtube\.com\/watch\?v=)([^&\n?#]+)"
    if match := re.search(pattern, url):
        return match.group(1)
    else:
        return None


def convert_to_text_with_timestamps(transcript: Iterable) -> str:
    """Convert transcript to SRT format"""
    lines = []
    for entry in transcript:
        timestamp = format_timestamp(entry.start)
        text = entry.text
        lines.append(f"[{timestamp}] {text}")

    return "\n".join(lines)


def format_timestamp(seconds: float) -> str:
        """Format seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    
    

