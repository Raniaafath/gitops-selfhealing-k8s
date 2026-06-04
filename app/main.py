from fastapi import FastAPI
import time

app = FastAPI()
start_time = time.time()

@app.get("/")
def root():
    return {"status": "ok", "service": "gitops-selfhealing-demo"}

@app.get("/health")
def health():
    return {"healthy": True}

@app.get("/metrics-info")
def metrics():
    uptime = time.time() - start_time
    return {"uptime_seconds": round(uptime, 2)}