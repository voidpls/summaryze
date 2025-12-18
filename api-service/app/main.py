import os
import re
import hashlib
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from bs4 import BeautifulSoup

from pydantic import BaseModel, HttpUrl, validator

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

DB_SERVICE_URL = os.getenv('DB_SERVICE_URL')
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL")
TRANSCRIPT_SERVICE_URL = os.getenv('TRANSCRIPT_SERVICE_URL')

# Endpoints
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/health", response_model=ServiceHealth)
async def get_health():
    return ServiceHealth(service="api-service", status="healthy")

@app.post("/summarize/text", response_model=SummaryResponse)
async def summarize_text(request: TextRequest):    
    # source_id: create a hash from text
    m = hashlib.md5()
    m.update(request.text.encode('utf-8'))
    text_id = m.hexdigest()[0:12] # ex: d6813a4b3abc
    
    cached = await cache_get(text_id)
    if cached is not None:
        return SummaryResponse(
            source_type="text",
            source_id=text_id,
            summary=cached['summary']
        )

    summary = await fetch_summary(text=request.text, type='text')
    await cache_create(text_id, summary)

    return SummaryResponse(
        source_type="text",
        source_id=text_id,
        summary=summary
    )

@app.post("/summarize/youtube", response_model=SummaryResponse)
async def summarize_youtube(request: YoutubeRequest):
    # source_id: extract youtube video id
    youtube_url = str(request.url)
    youtube_id = extract_video_id(youtube_url) # ex: dM2CN-GR4rU
    
    cached = await cache_get(youtube_id)
    if cached is not None:
        return SummaryResponse(
            source_type="youtube",
            source_id=youtube_id,
            summary=cached['summary']
        )
    
    transcript = await fetch_transcript(youtube_id)
    title = await fetch_title(youtube_url)
    
    transcript_with_title = f'(Video Title: {title})\n\n {transcript}'

    summary = await fetch_summary(text=transcript_with_title, type='video')
    await cache_create(youtube_id, summary)

    return SummaryResponse(
        source_type="youtube",
        source_id=youtube_id,
        summary=summary
    )

async def fetch_summary(text, type):
    try: 
        async with httpx.AsyncClient() as client:
            data = {'type': type, 'text': text}
            summarize_endpoint = f'{LLM_SERVICE_URL}/getSummary'
            res = await client.post(summarize_endpoint, json=data)
            res.raise_for_status()
            summary_data = res.json()
            return summary_data['summary']
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to fetch generated summary")


async def fetch_transcript(youtube_id):
    try: 
        async with httpx.AsyncClient() as client:
            data = {'youtube_id': youtube_id}
            transcript_endpoint = f'{TRANSCRIPT_SERVICE_URL}/fetchTranscript'
            res = await client.post(transcript_endpoint, json=data)
            res.raise_for_status()
            transcript_data = res.json()
            transcript = transcript_data['transcript']
            
            return transcript
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to fetch transcript for YouTube video")

async def fetch_title(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, follow_redirects=True)
            soup = BeautifulSoup(res.content, 'html.parser')
            title_tag = soup.find('meta', property='og:title')
            if title_tag and 'content' in title_tag.attrs:
                return title_tag['content']
            else: return ''
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to fetch YouTube video metadata")


async def cache_get(id):
    try:
        async with httpx.AsyncClient() as client:
            endpoint = f'{DB_SERVICE_URL}/entries/{id}'
            res = await client.get(endpoint)
            if res.status_code == 404: 
                return None
            res.raise_for_status()
            return res.json()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to get from cache")

async def cache_create(id, summary):
    try:
        async with httpx.AsyncClient() as client:
            endpoint = f'{DB_SERVICE_URL}/entries/'
            data = {'id': id, 'summary': summary}
            res = await client.post(endpoint, json=data)
            res.raise_for_status()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Failed to create cache entry")

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
