from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

app = FastAPI(title="Geopolitics & War Online")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def maintenance(request: Request):
    # Dữ liệu truyền xuống Frontend
    context = {
        "request": request,
        "status": "SECTOR LOCKDOWN",
        "version": "v2.0.5-PROTOTYPE",
        "eta": "2024-06-30T12:00:00", # Định dạng ISO để JS đọc
        "dev": "thehuy_03",
        "logs": [
            "Initializing deep-layer encryption...",
            "Freezing national assets...",
            "Syncing PostgreSQL clusters...",
            "Deploying Neural-Net defense..."
        ]
    }
    return templates.TemplateResponse("maintenance.html", context)
