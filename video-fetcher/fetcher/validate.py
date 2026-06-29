import json
import subprocess


class NotAVideoError(Exception):
    ...


def ensure_video(path: str, *, runner=subprocess.run) -> str:
    """Return `path` iff it holds a real, timed video stream; else raise NotAVideoError.

    Cobalt occasionally answers an Instagram reel with status:tunnel but serves the
    post's cover JPEG (IG won't serve the video stream anonymously). That file probes
    as a single still-image "video" stream (mjpeg) with no audio and no duration.
    We require a video stream AND either an audio track or a positive duration, so a
    bare cover image is rejected and download_with_fallback can try yt-dlp instead.
    """
    try:
        proc = runner(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as e:  # ffprobe missing / timeout / OS error
        raise NotAVideoError(f"ffprobe could not run on {path}: {e}")
    if proc.returncode != 0:
        raise NotAVideoError(f"ffprobe rc={proc.returncode}: {(proc.stderr or '').strip()[-200:]}")
    try:
        data = json.loads(proc.stdout or "{}")
    except ValueError as e:
        raise NotAVideoError(f"ffprobe gave unparseable output for {path}: {e}")

    streams = data.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    try:
        duration = float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        duration = 0.0

    if not has_video:
        raise NotAVideoError(f"{path}: no video stream")
    if not has_audio and duration < 0.2:
        raise NotAVideoError(
            f"{path}: looks like a still image (no audio, duration={duration})"
        )
    return path
