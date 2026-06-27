"""Tests for the process() orchestration in fetcher.main."""
import httpx
import pytest
from unittest.mock import MagicMock, call

from fetcher.main import process, FETCHED, FAILED
from fetcher.cobalt import CobaltError


def _bm(bid="B1", url="https://tiktok.com/@x/video/1"):
    return {"id": bid, "content": {"url": url}}


def test_process_download_fails_sets_failed_sentinel():
    """CobaltError during download -> add_tag(FAILED) called; upload/attach are NOT."""
    kk = MagicMock()
    download_fn = MagicMock(side_effect=CobaltError("cobalt error"))

    process(_bm(), kk, download_fn)

    kk.add_tag.assert_called_once_with("B1", FAILED)
    kk.upload_asset.assert_not_called()
    kk.attach_asset.assert_not_called()


def test_process_success_sets_fetched_sentinel():
    """Download + upload + attach all succeed -> add_tag(FETCHED) called."""
    kk = MagicMock()
    kk.upload_asset.return_value = "A1"
    download_fn = MagicMock()

    process(_bm(), kk, download_fn)

    kk.upload_asset.assert_called_once()
    kk.attach_asset.assert_called_once_with("B1", "A1")
    kk.add_tag.assert_called_once_with("B1", FETCHED)


def test_process_attach_fails_sets_no_sentinel():
    """Download succeeds but attach_asset raises -> no sentinel tag set (retried next poll)."""
    kk = MagicMock()
    kk.upload_asset.return_value = "A1"
    kk.attach_asset.side_effect = httpx.HTTPError("network error")
    download_fn = MagicMock()

    process(_bm(), kk, download_fn)

    kk.upload_asset.assert_called_once()
    kk.attach_asset.assert_called_once_with("B1", "A1")
    kk.add_tag.assert_not_called()
