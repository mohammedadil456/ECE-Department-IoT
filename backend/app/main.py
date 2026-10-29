"""ECE SmartLab API — local-first IoT telemetry service."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os, sqlite3
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("SMARTLAB_DB", Path(__file__).resolve().parent.parent / "smartlab.db"))
DEFAULT_DEVICE = "smartlab-node-01"

def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'ESP32 + DHT22', created_at TEXT NOT NULL, last_seen TEXT, online INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS readings(id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, temperature_c REAL NOT NULL, humidity_pct REAL NOT NULL, recorded_at TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'device', FOREIGN KEY(device_id) REFERENCES devices(id));
        CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(device_id, recorded_at DESC);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, severity TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL);
        INSERT OR IGNORE INTO devices(id,name,created_at) VALUES ('smartlab-node-01','SmartLab Node 01',datetime('now'));
        INSERT OR IGNORE INTO settings(key,value) VALUES ('temperature_limit_c','30'),('humidity_min_pct','20'),('humidity_max_pct','75');
        """)

class ReadingIn(BaseModel):
    temperature_c: float = Field(ge=-50, le=150)
    humidity_pct: float = Field(ge=0, le=100)
    device_id: str = Field(default=DEFAULT_DEVICE, min_length=1, max_length=80)
    source: str = Field(default="device", max_length=30)

class DeviceIn(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="ESP32 + DHT22", max_length=120)

class SettingsIn(BaseModel):
    temperature_limit_c: float = Field(ge=0, le=80)
    humidity_min_pct: float = Field(ge=0, le=100, default=20)
    humidity_max_pct: float = Field(ge=0, le=100, default=75)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(); yield

app = FastAPI(title="ECE SmartLab API", version="1.0.0", description="Telemetry, device registry, history and threshold events for ECE SmartLab.", lifespan=lifespan)
origins = os.getenv("SMARTLAB_CORS_ORIGINS", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","PUT","DELETE","OPTIONS"], allow_headers=["*"])

@app.get("/")
def root(): return {"name":"ECE SmartLab API","version":"1.0.0","docs":"/docs","health":"/api/health"}

@app.get("/api/health")
def health(): return {"ok":True,"service":"ece-smartlab-api","time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/devices")
def devices():
    with db() as con: rows=con.execute("SELECT * FROM devices ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/devices", status_code=201)
def add_device(item: DeviceIn):
    now=datetime.now(timezone.utc).isoformat()
    try:
        with db() as con: con.execute("INSERT INTO devices(id,name,kind,created_at) VALUES(?,?,?,?)",(item.id,item.name,item.kind,now))
    except sqlite3.IntegrityError: raise HTTPException(409,"Device ID already exists")
    return {"id":item.id,"name":item.name,"kind":item.kind,"created_at":now}

@app.post("/api/readings", status_code=201)
def ingest(item: ReadingIn):
    now=datetime.now(timezone.utc).isoformat()
    with db() as con:
        dev=con.execute("SELECT id FROM devices WHERE id=?",(item.device_id,)).fetchone()
        if not dev: raise HTTPException(404,"Unknown device. Register it first at /api/devices.")
        con.execute("INSERT INTO readings(device_id,temperature_c,humidity_pct,recorded_at,source) VALUES(?,?,?,?,?)",(item.device_id,item.temperature_c,item.humidity_pct,now,item.source))
        con.execute("UPDATE devices SET last_seen=?,online=1 WHERE id=?",(now,item.device_id))
        limit=float(con.execute("SELECT value FROM settings WHERE key='temperature_limit_c'").fetchone()[0])
        if item.temperature_c>=limit:
            con.execute("INSERT INTO events(device_id,severity,message,created_at) VALUES(?,?,?,?)",(item.device_id,"warning",f"Temperature {item.temperature_c:.1f} °C reached limit {limit:.1f} °C",now))
    return {"accepted":True,"device_id":item.device_id,"recorded_at":now}

@app.get("/api/readings/latest")
def latest(device_id: str=Query(default=DEFAULT_DEVICE)):
    with db() as con: row=con.execute("SELECT * FROM readings WHERE device_id=? ORDER BY id DESC LIMIT 1",(device_id,)).fetchone()
    if not row: raise HTTPException(404,"No readings have been received for this device yet")
    return dict(row)

@app.get("/api/readings")
def history(device_id: str=Query(default=DEFAULT_DEVICE), limit: int=Query(default=100,ge=1,le=1000), before_id: Optional[int]=None):
    sql="SELECT * FROM readings WHERE device_id=?"; params=[device_id]
    if before_id is not None: sql+=" AND id<?"; params.append(before_id)
    sql+=" ORDER BY id DESC LIMIT ?"; params.append(limit)
    with db() as con: rows=con.execute(sql,params).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/settings")
def get_settings():
    with db() as con: rows=con.execute("SELECT key,value FROM settings").fetchall()
    return {r["key"]:float(r["value"]) for r in rows}

@app.put("/api/settings")
def set_settings(item: SettingsIn):
    if item.humidity_min_pct>=item.humidity_max_pct: raise HTTPException(400,"Humidity minimum must be lower than maximum")
    values={"temperature_limit_c":item.temperature_limit_c,"humidity_min_pct":item.humidity_min_pct,"humidity_max_pct":item.humidity_max_pct}
    with db() as con:
        con.executemany("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",[(k,str(v)) for k,v in values.items()])
    return values

@app.get("/api/events")
def events(limit: int=Query(default=100,ge=1,le=500)):
    with db() as con: rows=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    return [dict(r) for r in rows]
