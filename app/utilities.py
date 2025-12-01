import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from youtube_transcript_api import YouTubeTranscriptApi

# Caption cache configuration
CACHE_DIR = Path(__file__).parent / ".caption_cache"
CACHE_TTL_DAYS = 30

logger = logging.getLogger(__name__)



def extract_video_id(url) -> str | None:
    pattern = r"(?:youtube\.com\/watch\?v=)([^&\n?#]+)"
    if match := re.search(pattern, url):
        return match.group(1)
    else:
        return None
    

def fetch_transcript(video_id: str, languages: list[str] | None = None):
    """Fetch transcript from YouTube (blocking I/O)."""
    if languages is None:
        languages = ["en"]
    api = YouTubeTranscriptApi()
    return api.fetch(video_id, languages)


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


def parse_timestamp_to_seconds(timestamp: str) -> int | None:
    """Parse a timestamp string (e.g., '5:30', '1:05:30', '00:05:30') to seconds."""
    if not timestamp:
        return None
    
    # Remove any leading/trailing whitespace
    timestamp = timestamp.strip()
    
    # Split by colon
    parts = timestamp.split(':')
    
    try:
        if len(parts) == 2:
            # MM:SS format
            minutes, seconds = int(parts[0]), int(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            # HH:MM:SS format
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        else:
            return None
    except ValueError:
        return None


def _cache_path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.json"


def get_cached_captions(video_id: str) -> str | None:
    """Retrieve cached captions if they exist and aren't expired."""
    cache_file = _cache_path(video_id)

    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["cached_at"])

        if datetime.now() - cached_at > timedelta(days=CACHE_TTL_DAYS):
            logger.info(f"Cache expired for video {video_id}")
            cache_file.unlink()
            return None

        logger.info(f"Cache hit for video {video_id}")
        return data["captions"]

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Invalid cache file for {video_id}: {e}")
        cache_file.unlink(missing_ok=True)
        return None


def cache_captions(video_id: str, captions: str) -> None:
    """Store captions in the cache."""
    CACHE_DIR.mkdir(exist_ok=True)

    data = {
        "video_id": video_id,
        "captions": captions,
        "cached_at": datetime.now().isoformat(),
    }

    _cache_path(video_id).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Cached captions for video {video_id}")

    
    

