import os, time, tempfile, logging, httpx
from tagger.logic import needs_tagging, video_asset_id, is_empty_transcript
from tagger.transcribe import transcribe
from tagger.ollama import tags_from_transcript
from tagger.karakeep import KarakeepClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("video-tagger")
DONE = "transcribed"

def process(bm, kk, oclient, obase, omodel, *, _transcribe_fn=None, _tag_fn=None):
    bid = bm["id"]; aid = video_asset_id(bm)
    if not aid: return
    with tempfile.TemporaryDirectory() as d:
        vid = kk.get_asset_bytes(aid, f"{d}/v.mp4")
        try:
            if _transcribe_fn is not None:
                text = _transcribe_fn(vid)
            else:
                text = transcribe(vid, workdir=d)
        except Exception as e:
            log.error("transcribe failed %s: %s", bid, e)
            try:
                kk.add_tag(bid, DONE)
            except Exception as se:
                log.error("sentinel failed after transcribe error %s: %s", bid, se)
            return
        if is_empty_transcript(text):
            log.info("no speech in %s; marking done", bid)
            try:
                kk.add_tag(bid, DONE)
            except Exception as se:
                log.error("sentinel failed for no-speech %s: %s", bid, se)
            return
        if _tag_fn is not None:
            tags = _tag_fn(text)
        else:
            tags = tags_from_transcript(oclient, obase, omodel, text)
        kk.add_tags(bid, tags)  # propagates on failure; retry is safe (tags not yet added)
        try:
            kk.set_note(bid, ("Transcript:\n" + text)[:8000])
        except Exception as e:
            log.warning("set_note failed %s (non-fatal): %s", bid, e)
        try:
            kk.add_tag(bid, DONE)
        except Exception as e:
            log.error("sentinel failed %s: %s", bid, e)
        log.info("tagged %s with %d tags", bid, len(tags))

def main():
    kk = KarakeepClient(os.environ["KARAKEEP_API"], os.environ["KARAKEEP_TOKEN"])
    obase = os.environ.get("OLLAMA_API","http://ollama:11434"); omodel = os.environ.get("TAG_MODEL","llama3.2")
    interval = int(os.environ.get("POLL_INTERVAL_SEC","45"))
    oclient = httpx.Client()
    log.info("video-tagger up; polling every %ss", interval)
    while True:
        try:
            for bm in kk.list_recent():
                if needs_tagging(bm, DONE):
                    try:
                        process(bm, kk, oclient, obase, omodel)   # serial: one at a time
                    except Exception as e:
                        log.error("process failed bm=%s: %s", bm.get("id"), e)
        except Exception as e:
            log.error("poll error: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    main()
