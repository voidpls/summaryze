import os
import re
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict

# models
class ServiceHealth(BaseModel):
    service: str
    status: str

# text input model
class TextRequest(BaseModel):
    text: str

# youtube link input model
class YoutubeRequest(BaseModel):
    url: HttpUrl
    # youtube link validator
    @validator('url')
    def validate_youtube_url(cls, v):
        url_str = str(v)
        if "youtube.com" not in url_str and "youtu.be" not in url_str:
            raise ValueError('Must be a valid YouTube URL')
        return v
    
# summary response model
class SummaryResponse(BaseModel):
    source_type: str # 'text' or 'youtube'
    source_id: str # hash for text, video_id for youtube
    summary: str

app = FastAPI()

# LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
TRANSCRIPT_SERVICE_URL = os.getenv("TRANSCRIPT_SERVICE_URL")

# Endpoints
@app.get("/health", response_model=ServiceHealth)
async def get_health():
    return ServiceHealth(service="api-service", status="healthy")

@app.post("/summarize/text", response_model=SummaryResponse)
async def summarize_text(request: TextRequest):    
    # source_id: create a hash from text
    text_id = str(hash(request.text))
    
    # TODO: check cache => llm api for summary

    return SummaryResponse(
        source_type="text",
        source_id=text_id,
        summary=f"[summary placeholder]"
    )

@app.post("/summarize/youtube", response_model=SummaryResponse)
async def summarize_youtube(request: YoutubeRequest):
    # source_id: extract youtube video id
    video_url = str(request.url)
    video_id = extract_video_id(video_url)
    
    # TODO: check cache => transcript api => llm api for summary
    

    return SummaryResponse(
        source_type="youtube",
        source_id=video_id,
        summary=f"[summary placeholder]"
    )


def extract_video_id(url: str) -> str:
    """
    Extracts video ID from:
        1. https://www.youtube.com/watch?v=VIDEO_ID
        2. https://youtu.be/VIDEO_ID
        3. https://www.youtube.com/shorts/VIDEO_ID
    """
    # regex for standard youtube pattern
    regex = r'(?:v=|shorts\/|\/)([0-9A-Za-z_-]{11})'
    match = re.search(regex, url)
    
    if match:
        return match.group(1)
    raise HTTPException(status_code=400, detail="Could not extract video ID from URL")
