import os, time, tempfile, logging, httpx
from fetcher.candidates import needs_fetch
from fetcher.cobalt import download_video, CobaltError
from fetcher.karakeep import KarakeepClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("video-fetcher")
FETCHED, FAILED = "video-fetched", "fetch-failed"

def process(bm, kk, download_fn):
    """Process one bookmark: download, upload, attach, sentinel-tag.

    download_fn(url, path) — callable matching download_video's (url, path) signature.
    Tag-API failures are guarded: a transient failure logging and swallowed so the
    bookmark keeps its correct sentinel rather than looping forever.
    """
    bid = bm["id"]; url = bm["content"]["url"]
    log.info("fetching %s for bookmark %s", url, bid)
    with tempfile.TemporaryDirectory() as d:
        path = f"{d}/video.mp4"
        try:
            download_fn(url, path)
        except (CobaltError, httpx.HTTPError) as e:
            log.error("download failed for %s: %s", bid, e)
            try:
                kk.add_tag(bid, FAILED)
            except httpx.HTTPError as te:
                log.error("failed to set %s sentinel for %s: %s", FAILED, bid, te)
            return
        try:
            aid = kk.upload_asset(path, "video/mp4")
            kk.attach_asset(bid, aid)
            log.info("attached video asset %s to %s", aid, bid)
        except httpx.HTTPError as e:
            log.error("attach failed for %s: %s", bid, e)  # leave un-sentineled -> retried next poll
            return
        try:
            kk.add_tag(bid, FETCHED)
        except httpx.HTTPError as te:
            log.error("failed to set %s sentinel for %s: %s", FETCHED, bid, te)

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
                    download_fn = lambda url, path: download_video(hclient, cobalt_base, cobalt_key, url, path)
                    process(bm, kk, download_fn)
        except Exception as e:
            log.error("poll error: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    main()
