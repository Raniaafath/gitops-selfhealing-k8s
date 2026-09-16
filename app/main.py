from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import time

app = FastAPI()
start_time = time.time()

Instrumentator().instrument(app).expose(app)

@app.get("/")
def root():
    return {"status": "ok", "service": "gitops-selfhealing-demo", "version": "v2"}

@app.get("/health")
def health():
    return {"healthy": True}

@app.get("/metrics-info")
def metrics():
    uptime = time.time() - start_time
    return {"uptime_seconds": round(uptime, 2)}