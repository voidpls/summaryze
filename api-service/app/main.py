import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

class ServiceHealth(BaseModel):
    service: str
    status: str

app = FastAPI()

# LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")

# Endpoints
@app.get("/health", response_model=ServiceHealth)
async def get_health():
    # async with httpx.AsyncClient() as client:
    #         res = await client.get(f"{LLM_SERVICE_URL}/health")

    return ServiceHealth(service="api-service", status="healthy")
