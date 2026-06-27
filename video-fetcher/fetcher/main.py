import os, time, tempfile, logging, httpx
from fetcher.candidates import needs_fetch
from fetcher.cobalt import download_video, CobaltError
from fetcher.karakeep import KarakeepClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("video-fetcher")
FETCHED, FAILED = "video-fetched", "fetch-failed"

def process(bm, kk, cobalt_base, cobalt_key, hclient):
    bid = bm["id"]; url = bm["content"]["url"]
    log.info("fetching %s for bookmark %s", url, bid)
    with tempfile.TemporaryDirectory() as d:
        path = f"{d}/video.mp4"
        try:
            download_video(hclient, cobalt_base, cobalt_key, url, path)
        except (CobaltError, httpx.HTTPError) as e:
            log.error("download failed for %s: %s", bid, e)
            kk.add_tag(bid, FAILED); return
        try:
            aid = kk.upload_asset(path, "video/mp4")
            kk.attach_asset(bid, aid)
            kk.add_tag(bid, FETCHED)
            log.info("attached video asset %s to %s", aid, bid)
        except httpx.HTTPError as e:
            log.error("attach failed for %s: %s", bid, e)  # leave un-sentineled -> retried next poll

def main():
    kk = KarakeepClient(os.environ["KARAKEEP_API"], os.environ["KARAKEEP_TOKEN"])
    cobalt_base = os.environ.get("COBALT_API", "http://cobalt:9000")
    cobalt_key = os.environ["COBALT_API_KEY"]
    interval = int(os.environ.get("POLL_INTERVAL_SEC", "45"))
    hclient = httpx.Client()
    log.info("video-fetcher up; polling every %ss", interval)
    while True:
        try:
            for bm in kk.list_recent():
                if needs_fetch(bm, FETCHED, FAILED):
                    process(bm, kk, cobalt_base, cobalt_key, hclient)
        except Exception as e:
            log.error("poll error: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    main()
