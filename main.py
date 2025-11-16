import os
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Attendance, Umkm

app = FastAPI(title="UMKM & Attendance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "UMKM & Attendance API is running"}

# --- Attendance Endpoints ---
class AttendanceIn(BaseModel):
    name: str

@app.post("/api/attendance", response_model=dict)
async def mark_attendance(payload: AttendanceIn):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    # Server-side timestamp in ISO format
    timestamp = datetime.now(timezone.utc).isoformat()

    data = Attendance(name=payload.name.strip(), timestamp=timestamp)
    inserted_id = create_document("attendance", data)
    return {"id": inserted_id, "name": data.name, "timestamp": data.timestamp}

@app.get("/api/attendance", response_model=List[dict])
async def list_attendance():
    docs = get_documents("attendance", {})
    # Normalize output (convert ObjectId & timestamps)
    normalized = []
    for d in docs:
        normalized.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "timestamp": d.get("timestamp") or (d.get("created_at") and d.get("created_at").isoformat()),
        })
    # Sort by timestamp descending
    normalized.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return normalized

# --- UMKM Endpoints ---
class UmkmIn(BaseModel):
    name: str
    contact: str
    description: str
    social: str | None = None

@app.post("/api/umkm", response_model=dict)
async def register_umkm(payload: UmkmIn):
    if not payload.name.strip() or not payload.contact.strip() or not payload.description.strip():
        raise HTTPException(status_code=400, detail="Name, contact, and description are required")

    data = Umkm(
        name=payload.name.strip(),
        contact=payload.contact.strip(),
        description=payload.description.strip(),
        social=(payload.social.strip() if payload.social else None),
    )
    inserted_id = create_document("umkm", data)
    return {"id": inserted_id, **data.model_dump()}

@app.get("/api/umkm", response_model=List[dict])
async def list_umkm():
    docs = get_documents("umkm", {})
    out = []
    for d in docs:
        out.append({
            "id": str(d.get("_id")),
            "name": d.get("name"),
            "contact": d.get("contact"),
            "description": d.get("description"),
            "social": d.get("social"),
        })
    # Sort alphabetically by name
    out.sort(key=lambda x: (x.get("name") or "").lower())
    return out

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db as _db

        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
