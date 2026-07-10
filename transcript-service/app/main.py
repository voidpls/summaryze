import asyncio
import os
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import (
    AgeRestricted,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeRequestFailed,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
load_dotenv()

class ServiceHealth(BaseModel):
    service: str
    status: str

class TranscriptRequest(BaseModel):
    youtube_id: str

class TranscriptResponse(BaseModel):
    youtube_id: str
    transcript: str

app = FastAPI()
ytt_formatter = TextFormatter()

use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
proxy_user = os.getenv("PROXY_USER")
proxy_pass = os.getenv("PROXY_PASS")

def make_api(with_proxy: bool) -> YouTubeTranscriptApi:
    if with_proxy:
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=proxy_user,
                proxy_password=proxy_pass,
                filter_ip_locations=["us"],
                retries_when_blocked=3,
            )
        )
    return YouTubeTranscriptApi()

primary = make_api(with_proxy=use_proxy)
fallback = make_api(with_proxy=not use_proxy) if (proxy_user and proxy_pass) else None

PERMANENT = (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    InvalidVideoId,
    AgeRestricted,
    VideoUnplayable,
)
TRANSIENT = (RequestBlocked, IpBlocked, YouTubeRequestFailed)

def fetch_sync(youtube_id: str) -> str:
    clients = [primary] + ([fallback] if fallback is not None else [])
    last_err = None
    for client_idx, client in enumerate(clients):
        attempts = 3 if client_idx == 0 else 1
        for attempt in range(attempts):
            try:
                fetched = client.fetch(youtube_id)
                return ytt_formatter.format_transcript(fetched)
            except PERMANENT:
                raise
            except TRANSIENT as e:
                last_err = e
                if attempt < attempts - 1:
                    time.sleep(0.5 * (2 ** attempt))
            except Exception as e:
                last_err = e
                if attempt < attempts - 1:
                    time.sleep(0.5 * (2 ** attempt))
    raise last_err

@app.get("/health", response_model=ServiceHealth)
async def get_health():
    return ServiceHealth(service="transcript-service", status="healthy")

@app.post("/fetchTranscript", response_model=TranscriptResponse)
async def fetch_transcript(request: TranscriptRequest):
    try:
        text = await asyncio.to_thread(fetch_sync, request.youtube_id)
        return TranscriptResponse(youtube_id=request.youtube_id, transcript=text)
    except PERMANENT as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=502, detail="Failed to fetch transcript for YouTube video")
