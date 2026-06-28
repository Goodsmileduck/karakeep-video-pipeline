FROM python:3.12-slim
# ffmpeg: lets the yt-dlp fallback merge video+audio into mp4 when needed
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fetcher ./fetcher
CMD ["python", "-m", "fetcher.main"]
