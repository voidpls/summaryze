import os

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.proxies import WebshareProxyConfig
from dotenv import load_dotenv
load_dotenv()

# models
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

# Configure proxy
use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
proxy_user = os.getenv("PROXY_USER")
proxy_pass = os.getenv("PROXY_PASS")

if use_proxy:
    print("Proxy enabled")
    proxy_config = WebshareProxyConfig(
        proxy_username=proxy_user,
        proxy_password=proxy_pass,
        filter_ip_locations=["us"]
    )
    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
else:
    print("Proxy disabled")
    ytt_api = YouTubeTranscriptApi()

# Endpoints
@app.get("/health", response_model=ServiceHealth)
async def get_health():
    return ServiceHealth(service="transcript-service", status="healthy")


@app.post("/fetchTranscript", response_model=TranscriptResponse)
async def fetch_transcript(request: TranscriptRequest):
    fetched_transcript = ytt_api.fetch(request.youtube_id)
    text_formatted = ytt_formatter.format_transcript(fetched_transcript)
    return TranscriptResponse(youtube_id=request.youtube_id, transcript=text_formatted)
