# Karakeep Video Pipeline

A self-contained stack that lets you send an **Instagram / YouTube / TikTok link** to
a Telegram bot and have the video **saved into Karakeep and auto-categorized by its
spoken content** (audio transcription → tags).

> **Network assumption:** this reference assumes a *normal* internet connection — the
> host can reach Instagram, YouTube, and `api.telegram.org` directly. If your server
> is in a region that blocks those, the IG/Telegram-facing services must run somewhere
> that isn't (out of scope here).

## What's in the box (`docker-compose.yml`)
| Service | Role |
|---------|------|
| `karakeep`, `chrome`, `meilisearch` | The Karakeep bookmark app + crawler + search |
| `ollama` | Local LLM inference (tagging). GPU is host-specific — see compose notes |
| `cobalt` | Primary downloader (no account/cookies for public content); internal-only, API-key protected |
| `video-fetcher` | Polls Karakeep for video links → **Cobalt, falling back to yt-dlp** → attaches the video to the bookmark |
| `video-tagger` | Polls for bookmarks with a video → faster-whisper transcript → llama3.2 tags → writes back |
| `karakeepbot` | The Telegram bot that turns your messages into bookmarks |

Two sentinel tags drive idempotency: `video-fetched` / `fetch-failed` (fetcher) and
`transcribed` (tagger). Music-only/visual reels are marked done with no junk tags.

## Setup
```bash
cp .env.example .env                 # fill NEXTAUTH_SECRET, MEILI_MASTER_KEY (openssl rand -base64 36)

# 1) Cobalt API key
mkdir -p cobalt
KEY=$(cat /proc/sys/kernel/random/uuid)
printf '{\n  "%s": { "name": "video-fetcher", "limit": 1000 }\n}\n' "$KEY" > cobalt/keys.json
echo "COBALT_API_KEY=$KEY"           # paste this into .env

# 2) Telegram: create a bot via @BotFather -> TELEGRAM_BOT_TOKEN;
#    get your numeric id from @userinfobot -> TELEGRAM_ALLOWLIST

# 3) Bring up the core, create your account + API key
docker compose up -d karakeep
#    open http://localhost:3000 -> sign up -> Settings -> API Keys -> create
#    put it in .env as KARAKEEP_TOKEN

# 4) Pull the models, then start everything
docker compose up -d ollama
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull gemma4:26b   # image tagging (optional, large)
docker compose up -d
```

## Use
Send a public Instagram/TikTok/YouTube link to your bot. Within a poll cycle (~45 s)
the reel is downloaded and attached to a Karakeep bookmark; shortly after, its audio is
transcribed and topical tags appear. Check `docker compose logs -f video-fetcher
video-tagger`.

## Notes
- **Downloaders:** Cobalt is tried first (great for Instagram, no account needed); if it
  can't extract a URL the fetcher **falls back to yt-dlp** (which handles TikTok,
  YouTube, and 1800+ sites). Cobalt is reachable only inside the compose network (no
  published port) and requires `Authorization: Api-Key`. Private content still needs
  login and is out of scope.
- **Whisper** uses `small` (CPU/int8) by default — ~7× realtime on a modest box. Set
  `WHISPER_MODEL=base` (faster) or `medium` (more accurate) in `.env`.
- **GPU:** `ollama` runs CPU-only unless you wire up device passthrough (see the compose
  comments). To reuse an existing host Ollama, comment out the `ollama` service and point
  `OLLAMA_API`/`OLLAMA_BASE_URL` at it.
- **Deep tagging is audio-based** — reels with no speech yield no content tags (by design).
