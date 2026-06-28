import os
import subprocess


class YtdlpError(Exception):
    ...


def download_video_ytdlp(url: str, dest_path: str, *, runner=subprocess.run) -> str:
    """Download a video to dest_path with yt-dlp.

    Fallback downloader for sources Cobalt's extractors can't handle (e.g. TikTok).
    Prefers a single progressive MP4; merges to MP4 if needed (requires ffmpeg).

    If YTDLP_COOKIES points at an existing cookies.txt (Netscape format), it is
    passed via --cookies. This is how Instagram becomes reliable — anonymous access
    gets login-walled/rate-limited from a datacenter IP. Optional: with no cookies
    file, anonymous download is still attempted.
    """
    cmd = [
        "yt-dlp", "-q", "--no-warnings", "--no-playlist", "--no-part",
        "-f", "mp4/bestvideo*+bestaudio/best",
        "--merge-output-format", "mp4",
    ]
    cookies = os.environ.get("YTDLP_COOKIES")
    if cookies and os.path.isfile(cookies):
        cmd += ["--cookies", cookies]
    cmd += ["-o", dest_path, url]
    proc = runner(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise YtdlpError(f"yt-dlp failed ({proc.returncode}): {(proc.stderr or '')[-300:]}")
    return dest_path
