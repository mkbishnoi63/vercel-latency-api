import json
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS: lets any website call this endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the data once, when the function starts
DATA_FILE = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"
with open(DATA_FILE) as f:
    DATA = json.load(f)


class Query(BaseModel):
    regions: List[str]
    threshold_ms: float


def percentile(values, p):
    """Same method as numpy.percentile (linear interpolation)."""
    v = sorted(values)
    k = (len(v) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def get(rec, *names):
    for n in names:
        if n in rec:
            return rec[n]


@app.post("/")
@app.post("/api")
def analyze(q: Query):
    result = {}
    for region in q.regions:
        rows = [r for r in DATA if get(r, "region") == region]
        if not rows:
            continue
        lat = [get(r, "latency_ms", "latency") for r in rows]
        up = [get(r, "uptime_pct", "uptime") for r in rows]
        result[region] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for x in lat if x > q.threshold_ms),
        }
    return result