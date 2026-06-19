from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3, time, os

app = FastAPI()

DB = "inspector.db"

# --- Seed data: real bus stations in Rishon LeZion ---
STATIONS = [
    {"id": 1, "name": "תחנה מרכזית ראשון לציון",     "lat": 31.9730, "lon": 34.7895},
    {"id": 2, "name": "בית החולים קפלן",               "lat": 31.9642, "lon": 34.7817},
    {"id": 3, "name": "רכבת ראשון לציון משה דיין",     "lat": 31.9884, "lon": 34.7763},
    {"id": 4, "name": "רכבת ראשון לציון הראשונים",     "lat": 31.9613, "lon": 34.8012},
    {"id": 5, "name": "קניון הזהב",                    "lat": 31.9748, "lon": 34.8031},
    {"id": 6, "name": "מרכז קליטה / אגמים",            "lat": 31.9801, "lon": 34.7712},
    {"id": 7, "name": "בית ברל / וולפסון",             "lat": 31.9553, "lon": 34.7934},
    {"id": 8, "name": "שדרות רוטשילד / הרצל",          "lat": 31.9677, "lon": 34.8056},
]

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            station_id INTEGER PRIMARY KEY,
            has_inspector INTEGER NOT NULL,
            reported_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

EXPIRY_SECONDS = 60 * 60  # 1 hour

class Report(BaseModel):
    station_id: int
    has_inspector: bool

@app.get("/", response_class=HTMLResponse)
def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/stations")
def get_stations():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reports").fetchall()
    conn.close()

    reports = {}
    now = time.time()
    for row in rows:
        age = now - row["reported_at"]
        if age < EXPIRY_SECONDS:
            reports[row["station_id"]] = {
                "has_inspector": bool(row["has_inspector"]),
                "minutes_ago": int(age // 60)
            }

    result = []
    for s in STATIONS:
        report = reports.get(s["id"])
        result.append({
            **s,
            "has_inspector": report["has_inspector"] if report else None,
            "minutes_ago": report["minutes_ago"] if report else None,
        })
    return result

@app.post("/report")
def post_report(report: Report):
    conn = get_db()
    conn.execute("""
        INSERT INTO reports (station_id, has_inspector, reported_at)
        VALUES (?, ?, ?)
        ON CONFLICT(station_id) DO UPDATE SET
            has_inspector = excluded.has_inspector,
            reported_at = excluded.reported_at
    """, (report.station_id, int(report.has_inspector), time.time()))
    conn.commit()
    conn.close()
    return {"ok": True}
