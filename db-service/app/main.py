import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pydantic import BaseModel

# set up postgres connection
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session

# models
class ServiceHealth(BaseModel):
    service: str
    status: str
# input and response model
class CacheEntry(SQLModel, table=True):
    id: str = Field(primary_key=True)  # primary key, hash or video ID
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow) # set date automatically
# update model for patch
class CacheEntryUpdate(BaseModel):
    summary: Optional[str] = None
    created_at: Optional[datetime] = None

app = FastAPI()

# create tables on start
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


# Endpoints
@app.get("/health", response_model=ServiceHealth)
async def get_health():
    return ServiceHealth(service="db-service", status="healthy")

# POST: Create entry 
@app.post("/entries/", response_model=CacheEntry)
def create_entry(entry: CacheEntry, session: Session = Depends(get_session)):
    # check if exists, only continue if doesn't
    existing = session.get(CacheEntry, entry.id)
    if existing:
        raise HTTPException(status_code=400, detail="Entry with this ID already exists")
    
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

# GET: Retrieve entry
@app.get("/entries/{entry_id}", response_model=CacheEntry)
def read_entry(entry_id: str, session: Session = Depends(get_session)):
    entry = session.get(CacheEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry

# PATCH: Update entry (summary field, most likely)
@app.patch("/entries/{entry_id}", response_model=CacheEntry)
def update_entry(entry_id: str, entry_update: CacheEntryUpdate, session: Session = Depends(get_session)):
    db_entry = session.get(CacheEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    entry_data = entry_update.dict(exclude_unset=True)
    for key, value in entry_data.items():
        setattr(db_entry, key, value)
        
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

# DELETE: Remove an entry
@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: str, session: Session = Depends(get_session)):
    entry = session.get(CacheEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    session.delete(entry)
    session.commit()
    return {"ok": True}