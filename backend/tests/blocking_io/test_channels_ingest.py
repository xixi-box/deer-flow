"""Regression anchor: ingesting inbound channel files must not block the event loop.

``ChannelManager``'s ``_ingest_inbound_files`` ensures the thread uploads
directory (``mkdir``), enumerates it (``iterdir`` / ``is_file``) to de-duplicate
filenames, and writes each downloaded attachment to disk
(``write_upload_file_no_symlink``) — all blocking filesystem IO. The async
function offloads the directory prep and every per-file write via
``asyncio.to_thread`` while keeping the genuinely async network read
(``file_reader``) on the loop. If any of that regresses back onto the event
loop, the strict Blockbuster gate raises ``BlockingError`` and this test fails.

Imports are kept at module top so any import-time IO runs at collection (outside
the gate); the surface under test runs on the event loop inside the gated test.
"""

from __future__ import annotations

import asyncio
import ssl
import threading
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from slack_sdk import WebClient

from app.channels import manager as mgr
from app.channels.discord import DiscordChannel
from app.channels.message_bus import INBOUND_FILE_CONTENT_KEY, InboundMessage, MessageBus
from app.channels.slack import SlackChannel
from deerflow.uploads.manager import get_uploads_dir

pytestmark = pytest.mark.asyncio


async def test_ingest_inbound_files_does_not_block_event_loop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEER_FLOW_HOME", str(tmp_path))
    # Rebuild the cached Paths against the tmp home so uploads resolve under it.
    import deerflow.config.paths as paths_mod

    monkeypatch.setattr(paths_mod, "_paths", None)

    # Swap the network reader for an in-memory one: no real HTTP, so the only IO
    # left for this anchor to guard is the filesystem work.
    async def _fake_reader(f, client):
        return b"payload-bytes"

    monkeypatch.setattr(mgr, "_read_http_inbound_file", _fake_reader)

    msg = InboundMessage(
        channel_name="unit-test-channel",  # absent from INBOUND_FILE_READERS -> default reader
        chat_id="c1",
        user_id="u1",
        text="hi",
        files=[{"type": "file", "filename": "report.txt"}],
    )

    created = await mgr._ingest_inbound_files("t1", msg)

    assert len(created) == 1
    assert created[0]["filename"] == "report.txt"
    written = await asyncio.to_thread(lambda: (get_uploads_dir("t1") / "report.txt").exists())
    assert written, "inbound file should be written under the tmp uploads dir"


@pytest.mark.parametrize("provider", ["slack", "discord"])
async def test_attachment_tls_loads_off_event_loop(provider: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bus = MessageBus()
    if provider == "slack":
        url = "https://files.slack.com/files-pri/T-F/download/report.txt"
        channel = SlackChannel(bus, {"bot_token": "test-token"})
        channel._web_client = WebClient(token="test-token")
        files = channel._extract_inbound_files({"files": [{"name": "report.txt", "size": 4, "url_private_download": url}]})
        authorization = "Bearer test-token"
    else:
        url = "https://cdn.discordapp.com/attachments/1/2/report.txt"
        channel = DiscordChannel(bus, {"bot_token": "test-token", "channel_store": SimpleNamespace(channels_dir=tmp_path)})
        files = channel._extract_inbound_files(SimpleNamespace(attachments=[SimpleNamespace(filename="report.txt", size=4, url=url)]))
        authorization = "Bot test-token"
    msg = channel._make_inbound("chat", "sender", "caption", files=files)

    monkeypatch.setenv("no_proxy", "*")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    loop_thread = threading.get_ident()
    certificate_threads: list[int] = []
    requests: list[httpx.Request] = []
    load_verify_locations = ssl.SSLContext.load_verify_locations

    def record_load(context, *args, **kwargs):
        certificate_threads.append(threading.get_ident())
        return load_verify_locations(context, *args, **kwargs)

    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"da"
            yield b"ta"

    async def respond(transport, request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, stream=Body())

    monkeypatch.setattr(ssl.SSLContext, "load_verify_locations", record_load)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", respond)

    result = await channel.receive_file(msg, "thread")

    assert result.text == "caption"
    assert result.files == [{"type": "file", "filename": "report.txt", "mime_type": "application/octet-stream", "size": 4, INBOUND_FILE_CONTENT_KEY: b"data"}]
    (request,) = requests
    assert (request.method, str(request.url)) == ("GET", url)
    assert request.headers["Authorization"] == authorization
    assert request.headers["Accept-Encoding"] == "identity"
    assert certificate_threads, "The real HTTPX TLS initialization must run"
    assert loop_thread not in certificate_threads, "Attachment TLS certificates loaded on the event-loop thread"
